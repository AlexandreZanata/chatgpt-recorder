"""Standard-mode contracts from docs/STANDARD-MODE.md."""

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication, QFormLayout, QWidget
from src.engine.video_composer import build_single_pass_command
from src.ui.mode_views import create_classic_fields


class TestStandardMode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def fields(self):
        self.widget = QWidget()
        return create_classic_fields(QFormLayout(self.widget), lambda *args: None,
                                     Path("imagens"), Path("audio"), Path("background-music"))

    def test_given_standard_mode_then_subtitles_default_on_and_can_be_disabled(self):
        fields = self.fields()
        self.assertTrue(fields["subtitles"].isChecked())
        fields["subtitles"].setChecked(False)
        self.assertFalse(fields["subtitles"].isChecked())

    def test_given_particle_theme_then_selection_overrides_image_and_is_mutually_exclusive(self):
        fields = self.fields()
        fields["in_img"].setText("original.png")
        religion = fields["background_checks"]["religious"]
        black = fields["background_checks"]["black"]
        self.assertFalse(religion.isChecked())
        religion.setChecked(True)
        self.assertFalse(fields["in_img"].isEnabled())
        black.setChecked(True)
        self.assertFalse(religion.isChecked())
        black.setChecked(False)
        self.assertTrue(fields["in_img"].isEnabled())
        self.assertEqual(fields["in_img"].text(), "original.png")

    def test_given_channel_themes_then_all_four_choices_are_exclusive_and_optional(self):
        """Contract: new channel themes preserve both existing Standard backgrounds."""
        from src.ui.standard_controls import selected_standard_theme
        fields = self.fields()
        checks = fields["background_checks"]
        self.assertEqual(set(checks), {"religious", "black", "agro", "fallem_prince"})
        self.assertTrue(all(not checkbox.isChecked() for checkbox in checks.values()))
        for name, checkbox in checks.items():
            checkbox.setChecked(True)
            self.assertEqual(selected_standard_theme(fields), name)
            self.assertEqual(sum(other.isChecked() for other in checks.values()), 1)
            self.assertFalse(fields["in_img"].isEnabled())
        checkbox.setChecked(False)
        self.assertEqual(selected_standard_theme(fields), "")
        self.assertTrue(fields["in_img"].isEnabled())

    def test_given_subtitles_then_composer_burns_them_into_video(self):
        with TemporaryDirectory() as directory:
            subtitle = Path(directory) / "narration.ass"
            subtitle.touch()
            cmd = build_single_pass_command(Path("image.png"), Path("voice.wav"), None,
                                            subtitle, Path("out.mp4"))
            vf = cmd[cmd.index("-filter_complex") + 1]
            self.assertIn("subtitles=", vf)
            self.assertIn("narration.ass", vf)

    def test_given_loop_background_then_composer_repeats_video_and_fills_frame(self):
        cmd = build_single_pass_command(Path("loop.mp4"), Path("voice.wav"), None, None,
                                        Path("out.mp4"), background_is_video=True)
        self.assertNotIn("-loop", cmd)
        self.assertEqual(cmd[cmd.index("-stream_loop") + 1], "-1")
        vf = cmd[cmd.index("-filter_complex") + 1]
        self.assertIn("force_original_aspect_ratio=increase", vf)
        self.assertIn("crop=1920:1080", vf)

    def test_given_subtitles_disabled_then_worker_skips_transcription_and_preserves_outro(self):
        from src.core.standard_video_worker import RenderWorker
        with patch("src.core.standard_video_worker.transcribe_audio_to_segments") as transcribe, \
             patch("src.core.standard_video_worker.get_audio_duration", return_value=10), \
             patch("src.core.standard_video_worker.render_single_pass_video", return_value=True) as render:
            worker = RenderWorker(Path("image.png"), Path("voice.wav"), None,
                                  Path("out.mp4"), 2.0, 0.15, "YouTube Standard (16:9)",
                                  has_subtitles=False)
            worker.run()
            transcribe.assert_not_called()
            self.assertIsNone(render.call_args.args[3])
            self.assertEqual(render.call_args.kwargs["total_duration"], 40)

    def test_given_enabled_subtitles_then_worker_passes_timestamped_narration_to_renderer(self):
        from src.core.standard_video_worker import RenderWorker
        segments = [{"start": 0.2, "end": 2.0, "text": "Faith and hope"}]
        observed = []

        def capture(*args, **kwargs):
            observed.append(args[3].read_text())
            return True

        with patch("src.core.standard_video_worker.transcribe_audio_to_segments", return_value=segments), \
             patch("src.core.standard_video_worker.get_audio_duration", return_value=10), \
             patch("src.core.standard_video_worker.render_single_pass_video", side_effect=capture):
            RenderWorker(Path("image.png"), Path("voice.wav"), None, Path("out.mp4"),
                         2.0, 0.15, "YouTube Standard (16:9)").run()
        self.assertIn("0:00:00.20,0:00:02.00", observed[0])
        self.assertIn("Faith and hope", observed[0])

    def test_given_selected_theme_without_image_then_worker_renders_loop(self):
        from src.core.standard_video_worker import RenderWorker
        with patch("src.core.standard_video_worker.get_audio_duration", return_value=10), \
             patch("src.core.standard_video_worker.render_single_pass_video", return_value=True) as render:
            RenderWorker(Path("missing.png"), Path("voice.wav"), None, Path("out.mp4"),
                         2.0, 0.15, "YouTube Standard (16:9)", has_subtitles=False,
                         background_theme="religious").run()
        self.assertEqual(render.call_args.args[0].name, "religious_particles.mp4")
        self.assertTrue(render.call_args.kwargs["background_is_video"])
        self.assertEqual(render.call_args.kwargs["fps"], 30)

    def test_given_standard_subtitles_then_text_is_large_and_centered_in_both_formats(self):
        """Contract: large, centered text draws attention in landscape and portrait."""
        from src.core.standard_video_worker import RenderWorker
        segments = [{"start": 0.2, "end": 2.0, "text": "Faith and hope"}]
        for width, height in ((1920, 1080), (1080, 1920)):
            with self.subTest(width=width, height=height), TemporaryDirectory() as directory, \
                 patch("src.core.standard_video_worker.transcribe_audio_to_segments", return_value=segments):
                worker = RenderWorker(Path("image.png"), Path("voice.wav"), None,
                                      Path("out.mp4"), 2.0, 0.15, "YouTube Standard (16:9)")
                content = worker._subtitle_file(Path(directory), width, height).read_text()
                style_format = next(line for line in content.splitlines() if line.startswith("Format: Name,"))
                style = next(line for line in content.splitlines() if line.startswith("Style: Default,"))
                attributes = dict(zip(style_format.removeprefix("Format: ").split(", "),
                                      style.removeprefix("Style: ").split(",")))
                self.assertEqual(attributes["Alignment"], "5")
                self.assertGreaterEqual(int(attributes["Fontsize"]), 84)
                self.assertEqual(attributes["Bold"], "1")
                self.assertGreaterEqual(float(attributes["Outline"]), 3)
                self.assertIn("0:00:00.20,0:00:02.00", content)

    def test_given_channel_background_then_worker_exports_bundled_loop_without_custom_image(self):
        """Contract: both channel themes use the existing Standard video workflow."""
        from src.core.standard_video_worker import RenderWorker
        for theme, filename in (("agro", "zaflas_agro.mp4"),
                                ("fallem_prince", "fallem_prince.mp4")):
            with self.subTest(theme=theme), \
                 patch("src.core.standard_video_worker.get_audio_duration", return_value=10), \
                 patch("src.core.standard_video_worker.render_single_pass_video", return_value=True) as render:
                RenderWorker(Path("missing.png"), Path("voice.wav"), None, Path("out.mp4"),
                             2.0, 0.15, "YouTube Standard (16:9)", has_subtitles=False,
                             background_theme=theme).run()
                self.assertEqual(render.call_args.args[0].name, filename)
                self.assertTrue(render.call_args.kwargs["background_is_video"])
                self.assertEqual(render.call_args.kwargs["total_duration"], 40)

    def test_given_transcription_failure_then_enabled_subtitles_report_error(self):
        from src.core.standard_video_worker import RenderWorker
        with patch("src.core.standard_video_worker.get_audio_duration", return_value=10), \
             patch("src.core.standard_video_worker.transcribe_audio_to_segments", return_value=[]), \
             patch("src.core.standard_video_worker.render_single_pass_video") as render:
            worker = RenderWorker(Path("image.png"), Path("voice.wav"), None,
                                  Path("out.mp4"), 2.0, 0.15, "YouTube Standard (16:9)")
            results = []
            worker.finished.connect(lambda ok, message: results.append((ok, message)))
            worker.run()
        render.assert_not_called()
        self.assertFalse(results[0][0])
        self.assertIn("disable subtitles", results[0][1])


if __name__ == "__main__":
    unittest.main()
