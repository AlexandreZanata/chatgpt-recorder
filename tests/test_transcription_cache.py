"""Exact ASR reuse contracts from docs/STANDARD-MODE.md, independent of models."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from src.engine.transcription_cache import cached_transcription

SEGMENTS = [{"id": 0, "start": 0.2, "end": 2.4, "text": "Faith and hope.",
             "avg_logprob": -0.1}]


class TestTranscriptionCache(unittest.TestCase):
    def test_given_identical_audio_then_exact_timestamps_and_text_are_reused(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "voice.wav"
            source.write_bytes(b"audio bytes")
            loader = Mock(return_value=SEGMENTS)
            first = cached_transcription(source, "large-v3-turbo", None, False, loader, root / "cache")
            second = cached_transcription(source, "large-v3-turbo", None, False, loader, root / "cache")
            self.assertEqual(first, SEGMENTS)
            self.assertEqual(second, SEGMENTS)
            self.assertEqual(loader.call_count, 1)
            second[0]["text"] = "Changed by a consumer"
            self.assertEqual(first, SEGMENTS)

    def test_given_changed_audio_or_settings_then_transcription_is_not_reused(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "voice.wav"
            source.write_bytes(b"first recording")
            loader = Mock(return_value=SEGMENTS)
            settings = [("large-v3-turbo", None, False), ("large-v3-turbo", "en", False),
                        ("large-v3-turbo", "en", True), ("small", "en", True)]
            for model, language, words in settings:
                cached_transcription(source, model, language, words, loader, root / "cache")
            source.write_bytes(b"different recording")
            cached_transcription(source, *settings[-1], loader, root / "cache")
            self.assertEqual(loader.call_count, 5)

    def test_given_corrupt_cache_then_original_audio_is_transcribed_again(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "voice.wav"
            source.write_bytes(b"audio bytes")
            loader = Mock(return_value=SEGMENTS)
            cached_transcription(source, "large-v3-turbo", None, False, loader, root / "cache")
            entry = next((root / "cache").glob("*.json"))
            entry.write_text(json.dumps([{"start": 9, "end": 1, "text": "Bad timestamps"}]))
            self.assertEqual(cached_transcription(source, "large-v3-turbo", None, False,
                                                 loader, root / "cache"), SEGMENTS)
            self.assertEqual(loader.call_count, 2)

    def test_given_empty_or_failed_transcription_then_no_success_cache_is_created(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "voice.wav"
            source.write_bytes(b"audio bytes")
            loader = Mock(return_value=[])
            self.assertEqual(cached_transcription(source, "large-v3-turbo", None, False,
                                                 loader, root / "cache"), [])
            self.assertEqual(list((root / "cache").glob("*.json")), [])
            loader.side_effect = RuntimeError("GPU failed")
            with self.assertRaisesRegex(RuntimeError, "GPU failed"):
                cached_transcription(source, "large-v3-turbo", None, False, loader, root / "cache")

    def test_given_engine_version_change_then_previous_result_is_not_reused(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "voice.wav"
            source.write_bytes(b"audio bytes")
            loader = Mock(return_value=SEGMENTS)
            with patch("src.engine.transcription_cache.engine_versions", return_value="old"):
                cached_transcription(source, "large-v3-turbo", None, False, loader, root / "cache")
            with patch("src.engine.transcription_cache.engine_versions", return_value="new"):
                cached_transcription(source, "large-v3-turbo", None, False, loader, root / "cache")
            self.assertEqual(loader.call_count, 2)


if __name__ == "__main__":
    unittest.main()
