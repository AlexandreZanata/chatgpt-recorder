"""Same-model acceleration/fallback contracts from docs/LOCAL-NARRATION.md."""

import unittest
from types import SimpleNamespace

from src.engine.qwen_acceleration import accelerate_model, warm_graphs


class TestQwenAcceleration(unittest.TestCase):
    def test_given_captured_unpadded_masks_then_warmup_marks_the_equivalent_cache(self):
        graph = SimpleNamespace(attn_mask_table=None, _mask_key=None)
        calls = []
        def capture(prefill_len):
            calls.append(prefill_len)
            graph.attn_mask_table = [object()]

        model = SimpleNamespace(_warmup=capture, talker_graph=graph)
        warm_graphs(model)
        self.assertEqual(calls, [100])
        self.assertEqual(graph._mask_key, (0,))

    def test_given_no_mask_table_then_unbuilt_cache_is_not_marked_complete(self):
        graph = SimpleNamespace(attn_mask_table=None, _mask_key=None)
        model = SimpleNamespace(_warmup=lambda prefill_len: None, talker_graph=graph)
        warm_graphs(model)
        self.assertIsNone(graph._mask_key)

    def test_given_cuda_default_model_then_acceleration_wraps_existing_weights_once(self):
        original, accelerated = object(), object()
        calls = []
        def wrap(model, dtype):
            calls.append((model, dtype))
            return accelerated

        actual = accelerate_model(original, True, "0.6B", "bfloat16", wrap=wrap)
        self.assertIs(actual, accelerated)
        self.assertEqual(calls, [(original, "bfloat16")])

    def test_given_unavailable_graphs_then_original_model_is_used_without_voice_substitution(self):
        original, messages = object(), []
        def broken(model, dtype):
            raise RuntimeError("GPU capture unavailable")

        actual = accelerate_model(original, True, "0.6B", "bfloat16", progress=messages.append,
                                  wrap=broken)
        self.assertIs(actual, original)
        self.assertTrue(any("original" in message for message in messages))

    def test_given_cpu_or_larger_model_then_unsupported_acceleration_is_not_attempted(self):
        original = object()
        def forbidden(model, dtype):
            self.fail("Unsupported graph capture was attempted")

        self.assertIs(accelerate_model(original, False, "0.6B", "float32", wrap=forbidden), original)
        self.assertIs(accelerate_model(original, True, "1.7B", "bfloat16", wrap=forbidden), original)


if __name__ == "__main__":
    unittest.main()
