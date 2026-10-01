"""Loop continuity and background-precedence contracts from docs/STANDARD-MODE.md."""

import unittest
from pathlib import Path

import numpy as np

from src.engine.particle_art import LOOP_SECONDS, ParticleLoop
from src.engine.standard_backgrounds import resolve_standard_background

THEMES = ("religious", "black", "agro", "fallem_prince")


class TestParticleBackgrounds(unittest.TestCase):
    def test_given_fractional_motion_then_glow_moves_without_whole_pixel_stalls(self):
        """Contract: 0.1-pixel shifts remain visible and monotonic in every theme."""
        from src.engine.particle_render import composite_particle
        centroids = []
        frames = []
        for x in (15.1, 15.2, 15.3):
            frame = np.zeros((32, 32, 3), dtype=np.float32)
            composite_particle(frame, x, 16, 2.0, 160.0, (255, 255, 255))
            frames.append(frame.astype(np.uint8).tobytes())
            light = frame[..., 0]
            centroids.append(float((light * np.arange(32)).sum() / light.sum()))
        self.assertEqual(len(set(frames)), 3)
        self.assertGreater(centroids[1], centroids[0])
        self.assertGreater(centroids[2], centroids[1])
        self.assertAlmostEqual(centroids[1] - centroids[0], 0.1, delta=0.025)

    def test_given_fractional_brightness_then_glow_does_not_quantize_into_steps(self):
        """Contract: small brightness changes remain continuous before video encoding."""
        from src.engine.particle_render import composite_particle
        frames = []
        for opacity in (100.1, 100.2, 100.3):
            frame = np.zeros((32, 32, 3), dtype=np.float32)
            composite_particle(frame, 16.25, 16.25, 2.0, opacity, (255, 255, 255))
            frames.append(frame)
        self.assertTrue(np.any(frames[0] != frames[1]))
        self.assertTrue(np.all(frames[1] >= frames[0]))
        self.assertTrue(np.any(frames[1] != frames[2]))

    def test_given_each_theme_then_one_full_cycle_returns_exactly_to_initial_frame(self):
        for theme in THEMES:
            with self.subTest(theme=theme):
                loop = ParticleLoop(theme, width=320, height=180)
                self.assertEqual(loop.frame(0).tobytes(), loop.frame(LOOP_SECONDS).tobytes())
                self.assertNotEqual(loop.frame(0).tobytes(), loop.frame(2).tobytes())

    def test_given_loop_boundary_then_adjacent_frames_have_no_reset_jump(self):
        for theme in THEMES:
            with self.subTest(theme=theme):
                loop = ParticleLoop(theme, width=320, height=180)
                end = np.asarray(loop.frame(LOOP_SECONDS - 1 / 30), dtype=float)
                start = np.asarray(loop.frame(0), dtype=float)
                next_frame = np.asarray(loop.frame(1 / 30), dtype=float)
                seam_change = np.abs(end - start).mean()
                regular_change = np.abs(next_frame - start).mean()
                self.assertLessEqual(seam_change, max(0.25, regular_change * 3))

    def test_given_custom_image_without_theme_then_resolver_keeps_image(self):
        image = Path("custom.webp")
        self.assertEqual(resolve_standard_background(image), (image, False))

    def test_given_selected_theme_then_resolver_ignores_missing_custom_image(self):
        for theme in THEMES:
            with self.subTest(theme=theme):
                background, is_video = resolve_standard_background(Path("missing-image.png"), theme)
                self.assertTrue(background.is_file())
                self.assertTrue(is_video)
                self.assertEqual(background.suffix, ".mp4")

    def test_given_unknown_theme_then_resolver_reports_invalid_selection(self):
        with self.assertRaises(ValueError):
            resolve_standard_background(Path("image.png"), "unknown")


if __name__ == "__main__":
    unittest.main()
