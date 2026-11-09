"""Qt narration journeys from docs/LOCAL-NARRATION.md, with deterministic audio."""

import os
from threading import Event
import unittest
import wave
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication
from src.engine.narration_service import NarrationService
from src.ui.narration_panel import NarrationPanel


class SilentSpeech:
    def synthesize(self, request, chunks, output, progress, cancelled):
        if cancelled():
            raise InterruptedError("Cancelled")
        with wave.open(str(output), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(24000)
            audio.writeframes(b"\0\0" * 2400)


class TestNarrationUi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make_panel(self, directory):
        panel = NarrationPanel(Path(directory), lambda: NarrationService(Path(directory), SilentSpeech()))
        self.addCleanup(panel.deleteLater)
        return panel

    def wait_for_completion(self, panel):
        loop = QEventLoop()
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(loop.quit)
        panel.busyChanged.connect(lambda busy: None if busy else loop.quit())
        timer.start(5000)
        loop.exec()
        self.assertFalse(panel.busy, "Speech job did not finish within the test timeout.")

    def test_given_panel_then_selected_audition_is_default_and_imported_audio_is_preserved(self):
        with TemporaryDirectory() as directory:
            panel = self.make_panel(directory)
            self.assertTrue(panel.controls.use_text.isChecked())
            panel.controls.use_text.setChecked(False)
            self.assertFalse(panel.controls.use_text.isChecked())
            self.assertEqual(panel.controls.voice.currentData(), "Uncle_Fu")
            self.assertEqual(panel.controls.language.currentData(), "English")
            self.assertEqual(panel.controls.model.currentData(), "0.6B")
            self.assertEqual(panel.controls.voice.count(), 1)
            self.assertFalse(panel.controls.voice.isEnabled())
            self.assertFalse(panel.controls.instruction.isEnabled())
            panel.controls.text.setPlainText("One calm morning.")
            self.assertEqual(panel.request().payload(), {
                "text": "One calm morning.", "voice": "Uncle_Fu", "language": "English",
                "model": "0.6B", "instruction": "",
            })
            panel.controls.model.setCurrentIndex(1)
            self.assertFalse(panel.controls.instruction.isEnabled())
            self.assertEqual(panel.controls.language.count(), 1)
            self.assertFalse(panel.controls.language.isEnabled())
            panel.controls.set_busy(True)
            panel.controls.set_busy(False)
            self.assertEqual(panel.controls.language.currentData(), "English")
            self.assertFalse(panel.controls.language.isEnabled())

    def test_given_empty_script_then_preview_reports_validation_without_starting_worker(self):
        with TemporaryDirectory() as directory:
            panel = self.make_panel(directory)
            panel.test_voice()
            self.assertFalse(panel.busy)
            self.assertIn("Paste narration", panel.controls.status.text())

    def test_given_preview_then_playable_audio_is_not_emitted_as_video_narration(self):
        with TemporaryDirectory() as directory, patch("src.ui.narration_panel.AudioPreview.play") as play:
            panel = self.make_panel(directory)
            emitted = []
            panel.narrationReady.connect(emitted.append)
            panel.controls.text.setPlainText("One calm morning. " * 100)
            panel.test_voice()
            self.assertTrue(panel.busy)
            self.wait_for_completion(panel)
            self.assertEqual(emitted, [])
            self.assertEqual(Path(play.call_args.args[0]).parent.name, "previews")

    def test_given_full_generation_then_callback_waits_for_complete_current_audio(self):
        with TemporaryDirectory() as directory:
            panel = self.make_panel(directory)
            emitted, callbacks = [], []
            panel.narrationReady.connect(emitted.append)
            panel.controls.text.setPlainText("One calm morning.")
            panel.request_full(lambda: callbacks.append("render"))
            self.assertEqual(callbacks, [])
            self.wait_for_completion(panel)
            self.assertEqual(callbacks, ["render"])
            self.assertTrue(Path(emitted[0]).is_file())
            self.assertEqual(Path(emitted[0]).parent.name, "generated")
            self.assertTrue(panel.controls.use_text.isChecked())
            panel.controls.text.setPlainText("A different story.")
            panel.request_full()
            self.wait_for_completion(panel)
            self.assertNotEqual(emitted[0], emitted[1])

    def test_given_engine_failure_then_render_not_started_and_controls_recover(self):
        class FailingSpeech:
            def synthesize(self, *args):
                raise RuntimeError("Model download failed")

        with TemporaryDirectory() as directory:
            panel = self.make_panel(directory)
            panel.service_factory = lambda: NarrationService(Path(directory), FailingSpeech())
            panel.controls.text.setPlainText("One calm morning.")
            callback = []
            panel.request_full(lambda: callback.append("render"))
            self.wait_for_completion(panel)
            self.assertEqual(callback, [])
            self.assertIn("Model download failed", panel.controls.status.text())
            self.assertTrue(panel.controls.generate.isEnabled())

    def test_given_cancelled_generation_then_no_narration_or_render_is_selected(self):
        class BlockingSpeech:
            def __init__(self):
                self.started, self.release = Event(), Event()

            def cancel(self):
                self.release.set()

            def synthesize(self, request, chunks, output, progress, cancelled):
                self.started.set()
                self.release.wait(2)
                if cancelled():
                    raise InterruptedError("Narration generation cancelled.")
                raise RuntimeError("Cancellation was not requested.")

        with TemporaryDirectory() as directory:
            adapter = BlockingSpeech()
            panel = self.make_panel(directory)
            panel.service_factory = lambda: NarrationService(Path(directory), adapter)
            emitted, callback = [], []
            panel.narrationReady.connect(emitted.append)
            panel.controls.text.setPlainText("One calm morning.")
            panel.request_full(lambda: callback.append("render"))
            self.assertTrue(adapter.started.wait(1))
            panel.cancel()
            self.wait_for_completion(panel)
            self.assertEqual(emitted, [])
            self.assertEqual(callback, [])
            self.assertIn("cancelled", panel.controls.status.text())
            self.assertEqual(list(Path(directory).rglob("*.wav")), [])

    def test_given_both_video_modes_then_text_narration_replaces_only_active_audio(self):
        from src.ui.main_window import VideoGeneratorApp
        window = VideoGeneratorApp()
        self.addCleanup(window.deleteLater)
        for index in (0, 1):
            window.mode_combo.setCurrentIndex(index)
            window.c_fields["in_narr"].setText("classic-original.wav")
            window.s_fields["in_narr"].setText("story-original.wav")
            window.narration.narrationReady.emit("generated.wav")
            active = window.s_fields if index else window.c_fields
            inactive = window.c_fields if index else window.s_fields
            self.assertEqual(active["in_narr"].text(), "generated.wav")
            self.assertNotEqual(inactive["in_narr"].text(), "generated.wav")
        window.narration.controls.use_text.setChecked(True)
        with patch.object(window.narration, "request_full") as request:
            window.start_rendering()
            request.assert_called_once()
        self.assertTrue(callable(request.call_args.args[0]))

    def test_given_new_window_then_classic_and_text_narration_are_selected(self):
        from src.ui.main_window import VideoGeneratorApp
        window = VideoGeneratorApp()
        self.addCleanup(window.deleteLater)
        self.assertEqual(window.mode_combo.currentIndex(), 0)
        self.assertEqual(window.stack.currentIndex(), 0)
        self.assertTrue(window.narration.controls.use_text.isChecked())
        self.assertTrue(window.c_fields["subtitles"].isChecked())


if __name__ == "__main__":
    unittest.main()
