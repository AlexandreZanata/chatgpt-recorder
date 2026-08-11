"""PySide6 Native Linux Desktop GUI MainWindow for Video Generation."""

import sys
from pathlib import Path
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from src.engine.audio_mixer import mix_audio_tracks
from src.engine.video_composer import render_video


class RenderWorker(QThread):
    """Asynchronous background rendering thread."""

    progress = Signal(int)
    finished = Signal(bool, str)

    def __init__(
        self,
        image: Path,
        narration: Path,
        bgm: Path | None,
        output: Path,
        music_vol: float,
        preset: str,
    ):
        super().__init__()
        self.image = image
        self.narration = narration
        self.bgm = bgm
        self.output = output
        self.music_vol = music_vol
        self.preset = preset

    def run(self):
        try:
            self.progress.emit(20)
            mixed_audio = self.output.parent / "temp_mixed.wav"
            ok_mix = mix_audio_tracks(
                self.narration, self.bgm, mixed_audio, bgm_volume=self.music_vol
            )
            if not ok_mix:
                self.finished.emit(False, "Audio mixing failed.")
                return

            self.progress.emit(60)
            width, height = (1920, 1080) if self.preset == "YouTube Standard (16:9)" else (1080, 1920)
            ok_render = render_video(
                self.image, mixed_audio, None, self.output, width=width, height=height
            )

            if mixed_audio.exists():
                mixed_audio.unlink()

            self.progress.emit(100)
            if ok_render:
                self.finished.emit(True, f"Video rendered successfully at {self.output}")
            else:
                self.finished.emit(False, "FFmpeg NVENC video rendering failed.")
        except Exception as err:
            self.finished.emit(False, str(err))


class VideoGeneratorApp(QMainWindow):
    """Main Window UI for Automated Video Generator."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Video Automation Studio")
        self.resize(650, 480)
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        form = QFormLayout()
        self.img_input = self.create_file_row(form, "Background Image:", "Select Image (*.png *.jpg *.webp)")
        self.narr_input = self.create_file_row(form, "Narration Audio:", "Select Audio (*.mp3 *.wav)")
        self.bgm_input = self.create_file_row(form, "Background Music:", "Select Music (*.mp3 *.wav)")

        self.music_slider = QSlider(Qt.Horizontal)
        self.music_slider.setRange(0, 50)
        self.music_slider.setValue(18)
        self.music_val_lbl = QLabel("18%")
        self.music_slider.valueChanged.connect(lambda v: self.music_val_lbl.setText(f"{v}%"))

        slider_box = QHBoxLayout()
        slider_box.addWidget(self.music_slider)
        slider_box.addWidget(self.music_val_lbl)
        form.addRow("Music Volume:", slider_box)

        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["YouTube Standard (16:9)", "YouTube Shorts / Reels (9:16)"])
        form.addRow("Video Preset:", self.preset_combo)

        layout.addLayout(form)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Status: Ready")
        layout.addWidget(self.status_label)

        self.btn_render = QPushButton("🚀 Generate Video (NVENC GPU)")
        self.btn_render.setStyleSheet("background-color: #6366f1; color: white; font-weight: bold; padding: 10px;")
        self.btn_render.clicked.connect(self.start_rendering)
        layout.addWidget(self.btn_render)

    def create_file_row(self, form, label, filter_str):
        line = QLineEdit()
        btn = QPushButton("Browse...")
        btn.clicked.connect(lambda: self.browse_file(line, filter_str))
        box = QHBoxLayout()
        box.addWidget(line)
        box.addWidget(btn)
        form.addRow(label, box)
        return line

    def browse_file(self, line_edit, filter_str):
        path, _ = QFileDialog.getOpenFileName(self, "Select File", "", filter_str)
        if path:
            line_edit.setText(path)

    def start_rendering(self):
        img = Path(self.img_input.text())
        narr = Path(self.narr_input.text())
        bgm = Path(self.bgm_input.text()) if self.bgm_input.text() else None
        output, _ = QFileDialog.getSaveFileName(self, "Save Video", "output_video.mp4", "MP4 Video (*.mp4)")

        if not img.is_file() or not narr.is_file() or not output:
            self.status_label.setText("Error: Please select valid Image and Narration Audio files.")
            return

        self.btn_render.setEnabled(False)
        self.status_label.setText("Rendering video using NVENC GPU...")
        self.worker = RenderWorker(img, narr, bgm, Path(output), self.music_slider.value() / 100.0, self.preset_combo.currentText())
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished.connect(self.on_render_finished)
        self.worker.start()

    def on_render_finished(self, success, message):
        self.btn_render.setEnabled(True)
        self.status_label.setText(message)


def run_app():
    app = QApplication(sys.argv)
    window = VideoGeneratorApp()
    window.show()
    sys.exit(app.exec())
