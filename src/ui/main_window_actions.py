"""Render, transcription and narration actions for the desktop app."""

from PySide6.QtWidgets import QFileDialog

from src.ui.render_requests import make_standard_worker, make_story_worker


class VideoGeneratorActions:
    def _get_next_out(self):
        n = 1
        while (self.video_dir / f"{n}.mp4").exists():
            n += 1
        return str(self.video_dir / f"{n}.mp4")

    def start_rendering(self):
        if self.narration.busy:
            return
        if self.narration.controls.use_text.isChecked():
            self.narration.request_full(self._start_rendering)
        else:
            self._start_rendering()

    def _make_standard_worker(self, output):
        try:
            return make_standard_worker(self.c_fields, self.no_bgm_cb.isChecked(),
                                        self.quick_outro_cb.isChecked(), output)
        except (ValueError, FileNotFoundError) as error:
            self.status_label.setText(str(error))
            return None

    def _use_generated_narration(self, path):
        fields = self.s_fields if self.mode_combo.currentIndex() == 1 else self.c_fields
        fields["in_narr"].setText(path)

    def _speech_busy(self, busy):
        self.mode_combo.setEnabled(not busy)
        self.btn_render.setEnabled(not busy)

    def closeEvent(self, event):
        if self.narration.busy:
            self.narration.cancel()
            event.ignore()
        elif hasattr(self, "worker") and self.worker.isRunning():
            self.status_label.setText("Wait for video rendering to finish before closing.")
            event.ignore()
        else:
            event.accept()

    def _start_rendering(self):
        out_def = self._get_next_out()
        output, _ = QFileDialog.getSaveFileName(self, "Save Video", out_def, "MP4 Video (*.mp4)")
        if not output:
            return

        try:
            if self.mode_combo.currentIndex() == 1:
                self.worker = make_story_worker(self.s_fields, output)
            else:
                self.worker = self._make_standard_worker(output)
                if self.worker is None:
                    return
        except (ValueError, FileNotFoundError) as error:
            self.status_label.setText(str(error))
            return

        self._speech_busy(True)
        self.narration.setEnabled(False)
        self._begin_transcription_phase()
        self.worker.progress.connect(self._on_render_progress)
        self.worker.finished.connect(self._on_render_finished)
        self.worker.start()

    def _begin_transcription_phase(self):
        self._transcribing = True
        self._pulse_tick = 0
        self._last_progress = 0
        self.progress_bar.setRange(0, 0)
        self.status_label.setText("Transcribing narration for synchronized subtitles…")
        self._pulse_timer.start()

    def _pulse_transcription(self):
        self._pulse_tick += 1
        phases = ("Loading speech model", "Listening to narration",
                  "Aligning subtitles", "Polishing timestamps")
        phase = phases[(self._pulse_tick // 3) % len(phases)]
        dots = "." * (1 + (self._pulse_tick % 3))
        self.status_label.setText(f"Transcribing narration — {phase}{dots}")

    def _on_render_progress(self, val, msg):
        if self._transcribing and val >= 5:
            self._transcribing = False
            self._pulse_timer.stop()
            self.progress_bar.setRange(0, 100)
            self._last_progress = 0
        if self._transcribing:
            return
        self._last_progress = max(self._last_progress, int(val))
        self.progress_bar.setValue(self._last_progress)
        self.status_label.setText(msg)

    def _on_render_finished(self, ok, msg):
        self._transcribing = False
        self._pulse_timer.stop()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100 if ok else max(self._last_progress, 5))
        self._speech_busy(False)
        self.narration.setEnabled(True)
        self.status_label.setText(msg)
