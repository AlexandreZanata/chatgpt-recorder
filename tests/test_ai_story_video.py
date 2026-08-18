"""Unit tests for the new AI Story Video generator pipeline."""

import unittest
from pathlib import Path

from src.core.ai_transcriber import format_timestamp_srt
from src.core.ai_scene_planner import plan_scenes_from_duration, clean_narrative_excerpt
from src.core.motion_renderer import build_ken_burns_filter, assign_random_motions
from src.core.sdxl_batch_generator import get_available_checkpoints


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
        self.assertIn("1920:1080", f_in)

        f_out = build_ken_burns_filter("zoom_out", 5.0)
        self.assertIn("zoompan", f_out)

    def test_assign_random_motions(self):
        scenes = [{"id": 1}, {"id": 2}, {"id": 3}]
        res = assign_random_motions(scenes)
        for s in res:
            self.assertIn("motion_type", s)


if __name__ == "__main__":
    unittest.main()
