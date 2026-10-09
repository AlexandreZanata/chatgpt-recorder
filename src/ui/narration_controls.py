"""Compact, accessible controls for local narration in both video modes."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
)

from src.core.narration import DEFAULT_VOICE, VOICES


class NarrationControls(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.use_text = QCheckBox("Use text for video (otherwise use the selected audio file)")
        self.use_text.setChecked(True)
        self.use_text.toggled.connect(self._sync_tts_visibility)
        layout.addWidget(self.use_text)
        self.text = QPlainTextEdit()
        self.text.setPlaceholderText("Paste your complete narration here. Voice tests use only the first 60 words.")
        self.text.setAccessibleName("Narration text")
        self.text.setMinimumHeight(100)
        self.text.setMaximumHeight(170)
        layout.addWidget(self.text)
        self.settings = QWidget()
        form = QFormLayout(self.settings)
        form.setContentsMargins(0, 0, 0, 0)
        self.language = QComboBox()
        self.language.addItem("American English (locked)", "English")
        self.language.setEnabled(False)
        self.language.setToolTip("All narration and subtitle recognition use English; automatic detection is disabled.")
        self.voice = QComboBox()
        self.voice.addItem(f"{DEFAULT_VOICE} — {VOICES[DEFAULT_VOICE]} (locked)", DEFAULT_VOICE)
        self.voice.setEnabled(False)
        self.model = QComboBox()
        self.model.addItem("Qwen Base 0.6B — fixed voice reference / default", "0.6B")
        self.model.addItem("Qwen Base 1.7B — same reference / more memory", "1.7B")
        self.instruction = QLineEdit("Fixed: original Uncle_Fu recording")
        self.instruction.setToolTip("Voice and delivery are anchored to your approved sample for every passage.")
        self.model.currentIndexChanged.connect(self.update_instruction)
        self.update_instruction()
        for label, control in (("Language:", self.language), ("Voice:", self.voice),
                               ("Speech model:", self.model), ("Delivery reference:", self.instruction)):
            form.addRow(label, control)
        layout.addWidget(self.settings)
        self.hint = QLabel("English narration and recognition are fixed. Every passage reuses your original Uncle_Fu reference. First use downloads Base weights.")
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)
        self.actions = QWidget()
        actions = QHBoxLayout(self.actions)
        actions.setContentsMargins(0, 0, 0, 0)
        self.preview = QPushButton("Test voice")
        self.generate = QPushButton("Generate full narration")
        self.stop = QPushButton("Stop playback")
        self.cancel = QPushButton("Cancel generation")
        self.cancel.setEnabled(False)
        for button in (self.preview, self.generate, self.stop, self.cancel):
            actions.addWidget(button)
        layout.addWidget(self.actions)
        self.status = QLabel(f"Reference-locked {DEFAULT_VOICE}. Paste text to test the same voice and delivery.")
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.PlainText)
        layout.addWidget(self.status)
        self._sync_tts_visibility(self.use_text.isChecked())

    def update_instruction(self):
        self.instruction.setEnabled(False)

    def _sync_tts_visibility(self, checked):
        for widget in (self.text, self.settings, self.hint, self.actions, self.status):
            widget.setVisible(checked)

    def set_busy(self, busy):
        for widget in (self.text, self.settings, self.use_text, self.preview, self.generate):
            widget.setEnabled(not busy)
        self.cancel.setEnabled(busy)
