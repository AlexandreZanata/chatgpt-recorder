"""Reference-locked narrator contract from docs/LOCAL-NARRATION.md."""

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from src.engine.voice_reference import create_reference_prompt, validate_reference


class TestVoiceReference(unittest.TestCase):
    def test_given_missing_reference_then_generation_stops_before_prompt_extraction(self):
        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(FileNotFoundError, "reference"):
                validate_reference(Path(directory) / "missing.wav")

    def test_given_changed_reference_then_it_is_not_used_as_a_new_speaker(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "changed.wav"
            path.write_bytes(b"not the approved Uncle_Fu recording")
            with self.assertRaisesRegex(ValueError, "reference"):
                validate_reference(path)

    def test_given_approved_reference_then_one_full_prompt_is_prepared(self):
        item = SimpleNamespace(icl_mode=True, x_vector_only_mode=False, ref_code=object())
        calls = []
        class Model:
            def create_voice_clone_prompt(self, **options):
                calls.append(options)
                return [item]

        with patch("src.engine.voice_reference.validate_reference", return_value=Path("approved.wav")):
            prompt = create_reference_prompt(Model())
        self.assertIs(prompt[0], item)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["ref_audio"], "approved.wav")
        self.assertFalse(calls[0]["x_vector_only_mode"])
        self.assertEqual(calls[0]["ref_text"],
                         "Beyond the quiet hills, a new morning begins. The sunlight touches "
                         "the trees, and the world feels peaceful. Take a breath, listen closely, "
                         "and let the story unfold.")

    def test_given_embedding_only_or_empty_prompt_then_missing_acoustic_anchor_is_rejected(self):
        for items in ([], [SimpleNamespace(icl_mode=False, x_vector_only_mode=True, ref_code=None)]):
            model = SimpleNamespace(create_voice_clone_prompt=lambda **kwargs: items)
            with self.subTest(items=items), patch("src.engine.voice_reference.validate_reference",
                                                 return_value=Path("approved.wav")):
                with self.assertRaisesRegex(RuntimeError, "reference"):
                    create_reference_prompt(model)


if __name__ == "__main__":
    unittest.main()
