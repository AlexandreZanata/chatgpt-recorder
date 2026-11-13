"""Contract: bot subtitles use the selected channel's explicit language."""

import unittest
from unittest.mock import patch

from tools.ytbot import channels, render


class NarrationLanguageTests(unittest.TestCase):
    def tearDown(self):
        channels.apply("fallem-prince")

    def test_zaflas_recognizes_portuguese_without_translation(self):
        channels.apply("zaflas")
        expected = [{"start": 0, "end": 2, "text": "Conhecimento para o campo."}]
        with patch("src.core.ai_transcriber.cached_transcription", return_value=expected) as cache:
            result = render.transcribe_narration("narration.aac")
        self.assertEqual(result, expected)
        self.assertEqual(cache.call_args.args[2], "pt")

    def test_fallem_prince_keeps_english_recognition(self):
        channels.apply("fallem-prince")
        with patch("src.core.ai_transcriber.cached_transcription", return_value=[]) as cache:
            render.transcribe_narration("narration.aac")
        self.assertEqual(cache.call_args.args[2], "en")


if __name__ == "__main__":
    unittest.main()
