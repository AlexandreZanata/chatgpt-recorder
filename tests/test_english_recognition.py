"""English-only recognition contracts from docs/LOCAL-NARRATION.md."""

from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from src.core.ai_transcriber import transcribe_audio_to_segments, _transcribe_uncached


class TestEnglishRecognition(unittest.TestCase):
    def test_given_no_language_or_none_then_cache_and_engine_receive_english(self):
        with patch("src.core.ai_transcriber.cached_transcription", return_value=[]) as cached:
            transcribe_audio_to_segments("voice.wav")
            self.assertEqual(cached.call_args.args[2], "en")
            transcribe_audio_to_segments("voice.wav", language=None)
            self.assertEqual(cached.call_args.args[2], "en")

    def test_given_non_english_language_then_rejected_before_cache_or_inference(self):
        with patch("src.core.ai_transcriber.cached_transcription") as cached:
            for language in ("pt", "auto", "ja"):
                with self.subTest(language=language), self.assertRaisesRegex(ValueError, "English"):
                    transcribe_audio_to_segments("voice.wav", language=language)
            cached.assert_not_called()

    def test_given_english_recognition_then_whisper_receives_explicit_english(self):
        model = Mock()
        model.transcribe.return_value = ([], SimpleNamespace(language="en"))
        whisper = SimpleNamespace(WhisperModel=Mock(return_value=model))
        torch = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False))
        with patch.dict("sys.modules", {"faster_whisper": whisper, "torch": torch}):
            self.assertEqual(_transcribe_uncached("voice.wav", "large-v3-turbo", "en", False), [])
        self.assertEqual(model.transcribe.call_args.kwargs["language"], "en")
        self.assertTrue(model.transcribe.call_args.kwargs["vad_filter"])
        self.assertEqual(model.transcribe.call_args.kwargs["beam_size"], 1)


if __name__ == "__main__":
    unittest.main()
