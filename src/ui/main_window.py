"""PySide6 Native Linux Desktop GUI MainWindow with Mode Selector."""

import sys
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFormLayout,
    QLabel, QMainWindow, QProgressBar, QPushButton, QStackedWidget,
    QScrollArea, QVBoxLayout, QWidget
)

from src.ui.mode_views import create_classic_fields, create_auto_story_fields
from src.ui.narration_panel import NarrationPanel
from src.ui.main_window_actions import VideoGeneratorActions

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
IMAGENS_DIR = PROJECT_ROOT / "imagens"
AUDIO_DIR = PROJECT_ROOT / "audio"
BGM_DIR = PROJECT_ROOT / "background-music"
VIDEO_DIR = PROJECT_ROOT / "video"
AUDIO_EXTS = [".aac", ".m4a", ".mp3", ".wav", ".ogg", ".flac"]


class VideoGeneratorApp(VideoGeneratorActions, QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Video Automation Studio")
        self.setObjectName("ChatGPTVideoStudio")
        self.resize(760, 780)
        for d in (IMAGENS_DIR, AUDIO_DIR, BGM_DIR, VIDEO_DIR):
            d.mkdir(exist_ok=True)
        self.video_dir = VIDEO_DIR
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
        accounts_button = QPushButton("Contas e canais do YouTube")
        accounts_button.clicked.connect(self.open_accounts)
        layout.addWidget(accounts_button)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        scroll.setWidget(body)
        body_layout = QVBoxLayout(body)
        layout.addWidget(scroll, 1)

        self.narration = NarrationPanel(AUDIO_DIR)
        self.narration.narrationReady.connect(self._use_generated_narration)
        self.narration.busyChanged.connect(self._speech_busy)
        body_layout.addWidget(self.narration)

        self.stack = QStackedWidget()
        self.w_classic, self.c_fields = self._build_classic_widget()
        self.w_story, self.s_fields = self._build_story_widget()
        self.stack.addWidget(self.w_classic)
        self.stack.addWidget(self.w_story)
        body_layout.addWidget(self.stack)

        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        self.status_label = QLabel("Status: Ready")
        layout.addWidget(self.status_label)
        self._pulse_timer = QTimer(self)
        self._pulse_timer.setInterval(450)
        self._pulse_timer.timeout.connect(self._pulse_transcription)
        self._pulse_tick = 0
        self._last_progress = 0
        self._transcribing = False

        self.btn_render = QPushButton("🚀 Generate Video (NVENC GPU)")
        self.btn_render.setStyleSheet("background-color: #6366f1; color: white; font-weight: bold; padding: 10px;")
        self.btn_render.clicked.connect(self.start_rendering)
        layout.addWidget(self.btn_render)
        self.mode_combo.setCurrentIndex(0)

    def open_accounts(self):
        from src.ui.accounts_window import AccountsWindow
        self.accounts_window = AccountsWindow(self)
        self.accounts_window.show()

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



def run_app():
    app = QApplication(sys.argv)
    app.setApplicationName("ChatGPTVideoStudio")
    app.setDesktopFileName("chatgpt-video-studio")
    window = VideoGeneratorApp()
    window.show()
    sys.exit(app.exec())
