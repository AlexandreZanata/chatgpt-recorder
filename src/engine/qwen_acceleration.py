"""Optional same-weight CUDA graphs; never substitutes a different voice or model."""

from importlib.metadata import version


def warm_graphs(accelerated):
    accelerated._warmup(prefill_len=100)
    graph = accelerated.talker_graph
    if graph.attn_mask_table is not None:
        # Pinned 0.2.6 capture already builds the same causal masks as an all-ones input.
        # A nonzero padding count still changes the key and rebuilds the required masks.
        graph._mask_key = (0,)


def wrap_cuda_graphs(model, dtype):
    if version("faster-qwen3-tts") != "0.2.6":
        raise RuntimeError("Install the tested faster-qwen3-tts==0.2.6 runtime.")
    from faster_qwen3_tts import FasterQwen3TTS
    from faster_qwen3_tts.predictor_graph import PredictorGraph
    from faster_qwen3_tts.talker_graph import TalkerGraph

    talker = model.model.talker
    config = model.model.config.talker_config
    predictor = talker.code_predictor
    predictor_graph = PredictorGraph(predictor, predictor.model.config, config.hidden_size,
                                     device="cuda:0", dtype=dtype, do_sample=True,
                                     top_k=50, top_p=1.0, temperature=0.9)
    talker_graph = TalkerGraph(talker.model, config, device="cuda:0", dtype=dtype,
                               max_seq_len=3072)
    accelerated = FasterQwen3TTS(model, predictor_graph, talker_graph, device="cuda:0",
                                dtype=dtype, max_seq_len=3072)
    warm_graphs(accelerated)
    return accelerated


def accelerate_model(model, cuda, size, dtype, progress=lambda message: None, wrap=None):
    if not cuda or size != "0.6B":
        return model
    progress("Preparing same-model GPU acceleration once for this narration...")
    try:
        accelerated = (wrap or wrap_cuda_graphs)(model, dtype)
    except (ImportError, RuntimeError, TypeError, ValueError, AttributeError) as error:
        progress(f"GPU acceleration unavailable; using original reference-anchored Uncle_Fu engine: {error}")
        return model
    progress("GPU acceleration ready; fixed Uncle_Fu voice, one passage at a time.")
    return accelerated
