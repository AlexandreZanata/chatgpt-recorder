"""Stale-app safety contract from docs/LOCAL-NARRATION.md."""

import unittest

from src.core.narration import NARRATION_PROFILE
from src.engine.qwen_runner import validate_profile


class TestSpeechProfile(unittest.TestCase):
    def test_given_current_reference_profile_then_worker_accepts_the_job(self):
        self.assertIsNone(validate_profile({"profile": NARRATION_PROFILE}))

    def test_given_old_or_missing_profile_then_worker_requests_restart_before_synthesis(self):
        for packet in ({}, {"profile": "qwen-uncle-fu-seed321-single-v2"}, {"profile": "another-reference"}):
            with self.subTest(packet=packet), self.assertRaisesRegex(ValueError, "Restart"):
                validate_profile(packet)


if __name__ == "__main__":
    unittest.main()
