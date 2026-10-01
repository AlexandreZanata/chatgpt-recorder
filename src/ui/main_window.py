"""PySide6 Native Linux Desktop GUI MainWindow with Mode Selector."""

import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFormLayout,
    QLabel, QMainWindow, QProgressBar, QPushButton, QStackedWidget,
    QVBoxLayout, QWidget
)

from src.core.auto_story_worker import AutoStoryWorker
from src.core.standard_video_worker import RenderWorker
from src.engine.standard_backgrounds import resolve_standard_background
from src.ui.mode_views import create_classic_fields, create_auto_story_fields
from src.ui.standard_controls import selected_standard_theme

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
IMAGENS_DIR = PROJECT_ROOT / "imagens"
AUDIO_DIR = PROJECT_ROOT / "audio"
BGM_DIR = PROJECT_ROOT / "background-music"
VIDEO_DIR = PROJECT_ROOT / "video"
AUDIO_EXTS = [".aac", ".m4a", ".mp3", ".wav", ".ogg", ".flac"]


class VideoGeneratorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Video Automation Studio")
        self.setObjectName("ChatGPTVideoStudio")
        self.resize(760, 780)
        for d in (IMAGENS_DIR, AUDIO_DIR, BGM_DIR, VIDEO_DIR):
            d.mkdir(exist_ok=True)
        self.init_ui()
        self.auto_prefill_media()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        header_form = QFormLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.setStyleSheet("font-weight: bold; font-size: 13px; color: #10b981; padding: 4px;")
        self.mode_combo.addItems(["🎬 Modo Clássico (1 Imagem + Áudio + Música)", "🤖 Modo Auto AI Story (Múltiplas Cenas + IA + Legendas)"])
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        header_form.addRow("🎯 Modo de Produção:", self.mode_combo)
        layout.addLayout(header_form)

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
        self.mode_combo.setCurrentIndex(1)

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
        fields = create_auto_story_fields(form, self.browse_file, AUDIO_DIR, BGM_DIR)
        for label, widget in fields["rows"]:
            form.addRow(label, widget)
        return w, fields

    def _on_mode_changed(self, idx: int):
        self.stack.setCurrentIndex(idx)
        btn_text = "🤖 Gerar Vídeo com IA & Cenas Automáticas" if idx == 1 else "🚀 Generate Video (NVENC GPU)"
        color = "#10b981" if idx == 1 else "#6366f1"
        self.btn_render.setText(btn_text)
        self.btn_render.setStyleSheet(f"background-color: {color}; color: white; font-weight: bold; padding: 10px;")

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
        self.s_fields["in_bgm"].setText(first_match(BGM_DIR, AUDIO_EXTS))

    def _get_next_out(self):
        n = 1
        while (VIDEO_DIR / f"{n}.mp4").exists():
            n += 1
        return str(VIDEO_DIR / f"{n}.mp4")

    def _make_standard_worker(self, output):
        img = Path(self.c_fields["in_img"].text().strip())
        narr = Path(self.c_fields["in_narr"].text().strip())
        theme = selected_standard_theme(self.c_fields)
        try:
            portrait = self.c_fields["preset"].currentText() == "YouTube Shorts / Reels (9:16)"
            background, _ = resolve_standard_background(img, theme, portrait=portrait)
        except (ValueError, FileNotFoundError) as err:
            self.status_label.setText(str(err))
            return None
        if not background.is_file() or not narr.is_file():
            self.status_label.setText("Select valid narration and a background image or particle theme.")
            return None
        has_bgm = not self.no_bgm_cb.isChecked() and bool(self.c_fields["in_bgm"].text().strip())
        bgm = Path(self.c_fields["in_bgm"].text().strip()) if has_bgm else None
        return RenderWorker(
            img, narr, bgm, Path(output), self.c_fields["s_narr"].value() / 100.0,
            self.c_fields["s_music"].value() / 100.0, self.c_fields["preset"].currentText(),
            quick_outro=self.quick_outro_cb.isChecked(),
            has_subtitles=self.c_fields["subtitles"].isChecked(), background_theme=theme,
        )

    def start_rendering(self):
        out_def = self._get_next_out()
        output, _ = QFileDialog.getSaveFileName(self, "Save Video", out_def, "MP4 Video (*.mp4)")
        if not output:
            return

        if self.mode_combo.currentIndex() == 1:
            narr = Path(self.s_fields["in_narr"].text().strip())
            if not narr.is_file():
                self.status_label.setText("Erro: Selecione um áudio de narração válido!")
                return
            has_s_bgm = not self.s_fields["no_bgm"].isChecked() and bool(self.s_fields["in_bgm"].text().strip())
            s_bgm = Path(self.s_fields["in_bgm"].text().strip()) if has_s_bgm else None
            t_w = self.s_fields["theme"]
            theme_val = t_w.currentText() if hasattr(t_w, "currentText") else t_w.text()
            self.worker = AutoStoryWorker(
                narr, s_bgm, Path(output), self.s_fields["interval"].value(),
                theme_val, self.s_fields["model"].currentText(),
                self.s_fields["subtitles"].isChecked(), self.s_fields["motion"].isChecked(),
                self.s_fields["preset"].currentText(), self.s_fields["s_narr"].value() / 100.0,
                self.s_fields["s_music"].value() / 100.0
            )
        else:
            self.worker = self._make_standard_worker(output)
            if self.worker is None:
                return

        self.btn_render.setEnabled(False)
        self.progress_bar.setValue(5)
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
