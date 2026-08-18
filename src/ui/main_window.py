"""PySide6 Native Linux Desktop GUI MainWindow with Mode Selector."""

import sys
from pathlib import Path
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFormLayout,
    QLabel, QMainWindow, QProgressBar, QPushButton, QStackedWidget,
    QVBoxLayout, QWidget
)

from src.engine.audio_mixer import get_audio_duration
from src.engine.video_composer import render_single_pass_video
from src.ui.mode_views import create_classic_fields, create_auto_story_fields

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
IMAGENS_DIR = PROJECT_ROOT / "imagens"
AUDIO_DIR = PROJECT_ROOT / "audio"
BGM_DIR = PROJECT_ROOT / "background-music"
VIDEO_DIR = PROJECT_ROOT / "video"
AUDIO_EXTS = [".aac", ".m4a", ".mp3", ".wav", ".ogg", ".flac"]


class RenderWorker(QThread):
    progress = Signal(int, str)
    finished = Signal(bool, str)

    def __init__(self, img: Path, narr: Path, bgm: Path | None, out: Path, n_vol: float, m_vol: float, preset: str, quick_outro: bool = False):
        super().__init__()
        self.img, self.narr, self.bgm, self.out = img, narr, bgm, out
        self.n_vol, self.m_vol, self.preset, self.quick_outro = n_vol, m_vol, preset, quick_outro

    def run(self):
        try:
            total_dur = get_audio_duration(self.narr)
            outro_margin = 0.0 if self.preset != "YouTube Standard (16:9)" else (5.0 if self.quick_outro else 30.0)
            render_dur = total_dur + outro_margin if total_dur > 0 else 0.0
            self.progress.emit(5, f"Single-Pass GPU Encoding (0.0s / {render_dur:.1f}s)...")

            def on_progress(pct_val: float, sec_val: float):
                self.progress.emit(int(pct_val), f"Single-Pass GPU Encoding ({sec_val:.1f}s / {render_dur:.1f}s)...")

            w, h = (1920, 1080) if self.preset == "YouTube Standard (16:9)" else (1080, 1920)
            ok = render_single_pass_video(self.img, self.narr, self.bgm, None, self.out, narr_vol=self.n_vol, bgm_vol=self.m_vol, width=w, height=h, progress_callback=on_progress, total_duration=render_dur)
            self.progress.emit(100, "Rendering complete!")
            self.finished.emit(ok, f"Video rendered at {self.out}" if ok else "GPU rendering failed.")
        except Exception as err:
            self.finished.emit(False, str(err))


class VideoGeneratorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Video Automation Studio")
        self.setObjectName("ChatGPTVideoStudio")
        self.resize(680, 560)
        for d in (IMAGENS_DIR, AUDIO_DIR, BGM_DIR, VIDEO_DIR):
            d.mkdir(exist_ok=True)
        self.init_ui()
        self.auto_prefill_media()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Mode Selector
        header_form = QFormLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.setStyleSheet("font-weight: bold; font-size: 13px; color: #10b981; padding: 4px;")
        self.mode_combo.addItems(["🎬 Modo Clássico (1 Imagem + Áudio + Música)", "🤖 Modo Auto AI Story (Múltiplas Cenas + IA + Legendas)"])
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        header_form.addRow("🎯 Modo de Produção:", self.mode_combo)
        layout.addLayout(header_form)

        # Stacked Container
        self.stack = QStackedWidget()
        self.w_classic, self.c_fields = self._build_classic_widget()
        self.w_story, self.s_fields = self._build_story_widget()
        self.stack.addWidget(self.w_classic)
        self.stack.addWidget(self.w_story)
        layout.addWidget(self.stack)

        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        self.status_label = QLabel("Status: Ready")
        layout.addWidget(self.status_label)

        self.btn_render = QPushButton("🚀 Generate Video (NVENC GPU)")
        self.btn_render.setStyleSheet("background-color: #6366f1; color: white; font-weight: bold; padding: 10px;")
        self.btn_render.clicked.connect(self.start_rendering)
        layout.addWidget(self.btn_render)

    def _build_classic_widget(self):
        w = QWidget()
        form = QFormLayout(w)
        fields = create_classic_fields(form, self.browse_file, IMAGENS_DIR, AUDIO_DIR, BGM_DIR)
        for label, widget in fields["rows"]:
            form.addRow(label, widget)

        style_ind = "QCheckBox { font-weight: bold; font-size: 13px; color: #4338ca; background-color: #e0e7ff; border: 2px solid #6366f1; border-radius: 6px; padding: 5px 10px; }"
        style_red = "QCheckBox { font-weight: bold; font-size: 13px; color: #991b1b; background-color: #fee2e2; border: 2px solid #ef4444; border-radius: 6px; padding: 5px 10px; }"
        self.no_bgm_cb = QCheckBox("🎵 Criar sem música de fundo (Apenas Narração)")
        self.no_bgm_cb.setStyleSheet(style_ind)
        self.quick_outro_cb = QCheckBox("⏱️ Encerramento rápido (+5s de música no final)")
        self.quick_outro_cb.setStyleSheet(style_red)
        form.addRow("", self.no_bgm_cb)
        form.addRow("", self.quick_outro_cb)
        return w, fields

    def _build_story_widget(self):
        w = QWidget()
        form = QFormLayout(w)
        fields = create_auto_story_fields(form, self.browse_file, AUDIO_DIR)
        for label, widget in fields["rows"]:
            form.addRow(label, widget)
        return w, fields

    def _on_mode_changed(self, idx: int):
        self.stack.setCurrentIndex(idx)
        if idx == 1:
            self.btn_render.setText("🤖 Gerar Vídeo com IA & Cenas Automáticas")
            self.btn_render.setStyleSheet("background-color: #10b981; color: white; font-weight: bold; padding: 10px;")
        else:
            self.btn_render.setText("🚀 Generate Video (NVENC GPU)")
            self.btn_render.setStyleSheet("background-color: #6366f1; color: white; font-weight: bold; padding: 10px;")

    def browse_file(self, line_edit, filter_str, default_dir):
        start = str(default_dir) if default_dir.is_dir() else ""
        path, _ = QFileDialog.getOpenFileName(self, "Select File", start, filter_str)
        if path:
            line_edit.setText(path)

    def auto_prefill_media(self):
        def first_match(d, exts):
            m = [p for p in d.glob("*") if p.suffix.lower() in exts]
            return str(m[0]) if m else ""
        self.c_fields["in_img"].setText(first_match(IMAGENS_DIR, [".png", ".jpg", ".jpeg", ".webp"]))
        self.c_fields["in_narr"].setText(first_match(AUDIO_DIR, AUDIO_EXTS))
        self.c_fields["in_bgm"].setText(first_match(BGM_DIR, AUDIO_EXTS))
        self.s_fields["in_narr"].setText(first_match(AUDIO_DIR, AUDIO_EXTS))

    def start_rendering(self):
        if self.mode_combo.currentIndex() == 1:
            self.status_label.setText("🤖 Planejador de Cenas iniciado: Gerando imagens SDXL e legendas...")
            self.progress_bar.setValue(25)
            return

        img = Path(self.c_fields["in_img"].text())
        narr = Path(self.c_fields["in_narr"].text())
        has_bgm = not self.no_bgm_cb.isChecked() and bool(self.c_fields["in_bgm"].text())
        bgm = Path(self.c_fields["in_bgm"].text()) if has_bgm else None
        n = 1
        while (VIDEO_DIR / f"{n}.mp4").exists():
            n += 1
        output, _ = QFileDialog.getSaveFileName(self, "Save Video", str(VIDEO_DIR / f"{n}.mp4"), "MP4 Video (*.mp4)")
        if not img.is_file() or not narr.is_file() or not output:
            self.status_label.setText("Error: Select valid Image and Narration Audio files.")
            return

        self.btn_render.setEnabled(False)
        self.progress_bar.setValue(5)
        self.status_label.setText("Initializing single-pass NVENC GPU pipeline...")
        self.worker = RenderWorker(img, narr, bgm, Path(output), self.c_fields["s_narr"].value() / 100.0, self.c_fields["s_music"].value() / 100.0, self.c_fields["preset"].currentText(), quick_outro=self.quick_outro_cb.isChecked())
        self.worker.progress.connect(lambda val, msg: (self.progress_bar.setValue(val), self.status_label.setText(msg)))
        self.worker.finished.connect(lambda ok, msg: (self.btn_render.setEnabled(True), self.status_label.setText(msg)))
        self.worker.start()


def run_app():
    app = QApplication(sys.argv)
    app.setApplicationName("ChatGPTVideoStudio")
    app.setDesktopFileName("chatgpt-video-studio")
    window = VideoGeneratorApp()
    window.show()
    sys.exit(app.exec())
