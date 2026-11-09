"""Voice auditions and complete narration selection without blocking the GUI."""

from pathlib import Path
from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import QGroupBox, QVBoxLayout

from src.core.narration import SpeechRequest
from src.core.narration_worker import NarrationWorker
from src.engine.narration_service import NarrationService
from src.engine.qwen_speech import QwenSpeechAdapter
from src.ui.audio_preview import AudioPreview
from src.ui.narration_controls import NarrationControls


class NarrationPanel(QGroupBox):
    busyChanged = Signal(bool)
    narrationReady = Signal(str)

    def __init__(self, audio_dir: Path, service_factory=None):
        super().__init__("Local narration · reference-locked Uncle_Fu")
        self.service_factory = service_factory or (lambda: NarrationService(audio_dir, QwenSpeechAdapter()))
        self.controls = NarrationControls()
        QVBoxLayout(self).addWidget(self.controls)
        self.player = AudioPreview(self)
        self.player.failed.connect(lambda message: self.controls.status.setText(f"Playback failed: {message}"))
        self.worker = None
        self.busy, self._pending = False, None
        self.controls.preview.clicked.connect(self.test_voice)
        self.controls.generate.clicked.connect(lambda: self.request_full())
        self.controls.stop.clicked.connect(self.player.stop)
        self.controls.cancel.clicked.connect(self.cancel)

    def request(self):
        fields = self.controls
        return SpeechRequest(fields.text.toPlainText(), fields.voice.currentData(),
                             fields.language.currentData(), fields.model.currentData(),
                             fields.instruction.text())

    def test_voice(self):
        return self._start(preview=True)

    def request_full(self, callback=None):
        return self._start(preview=False, callback=callback)

    def _set_busy(self, busy):
        self.busy = busy
        self.controls.set_busy(busy)
        self.busyChanged.emit(busy)

    def _start(self, preview, callback=None):
        if self.busy:
            return False
        try:
            request = self.request()
        except ValueError as error:
            self.controls.status.setText(str(error))
            return False
        self.player.stop()
        self._pending = callback
        self.worker = NarrationWorker(self.service_factory(), request, preview, self)
        self.worker.progress.connect(self.controls.status.setText)
        self.worker.finished.connect(self._complete)
        self.controls.status.setText("Preparing voice test..." if preview else "Preparing full narration...")
        self._set_busy(True)
        self.worker.start()
        return True

    @Slot()
    def _complete(self):
        worker = self.worker
        callback, self._pending = self._pending, None
        self.worker = None
        self._set_busy(False)
        if worker.error:
            self.controls.status.setText(worker.error)
        elif worker.preview:
            self.controls.status.setText(f"Voice test ready in {worker.elapsed:.1f}s. Playing preview.")
            self.player.play(worker.output)
        else:
            self.controls.use_text.setChecked(True)
            self.controls.status.setText(f"Full narration ready in {worker.elapsed:.1f}s: {worker.output}")
            self.narrationReady.emit(str(worker.output))
            if callback:
                callback()
        worker.deleteLater()

    def cancel(self):
        if self.worker is not None:
            self.controls.status.setText("Cancelling narration generation...")
            self.worker.cancel()
