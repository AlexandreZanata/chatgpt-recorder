"""PySide6 Native Linux Desktop GUI MainWindow for Video Generation."""

import sys
from pathlib import Path
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QMainWindow, QProgressBar, QPushButton, QSlider,
    QVBoxLayout, QWidget,
)

from src.engine.audio_mixer import get_audio_duration
from src.engine.video_composer import render_single_pass_video

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
IMAGENS_DIR = PROJECT_ROOT / "imagens"
AUDIO_DIR = PROJECT_ROOT / "audio"
BGM_DIR = PROJECT_ROOT / "background-music"
VIDEO_DIR = PROJECT_ROOT / "video"
AUDIO_EXTS = [".aac", ".m4a", ".mp3", ".wav", ".ogg", ".flac"]


class RenderWorker(QThread):
    """Asynchronous background rendering thread."""

    progress = Signal(int, str)
    finished = Signal(bool, str)

    def __init__(self, img: Path, narr: Path, bgm: Path | None, out: Path, n_vol: float, m_vol: float, preset: str):
        super().__init__()
        self.img, self.narr, self.bgm, self.out = img, narr, bgm, out
        self.n_vol, self.m_vol, self.preset = n_vol, m_vol, preset

    def run(self):
        try:
            total_dur = get_audio_duration(self.narr)
            render_dur = total_dur + 30.0 if total_dur > 0 else 0.0
            self.progress.emit(5, f"Single-Pass GPU Encoding (0.0s / {render_dur:.1f}s)...")

            def on_progress(pct_val: float, sec_val: float):
                msg = f"Single-Pass GPU Encoding ({sec_val:.1f}s / {render_dur:.1f}s)..."
                self.progress.emit(int(pct_val), msg)

            w, h = (1920, 1080) if self.preset == "YouTube Standard (16:9)" else (1080, 1920)
            ok = render_single_pass_video(
                self.img, self.narr, self.bgm, None, self.out,
                narr_vol=self.n_vol, bgm_vol=self.m_vol, width=w, height=h,
                progress_callback=on_progress, total_duration=render_dur
            )

            self.progress.emit(100, "Rendering complete!")
            self.finished.emit(ok, f"Video rendered at {self.out}" if ok else "GPU rendering failed.")
        except Exception as err:
            self.finished.emit(False, str(err))


class VideoGeneratorApp(QMainWindow):
    """Main Window UI for Automated Video Generator."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Video Automation Studio")
        self.setObjectName("ChatGPTVideoStudio")
        self.resize(650, 500)
        for d in (IMAGENS_DIR, AUDIO_DIR, BGM_DIR, VIDEO_DIR):
            d.mkdir(exist_ok=True)
        self.init_ui()
        self.auto_prefill_media()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        form = QFormLayout()

        filter_a = "Audio (*.aac *.m4a *.mp3 *.wav *.ogg *.flac)"
        self.img_input = self.create_file_row(form, "Background Image:", "Image (*.png *.jpg *.webp)", IMAGENS_DIR)
        self.narr_input = self.create_file_row(form, "Narration Audio:", filter_a, AUDIO_DIR)
        self.bgm_input = self.create_file_row(form, "Background Music:", filter_a, BGM_DIR)

        self.narr_slider = self.create_slider_row(form, "Narration Volume:", 0, 200, 150)
        self.music_slider = self.create_slider_row(form, "Music Volume:", 0, 50, 15)

        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["YouTube Standard (16:9)", "YouTube Shorts / Reels (9:16)"])
        form.addRow("Video Preset:", self.preset_combo)

        self.no_bgm_cb = QCheckBox("Criar sem música de fundo (Apenas Narração)")
        form.addRow("", self.no_bgm_cb)

        layout.addLayout(form)
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        self.status_label = QLabel("Status: Ready")
        layout.addWidget(self.status_label)

        self.btn_render = QPushButton("🚀 Generate Video (NVENC GPU)")
        self.btn_render.setStyleSheet("background-color: #6366f1; color: white; font-weight: bold; padding: 10px;")
        self.btn_render.clicked.connect(self.start_rendering)
        layout.addWidget(self.btn_render)

    def create_file_row(self, form, label, filter_str, default_dir):
        line = QLineEdit()
        btn = QPushButton("Browse...")
        btn.clicked.connect(lambda: self.browse_file(line, filter_str, default_dir))
        box = QHBoxLayout()
        box.addWidget(line)
        box.addWidget(btn)
        form.addRow(label, box)
        return line

    def create_slider_row(self, form, label, min_v, max_v, default_v):
        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_v, max_v)
        slider.setValue(default_v)
        lbl = QLabel(f"{default_v}%")
        slider.valueChanged.connect(lambda v: lbl.setText(f"{v}%"))
        box = QHBoxLayout()
        box.addWidget(slider)
        box.addWidget(lbl)
        form.addRow(label, box)
        return slider

    def browse_file(self, line_edit, filter_str, default_dir):
        start = str(default_dir) if default_dir.is_dir() else ""
        path, _ = QFileDialog.getOpenFileName(self, "Select File", start, filter_str)
        if path:
            line_edit.setText(path)

    def auto_prefill_media(self):
        def first_match(dir_path, exts):
            m = [p for p in dir_path.glob("*") if p.suffix.lower() in exts]
            return str(m[0]) if m else ""

        self.img_input.setText(first_match(IMAGENS_DIR, [".png", ".jpg", ".jpeg", ".webp"]))
        self.narr_input.setText(first_match(AUDIO_DIR, AUDIO_EXTS))
        self.bgm_input.setText(first_match(BGM_DIR, AUDIO_EXTS))

    def update_progress(self, val: int, msg: str):
        self.progress_bar.setValue(val)
        self.status_label.setText(msg)

    def get_next_suggested_video_path(self):
        n = 1
        while (VIDEO_DIR / f"{n}.mp4").exists():
            n += 1
        return str(VIDEO_DIR / f"{n}.mp4")

    def start_rendering(self):
        img = Path(self.img_input.text())
        narr = Path(self.narr_input.text())
        has_bgm = not self.no_bgm_cb.isChecked() and bool(self.bgm_input.text())
        bgm = Path(self.bgm_input.text()) if has_bgm else None
        default_out = self.get_next_suggested_video_path()
        output, _ = QFileDialog.getSaveFileName(self, "Save Video", default_out, "MP4 Video (*.mp4)")

        if not img.is_file() or not narr.is_file() or not output:
            self.status_label.setText("Error: Select valid Image and Narration Audio files.")
            return

        self.btn_render.setEnabled(False)
        self.update_progress(5, "Initializing single-pass NVENC GPU pipeline...")
        self.worker = RenderWorker(
            img, narr, bgm, Path(output),
            self.narr_slider.value() / 100.0,
            self.music_slider.value() / 100.0,
            self.preset_combo.currentText(),
        )
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_render_finished)
        self.worker.start()

    def on_render_finished(self, success, message):
        self.btn_render.setEnabled(True)
        self.status_label.setText(message)


def run_app():
    app = QApplication(sys.argv)
    app.setApplicationName("ChatGPTVideoStudio")
    app.setDesktopFileName("chatgpt-video-studio")
    window = VideoGeneratorApp()
    window.show()
    sys.exit(app.exec())
