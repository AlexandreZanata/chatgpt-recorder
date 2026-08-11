"""PySide6 Native Linux Desktop GUI MainWindow for Video Generation."""

import sys
from pathlib import Path
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QMainWindow, QProgressBar, QPushButton, QSlider,
    QVBoxLayout, QWidget,
)

from src.engine.audio_mixer import mix_audio_tracks
from src.engine.video_composer import render_video

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
IMAGENS_DIR = PROJECT_ROOT / "imagens"
AUDIO_DIR = PROJECT_ROOT / "audio"
BGM_DIR = PROJECT_ROOT / "background-music"
AUDIO_EXTS = [".aac", ".m4a", ".mp3", ".wav", ".ogg", ".flac"]


class RenderWorker(QThread):
    """Asynchronous background rendering thread."""

    progress = Signal(int)
    finished = Signal(bool, str)

    def __init__(self, img: Path, narr: Path, bgm: Path | None, out: Path, n_vol: float, m_vol: float, preset: str):
        super().__init__()
        self.img, self.narr, self.bgm, self.out = img, narr, bgm, out
        self.n_vol, self.m_vol, self.preset = n_vol, m_vol, preset

    def run(self):
        try:
            self.progress.emit(20)
            mixed = self.out.parent / "temp_mixed.wav"
            if not mix_audio_tracks(self.narr, self.bgm, mixed, narration_volume=self.n_vol, bgm_volume=self.m_vol):
                self.finished.emit(False, "Audio mixing failed.")
                return
            self.progress.emit(60)
            w, h = (1920, 1080) if self.preset == "YouTube Standard (16:9)" else (1080, 1920)
            ok = render_video(self.img, mixed, None, self.out, width=w, height=h)
            if mixed.exists():
                mixed.unlink()
            self.progress.emit(100)
            self.finished.emit(ok, f"Video rendered at {self.out}" if ok else "NVENC GPU rendering failed.")
        except Exception as err:
            self.finished.emit(False, str(err))


class VideoGeneratorApp(QMainWindow):
    """Main Window UI for Automated Video Generator."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Video Automation Studio")
        self.setObjectName("ChatGPTVideoStudio")
        self.resize(650, 500)
        for d in (IMAGENS_DIR, AUDIO_DIR, BGM_DIR):
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

        self.narr_slider = self.create_slider_row(form, "Narration Volume:", 0, 200, 100)
        self.music_slider = self.create_slider_row(form, "Music Volume:", 0, 50, 18)

        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["YouTube Standard (16:9)", "YouTube Shorts / Reels (9:16)"])
        form.addRow("Video Preset:", self.preset_combo)

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

    def start_rendering(self):
        img = Path(self.img_input.text())
        narr = Path(self.narr_input.text())
        bgm = Path(self.bgm_input.text()) if self.bgm_input.text() else None
        output, _ = QFileDialog.getSaveFileName(self, "Save Video", "output_video.mp4", "MP4 Video (*.mp4)")

        if not img.is_file() or not narr.is_file() or not output:
            self.status_label.setText("Error: Select valid Image and Narration Audio files.")
            return

        self.btn_render.setEnabled(False)
        self.status_label.setText("Rendering video using NVENC GPU...")
        self.worker = RenderWorker(
            img, narr, bgm, Path(output),
            self.narr_slider.value() / 100.0,
            self.music_slider.value() / 100.0,
            self.preset_combo.currentText(),
        )
        self.worker.progress.connect(self.progress_bar.setValue)
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
