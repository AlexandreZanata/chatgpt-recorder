"""Unit tests for the new AI Story Video generator pipeline."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.core.ai_transcriber import format_timestamp_srt
from src.core.ai_scene_planner import plan_scenes_from_duration, clean_narrative_excerpt
from src.core.generation_profiles import get_generation_profile
from src.core.motion_renderer import (
    apply_motion_preference,
    assign_random_motions,
    build_cinematic_transition_filter,
    build_ken_burns_filter,
)
from src.core.sdxl_batch_generator import get_available_checkpoints
from src.core.storyboard_composer import assemble_clips_to_video


class TestAIStoryVideoPipeline(unittest.TestCase):
    """Test suite for Whisper timestamps, scene planner, Ken Burns motion, and SDXL models."""

    def test_format_timestamp_srt(self):
        self.assertEqual(format_timestamp_srt(0.0), "00:00:00,000")
        self.assertEqual(format_timestamp_srt(65.5), "00:01:05,500")
        self.assertEqual(format_timestamp_srt(3661.123), "01:01:01,123")

    def test_clean_narrative_excerpt(self):
        text = "The luxury supercar drives along the sunny ocean boulevard in Miami."
        res = clean_narrative_excerpt(text)
        self.assertIn("supercar", res)
        self.assertIn("Miami", res)

    def test_plan_scenes_from_duration(self):
        scenes = plan_scenes_from_duration(
            total_duration_sec=180.0,
            interval_sec=60.0,
            master_theme="Cinematic Miami Luxury"
        )
        self.assertEqual(len(scenes), 3)
        self.assertEqual(scenes[0]["duration_sec"], 60.0)
        self.assertEqual(scenes[1]["start_sec"], 60.0)
        self.assertEqual(scenes[2]["end_sec"], 180.0)
        self.assertTrue(scenes[0]["prompt"].startswith("A vivid cinematic photograph"))

    def test_ken_burns_filters(self):
        f_in = build_ken_burns_filter("zoom_in", 5.0)
        self.assertIn("zoompan", f_in)
        self.assertIn("1920x1080", f_in)

        f_out = build_ken_burns_filter("zoom_out", 5.0)
        self.assertIn("zoompan", f_out)

        f_pan = build_ken_burns_filter("pan_right", 5.0)
        self.assertIn("zoompan", f_pan)

        f_tilt = build_ken_burns_filter("tilt_up", 5.0)
        self.assertIn("zoompan", f_tilt)

    def test_given_long_scene_when_zooming_then_motion_is_eased_and_visible(self):
        """Contract: AI Story motion remains perceptible and uses smooth acceleration."""
        result = build_ken_burns_filter("zoom_in", 30.0)
        self.assertIn("3-2*", result)
        self.assertIn("0.1600", result)

    def test_given_scene_when_rendering_then_transition_fades_both_edges(self):
        """Contract: scene boundaries transition inline without a second render pass."""
        result = build_cinematic_transition_filter(10.0)
        self.assertIn("fade=t=in:st=0:d=0.400", result)
        self.assertIn("fade=t=out:st=9.600:d=0.400", result)

    def test_given_motion_disabled_when_preparing_scenes_then_frames_are_static(self):
        """Contract: the AI Story motion checkbox controls every planned scene."""
        scenes = [{"motion_type": "zoom_in"}, {"motion_type": "pan_left"}]
        result = apply_motion_preference(scenes, enabled=False)
        self.assertEqual([scene["motion_type"] for scene in result], ["static", "static"])
        self.assertIn("z='1.0'", build_ken_burns_filter("static", 5.0))

    def test_given_preencoded_scenes_when_assembling_then_video_is_stream_copied(self):
        """Contract: inline motion and transitions must not trigger a second video encode."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            clip, audio, output = root / "clip.mp4", root / "audio.wav", root / "out.mp4"
            clip.touch()
            audio.touch()
            with patch("src.core.storyboard_composer.subprocess.run") as run:
                assemble_clips_to_video([clip], str(audio), str(output))
            command = run.call_args.args[0]
            codec_index = command.index("-c:v")
            self.assertEqual(command[codec_index + 1], "copy")

    def test_assign_random_motions(self):
        scenes = [{"id": 1}, {"id": 2}, {"id": 3}]
        res = assign_random_motions(scenes)
        for s in res:
            self.assertIn("motion_type", s)

    def test_slice_srt_for_window(self):
        from src.core.ai_transcriber import slice_srt_for_window
        import tempfile
        segments = [
            {"start": 10.0, "end": 20.0, "text": "First segment"},
            {"start": 25.0, "end": 35.0, "text": "Crossing boundary"},
            {"start": 40.0, "end": 50.0, "text": "Third segment"}
        ]
        with tempfile.NamedTemporaryFile(suffix=".srt", delete=False) as tf:
            tf_path = tf.name

        # Scene 1: 0 to 30s
        res = slice_srt_for_window(segments, 0.0, 30.0, tf_path)
        self.assertIsNotNone(res)
        content = Path(tf_path).read_text(encoding="utf-8")
        self.assertIn("First segment", content)
        self.assertIn("Crossing boundary", content)
        self.assertNotIn("Third segment", content)
        Path(tf_path).unlink(missing_ok=True)

    def test_theme_visual_bibles_and_models(self):
        from src.core.ai_scene_planner import build_visual_bible
        from src.core.sdxl_batch_generator import get_model_for_theme

        b_black = build_visual_bible("deep black")
        self.assertEqual(b_black["master_theme"], "deep black")
        self.assertIn("monochrome", b_black["color_palette"])
        self.assertEqual(get_model_for_theme("deep black"), "RealVisXL_V5.0_fp16.safetensors")

        b_agro = build_visual_bible("agro zaflas")
        self.assertEqual(b_agro["master_theme"], "agro zaflas")
        self.assertIn("agricultural", b_agro["color_palette"])
        self.assertEqual(get_model_for_theme("agro zaflas"), "juggernautXL_v8Rundiffusion.safetensors")

        b_rel = build_visual_bible("religião primium word")
        self.assertEqual(b_rel["master_theme"], "religião primium word")
        self.assertIn("golden", b_rel["lighting"])
        self.assertIn("amber", b_rel["color_palette"])
        self.assertIn("crowd", b_rel["negative_prompt"])
        self.assertEqual(get_model_for_theme("religião primium word"), "RealVisXL_V5.0_fp16.safetensors")

    def test_given_religion_theme_when_selecting_profile_then_use_measured_quality_path(self):
        """Contract: religion alone uses the measured premium DPM++ configuration."""
        profile = get_generation_profile("religião primium word", is_short=False)
        self.assertEqual(profile.sampler, "dpmpp_2m_karras")
        self.assertEqual((profile.steps, profile.guidance_scale), (12, 4.5))
        self.assertEqual(profile.inference_size, (1216, 704))
        self.assertFalse(profile.use_lightning)

    def test_given_other_theme_when_selecting_profile_then_preserve_fast_visual_style(self):
        """Contract: other themes gain resolution while retaining the fast sampler."""
        profile = get_generation_profile("agro zaflas", is_short=True)
        self.assertEqual((profile.steps, profile.guidance_scale), (4, 0.0))
        self.assertEqual(profile.inference_size, (704, 1216))
        self.assertTrue(profile.use_lightning)


if __name__ == "__main__":
    unittest.main()
