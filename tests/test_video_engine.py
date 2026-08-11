"""Unit tests for Video Engine Core (audio mixer, video composer, subtitle generator)."""

import unittest
from pathlib import Path

from src.engine.audio_mixer import build_audio_mix_command
from src.engine.subtitle_generator import format_ass_time, generate_ass_content
from src.engine.video_composer import build_single_pass_command


class TestVideoEngine(unittest.TestCase):
    """Test suite for video rendering and audio mixing commands."""

    def test_audio_mix_command_structure(self):
        narr = Path("/tmp/narr.wav")
        bgm = Path("/tmp/bgm.wav")
        out = Path("/tmp/out.wav")
        cmd = build_audio_mix_command(narr, None, out, narration_volume=1.0)
        self.assertIn("ffmpeg", cmd)
        self.assertIn("-af", cmd)
        self.assertIn("volume=1.0", cmd)

    def test_video_composer_nvenc_command(self):
        img = Path("/tmp/img.png")
        audio = Path("/tmp/audio.wav")
        out = Path("/tmp/out.mp4")
        cmd = build_single_pass_command(img, audio, None, None, out, width=1920, height=1080)
        self.assertIn("h264_nvenc", cmd)
        self.assertIn("-preset", cmd)
        self.assertIn("p1", cmd)

    def test_ass_subtitle_formatting(self):
        self.assertEqual(format_ass_time(0.0), "0:00:00.00")
        self.assertEqual(format_ass_time(65.5), "0:01:05.50")
        segs = [{"start": 1.0, "end": 4.5, "text": "Hello world"}]
        ass_text = generate_ass_content(segs)
        self.assertIn("[Script Info]", ass_text)
        self.assertIn("Dialogue: 0,0:00:01.00,0:00:04.50,Default,,0,0,0,,Hello world", ass_text)


if __name__ == "__main__":
    unittest.main()
