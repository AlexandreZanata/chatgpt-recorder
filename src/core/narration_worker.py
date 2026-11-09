"""Background narration generation, cancellable without terminating Qt threads."""

import time
from PySide6.QtCore import QThread, Signal


class NarrationWorker(QThread):
    progress = Signal(str)

    def __init__(self, service, request, preview=False, parent=None):
        super().__init__(parent)
        self.service, self.request, self.preview = service, request, preview
        self.output, self.error, self.elapsed = None, "", 0.0

    def cancel(self):
        self.requestInterruption()
        cancel = getattr(self.service.adapter, "cancel", None)
        if cancel:
            cancel()

    def run(self):
        started = time.perf_counter()
        try:
            self.output = self.service.generate(
                self.request, preview=self.preview, progress=self.progress.emit,
                cancelled=self.isInterruptionRequested,
            )
        except Exception as error:
            self.error = str(error)
        finally:
            self.elapsed = time.perf_counter() - started
