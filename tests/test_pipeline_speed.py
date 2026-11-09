"""Quality-preserving speed contracts from local narration and Standard-mode docs."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import wave

from src.core.narration import SpeechRequest
from src.engine.audio_mixer import get_audio_duration
from src.engine.narration_service import NarrationService
from src.engine.video_composer import build_single_pass_command
from tests.test_local_narration import FakeSpeech


class TestPipelineSpeed(unittest.TestCase):
    def test_given_fooocus_parent_then_speech_uses_only_its_own_gpu_libraries(self):
        from src.engine.gpu_environment import speech_environment
        with TemporaryDirectory() as directory:
            root = Path(directory)
            library = root / "lib/python3.12/site-packages/nvidia/cudnn/lib"
            library.mkdir(parents=True)
            inherited = {"LD_LIBRARY_PATH": "/foreign/Fooocus/nvidia/cudnn/lib",
                         "HF_HOME": "/other/cache", "KEEP_ME": "yes"}
            actual = speech_environment(root / "bin/python", inherited)
            self.assertEqual(actual["LD_LIBRARY_PATH"], str(library))
            self.assertEqual(actual["KEEP_ME"], "yes")
            self.assertEqual(inherited["LD_LIBRARY_PATH"], "/foreign/Fooocus/nvidia/cudnn/lib")

    def test_given_complete_preview_then_full_narration_reuses_exact_audio(self):
        with TemporaryDirectory() as directory:
            adapter = FakeSpeech()
            service = NarrationService(Path(directory), adapter)
            request = SpeechRequest("A quiet morning begins.")
            preview = service.generate(request, preview=True)
            full = service.generate(request)
            self.assertEqual(len(adapter.calls), 1)
            self.assertEqual(preview.read_bytes(), full.read_bytes())
            self.assertEqual(full.parent.name, "generated")

    def test_given_changed_model_then_complete_preview_is_not_reused(self):
        with TemporaryDirectory() as directory:
            adapter = FakeSpeech()
            service = NarrationService(Path(directory), adapter)
            service.generate(SpeechRequest("A quiet morning begins."), preview=True)
            service.generate(SpeechRequest("A quiet morning begins.", model="1.7B"))
            self.assertEqual(len(adapter.calls), 2)

    def test_given_wav_then_duration_is_exact_without_starting_ffmpeg(self):
        with TemporaryDirectory() as directory:
            source = Path(directory) / "voice.wav"
            with wave.open(str(source), "wb") as output:
                output.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
                output.writeframes(b"\0\0" * 24001)
            with patch("src.engine.audio_mixer.subprocess.run") as run:
                self.assertEqual(get_audio_duration(source), 24001 / 24000)
                run.assert_not_called()

    def test_given_static_background_then_repeat_scaled_frames_before_subtitle_overlay(self):
        with TemporaryDirectory() as directory:
            subtitle = Path(directory) / "voice.ass"
            subtitle.touch()
            cmd = build_single_pass_command(Path("image.png"), Path("voice.wav"), None,
                                            subtitle, Path("out.mp4"), fps=15)
            self.assertEqual(cmd[cmd.index("-framerate") + 1], "1")
            filters = cmd[cmd.index("-filter_complex") + 1]
            self.assertLess(filters.index("fps=15"), filters.index("subtitles="))
            self.assertEqual(cmd[cmd.index("-qp") + 1], "28")

    def test_given_animated_background_then_no_frame_decimation_is_added(self):
        cmd = build_single_pass_command(Path("loop.mp4"), Path("voice.wav"), None, None,
                                        Path("out.mp4"), fps=30, background_is_video=True)
        self.assertNotIn("-framerate", cmd)
        self.assertNotIn("fps=", cmd[cmd.index("-filter_complex") + 1])
        self.assertEqual(cmd[cmd.index("-r") + 1], "30")


if __name__ == "__main__":
    unittest.main()
