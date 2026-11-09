"""Native local WAV preview; synthesis and playback are separate operations."""

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer


class AudioPreview(QObject):
    failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.player, self.output = None, None

    def play(self, path):
        if self.player is None:
            self.player = QMediaPlayer(self)
            self.output = QAudioOutput(self)
            self.output.setVolume(0.8)
            self.player.setAudioOutput(self.output)
            self.player.errorOccurred.connect(lambda *args: self.failed.emit(self.player.errorString()))
        self.player.stop()
        self.player.setSource(QUrl.fromLocalFile(str(path)))
        self.player.play()

    def stop(self):
        if self.player is not None:
            self.player.stop()
