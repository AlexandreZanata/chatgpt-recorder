"""Narration contracts from docs/LOCAL-NARRATION.md; no real model required."""

import unittest
import wave
from pathlib import Path
from tempfile import TemporaryDirectory

from src.core.narration import SpeechRequest, split_narration, preview_text
from src.engine.narration_service import NarrationService
from src.engine.qwen_runner import model_location, REQUIRED_MODEL_FILES


class FakeSpeech:
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    def synthesize(self, request, chunks, output, progress, cancelled):
        self.calls.append((request, chunks))
        with wave.open(str(output), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(24000)
            for number, _ in enumerate(chunks):
                if cancelled():
                    raise InterruptedError("Narration generation cancelled.")
                if self.fail:
                    raise RuntimeError("Speech failed.")
                audio.writeframes(b"\0\0" * 240)
                progress(f"Chunk {number + 1}")


class TestNarrationContract(unittest.TestCase):
    def test_given_no_voice_override_then_user_selected_audition_is_default(self):
        request = SpeechRequest("One calm morning.")
        self.assertEqual(request.voice, "Uncle_Fu")
        self.assertEqual(request.model, "0.6B")
        self.assertEqual(request.language, "English")
        with self.assertRaisesRegex(ValueError, "Uncle_Fu"):
            SpeechRequest("One calm morning.", voice="Aiden")

    def test_given_empty_text_then_rejected_before_model_loading(self):
        with self.assertRaisesRegex(ValueError, "text"):
            SpeechRequest("  ")

    def test_given_unknown_voice_language_or_model_then_rejected(self):
        for options in ({"voice": "unknown"}, {"language": "unknown"}, {"model": "unknown"}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                SpeechRequest("Hello", **options)

    def test_given_non_english_or_auto_language_then_rejected_before_inference(self):
        for language in ("Portuguese", "Auto", None):
            with self.subTest(language=language), self.assertRaisesRegex(ValueError, "English"):
                SpeechRequest("One calm morning.", language=language)

    def test_given_previous_multilingual_profile_then_audio_is_not_reused(self):
        import hashlib
        import json
        request = SpeechRequest("One calm morning.")
        payload = json.dumps(request.payload(), sort_keys=True, ensure_ascii=False)
        profile = "qwen-uncle-fu-base-icl-seed321-v3:37c0f7ecb126f36e96723cef6e9f7d6f9efc251879ae9cf5e32981b6399ada76"
        old_key = hashlib.sha256((profile + ":" + payload).encode()).hexdigest()[:24]
        self.assertNotEqual(request.cache_key(), old_key)

    def test_given_long_script_then_all_words_preserved_in_bounded_chunks(self):
        text = ("Faith grows quietly. A new morning begins!\n" * 100).strip()
        chunks = split_narration(text, limit=180)
        self.assertEqual(" ".join(chunks).split(), text.split())
        self.assertTrue(all(len(chunk) <= 180 for chunk in chunks))

    def test_given_unusually_long_word_then_split_without_losing_characters(self):
        text = "x" * 1100
        chunks = split_narration(text, limit=180)
        self.assertEqual("".join(chunks), text)
        self.assertTrue(all(len(chunk) <= 180 for chunk in chunks))

    def test_given_preview_then_excerpt_is_bounded_and_full_text_unchanged(self):
        text = " ".join(f"word{i}" for i in range(300))
        self.assertEqual(preview_text(text).split(), text.split()[:60])
        self.assertEqual(len(SpeechRequest(text).text.split()), 300)

    def test_given_changes_then_reuse_key_changes_except_unsupported_instruction(self):
        base = SpeechRequest("Hello there")
        for options in ({"text": "New text"}, {"model": "1.7B"}):
            args = {"text": "Hello there", **options}
            self.assertNotEqual(base.cache_key(), SpeechRequest(**args).cache_key())
        self.assertEqual(base.cache_key(), SpeechRequest("Hello there", instruction="Warm").cache_key())
        self.assertEqual(SpeechRequest("Hello there", model="1.7B").cache_key(),
                            SpeechRequest("Hello there", model="1.7B", instruction="Warm").cache_key())

    def test_given_old_random_profile_then_it_cannot_reuse_corrected_default_narration(self):
        import hashlib
        import json
        request = SpeechRequest("Hello there")
        payload = json.dumps(request.payload(), sort_keys=True, ensure_ascii=False)
        old_key = hashlib.sha256(("qwen-narration-v1:" + payload).encode()).hexdigest()[:24]
        self.assertNotEqual(request.cache_key(), old_key)

    def test_given_fixed_seed_customvoice_cache_then_it_is_not_reused_for_reference_narration(self):
        import hashlib
        import json
        request = SpeechRequest("Hello there")
        payload = json.dumps(request.payload(), sort_keys=True, ensure_ascii=False)
        old_key = hashlib.sha256(("qwen-uncle-fu-seed321-single-v2:" + payload).encode()).hexdigest()[:24]
        self.assertNotEqual(request.cache_key(), old_key)

    def test_given_full_script_then_complete_wav_and_matching_requests_reused(self):
        with TemporaryDirectory() as directory:
            adapter = FakeSpeech()
            service = NarrationService(Path(directory), adapter)
            request = SpeechRequest("One quiet morning. " * 100)
            output = service.generate(request)
            self.assertEqual(output.parent.name, "generated")
            self.assertEqual(" ".join(adapter.calls[0][1]).split(), request.text.split())
            with wave.open(str(output)) as audio:
                self.assertEqual(audio.getnframes(), 240 * len(adapter.calls[0][1]))
            self.assertEqual(service.generate(request), output)
            self.assertEqual(len(adapter.calls), 1)

    def test_given_preview_then_it_cannot_replace_complete_narration(self):
        with TemporaryDirectory() as directory:
            adapter = FakeSpeech()
            service = NarrationService(Path(directory), adapter)
            request = SpeechRequest("A new beginning. " * 200)
            preview = service.generate(request, preview=True)
            full = service.generate(request)
            self.assertEqual(preview.parent.name, "previews")
            self.assertNotEqual(preview, full)
            self.assertEqual(len(adapter.calls), 2)
            self.assertGreater(len(adapter.calls[1][0].text), len(adapter.calls[0][0].text))

    def test_given_failed_or_cancelled_generation_then_no_partial_result_is_selected(self):
        for fail in (True, False):
            with self.subTest(fail=fail), TemporaryDirectory() as directory:
                service = NarrationService(Path(directory), FakeSpeech(fail=fail))
                with self.assertRaises((RuntimeError, InterruptedError)):
                    service.generate(SpeechRequest("Hello"), cancelled=lambda: not fail)
                self.assertEqual(list(Path(directory).rglob("*.wav")), [])

    def test_given_corrupt_cache_then_narration_is_regenerated(self):
        with TemporaryDirectory() as directory:
            adapter = FakeSpeech()
            service = NarrationService(Path(directory), adapter)
            request = SpeechRequest("Hello")
            output = service.generate(request)
            output.write_bytes(b"broken")
            service.generate(request)
            self.assertEqual(len(adapter.calls), 2)

    def test_given_complete_model_cache_then_loading_uses_local_weights(self):
        with TemporaryDirectory() as directory:
            snapshot = Path(directory)
            for name in REQUIRED_MODEL_FILES:
                target = snapshot / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.touch()
            self.assertEqual(model_location("official/model", lambda *args, **kwargs: directory), directory)

    def test_given_missing_or_incomplete_model_cache_then_first_download_remains_available(self):
        def missing(*args, **kwargs):
            raise FileNotFoundError("No cached snapshot")

        self.assertEqual(model_location("official/model", missing), "official/model")
        with TemporaryDirectory() as directory:
            self.assertEqual(model_location("official/model", lambda *args, **kwargs: directory), "official/model")


if __name__ == "__main__":
    unittest.main()
