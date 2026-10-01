"""Automatic portrait backgrounds: contracts from docs/STANDARD-MODE.md."""

import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from src.core.standard_video_worker import RenderWorker
from src.engine.particle_art import LOOP_SECONDS, ParticleLoop
from src.engine.standard_backgrounds import resolve_standard_background
from src.ui.main_window import VideoGeneratorApp

THEMES = {
    "religious": "religious_particles_shorts.mp4",
    "black": "enigmatic_black_shorts.mp4",
    "agro": "zaflas_agro_shorts.mp4",
    "fallem_prince": "fallem_prince_shorts.mp4",
}


class TestShortBackgrounds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_given_portrait_selection_then_each_theme_uses_a_dedicated_background(self):
        for theme, expected in THEMES.items():
            with self.subTest(theme=theme):
                portrait, is_video = resolve_standard_background(Path("missing.png"), theme, portrait=True)
                landscape, _ = resolve_standard_background(Path("missing.png"), theme)
                self.assertEqual(portrait.name, expected)
                self.assertTrue(portrait.is_file())
                self.assertTrue(is_video)
                self.assertNotEqual(portrait, landscape)

    def test_given_portrait_without_theme_then_custom_image_is_preserved(self):
        image = Path("custom.webp")
        self.assertEqual(resolve_standard_background(image, portrait=True), (image, False))

    def test_given_short_preset_then_worker_uses_portrait_and_no_landscape_outro(self):
        for theme, expected in THEMES.items():
            with self.subTest(theme=theme), \
                 patch("src.core.standard_video_worker.get_audio_duration", return_value=10), \
                 patch("src.core.standard_video_worker.render_single_pass_video", return_value=True) as render:
                RenderWorker(Path("missing.png"), Path("voice.wav"), None, Path("out.mp4"),
                             2.0, 0.15, "YouTube Shorts / Reels (9:16)",
                             has_subtitles=False, background_theme=theme).run()
                self.assertEqual(render.call_args.args[0].name, expected)
                self.assertEqual(render.call_args.kwargs["width"], 1080)
                self.assertEqual(render.call_args.kwargs["height"], 1920)
                self.assertEqual(render.call_args.kwargs["total_duration"], 10)
                self.assertEqual(render.call_args.kwargs["fps"], 30)

    def test_given_preset_switch_then_ui_preserves_theme_and_validates_matching_assets(self):
        window = VideoGeneratorApp()
        with TemporaryDirectory() as directory:
            narration = Path(directory) / "voice.wav"
            narration.touch()
            window.c_fields["in_narr"].setText(str(narration))
            window.c_fields["in_img"].setText("missing.png")
            window.no_bgm_cb.setChecked(True)
            for theme in THEMES:
                window.c_fields["background_checks"][theme].setChecked(True)
                for preset in (1, 0, 1):
                    window.c_fields["preset"].setCurrentIndex(preset)
                    worker = window._make_standard_worker(Path(directory) / "out.mp4")
                    self.assertIsNotNone(worker)
                    self.assertEqual(worker.background_theme, theme)
                    self.assertEqual(worker.preset, window.c_fields["preset"].currentText())
        window.close()

    def test_given_portrait_particles_then_motion_remains_seamless_and_continuous(self):
        for theme in THEMES:
            with self.subTest(theme=theme):
                loop = ParticleLoop(theme, width=180, height=320)
                self.assertEqual(loop.frame(0).size, (180, 320))
                self.assertEqual(loop.frame(0).tobytes(), loop.frame(LOOP_SECONDS).tobytes())
                self.assertNotEqual(loop.frame(6).tobytes(), loop.frame(6 + 1/30).tobytes())

    def test_given_only_portrait_asset_then_short_ui_does_not_require_landscape_asset(self):
        """Contract: Shorts input validation uses the portrait background itself."""
        window = VideoGeneratorApp()
        with TemporaryDirectory() as directory, \
             patch("src.engine.standard_backgrounds.BACKGROUND_DIR", Path(directory)):
            (Path(directory) / "religious_particles_shorts.mp4").touch()
            narration = Path(directory) / "voice.wav"
            narration.touch()
            window.c_fields["in_narr"].setText(str(narration))
            window.c_fields["in_img"].setText("missing.png")
            window.c_fields["background_checks"]["religious"].setChecked(True)
            window.c_fields["preset"].setCurrentIndex(1)
            window.no_bgm_cb.setChecked(True)
            self.assertIsNotNone(window._make_standard_worker(Path(directory) / "out.mp4"))
            window.c_fields["preset"].setCurrentIndex(0)
            self.assertIsNone(window._make_standard_worker(Path(directory) / "out.mp4"))
        window.close()


if __name__ == "__main__":
    unittest.main()
