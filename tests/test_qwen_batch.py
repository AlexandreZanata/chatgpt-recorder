"""Native ordered speech batching contracts from docs/LOCAL-NARRATION.md."""

import unittest

from src.core.narration import SpeechRequest
from src.engine.qwen_batch import batch_size, synthesize_passages

REFERENCE_PROMPT = object()


class FakeModel:
    def __init__(self, oom=False, incomplete=False):
        self.calls = []
        self.oom, self.incomplete = oom, incomplete

    def generate_voice_clone(self, **options):
        self.calls.append(options)
        text = options["text"]
        if isinstance(text, list) and self.oom:
            raise MemoryError("Batch exceeds GPU memory")
        passages = text if isinstance(text, list) else [text]
        return ([] if self.incomplete else passages), 24000


class TestQwenBatch(unittest.TestCase):
    def test_given_supported_gpu_then_default_narration_stays_single_passage_for_consistency(self):
        self.assertEqual(batch_size("0.6B", True, 4 * 1024**3, 5), 1)
        self.assertEqual(batch_size("1.7B", True, 4 * 1024**3, 5), 1)
        self.assertEqual(batch_size("0.6B", False, 4 * 1024**3, 5), 1)
        self.assertEqual(batch_size("0.6B", True, 2 * 1024**3, 5), 1)
        self.assertEqual(batch_size("0.6B", True, 4 * 1024**3, 1), 1)

    def test_given_passages_then_sampling_seed_is_reset_before_each_model_call(self):
        events = []
        class RecordingModel(FakeModel):
            def generate_voice_clone(self, **options):
                events.append(options["text"])
                return super().generate_voice_clone(**options)

        list(synthesize_passages(RecordingModel(), SpeechRequest("A. B."), ["A.", "B."],
                                 reset_seed=lambda: events.append("seed321"), voice_prompt=REFERENCE_PROMPT))
        self.assertEqual(events, ["seed321", "A.", "seed321", "B."])

    def test_given_three_passages_then_every_passage_keeps_order_and_original_settings(self):
        model = FakeModel()
        request = SpeechRequest("First. Second. Third.")
        output = list(synthesize_passages(model, request, ["First.", "Second.", "Third."], 2,
                                          voice_prompt=REFERENCE_PROMPT))
        self.assertEqual(output, [(0, "First.", 24000), (1, "Second.", 24000), (2, "Third.", 24000)])
        self.assertEqual([call["text"] for call in model.calls], [["First.", "Second."], "Third."])
        for call in model.calls:
            self.assertIs(call["voice_clone_prompt"], REFERENCE_PROMPT)
            self.assertEqual(call["language"], "English")
            self.assertEqual(call["max_new_tokens"], 2048)
            self.assertNotIn("instruct", call)
            self.assertNotIn("speaker", call)

    def test_given_no_fixed_voice_prompt_then_unanchored_generation_is_rejected(self):
        model = FakeModel()
        with self.assertRaisesRegex(ValueError, "reference"):
            list(synthesize_passages(model, SpeechRequest("Hello."), ["Hello."]))
        self.assertEqual(model.calls, [])

    def test_given_batch_out_of_memory_then_same_text_retries_sequentially_without_loss(self):
        model, released = FakeModel(oom=True), []
        output = list(synthesize_passages(model, SpeechRequest("A. B. C."), ["A.", "B.", "C."],
                                          2, on_oom=lambda: released.append(True), voice_prompt=REFERENCE_PROMPT))
        self.assertEqual(output, [(0, "A.", 24000), (1, "B.", 24000), (2, "C.", 24000)])
        self.assertEqual([call["text"] for call in model.calls], [["A.", "B."], "A.", "B.", "C."])
        self.assertEqual(released, [True])

    def test_given_single_passage_out_of_memory_then_error_is_not_hidden(self):
        class BrokenModel:
            def generate_voice_clone(self, **options):
                raise MemoryError("Not enough memory for even one passage")

        with self.assertRaises(MemoryError):
            list(synthesize_passages(BrokenModel(), SpeechRequest("A."), ["A."], 1,
                                     voice_prompt=REFERENCE_PROMPT))

    def test_given_incomplete_model_response_then_no_partial_batch_is_accepted(self):
        with self.assertRaisesRegex(RuntimeError, "passage"):
            list(synthesize_passages(FakeModel(incomplete=True), SpeechRequest("A. B."),
                                      ["A.", "B."], 2, voice_prompt=REFERENCE_PROMPT))


if __name__ == "__main__":
    unittest.main()
