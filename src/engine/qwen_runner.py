"""Qwen runtime entry point executed only inside the optional speech environment."""

import json
import os
from pathlib import Path
import sys

from src.core.narration import MODELS, NARRATION_PROFILE, SpeechRequest, VOICE_SEED
from src.engine.qwen_acceleration import accelerate_model
from src.engine.qwen_batch import batch_size, synthesize_passages
from src.engine.voice_reference import create_reference_prompt, validate_reference

REQUIRED_MODEL_FILES = (
    "config.json", "model.safetensors", "generation_config.json", "preprocessor_config.json",
    "tokenizer_config.json", "merges.txt", "vocab.json", "speech_tokenizer/config.json",
    "speech_tokenizer/model.safetensors", "speech_tokenizer/preprocessor_config.json",
)


def model_location(model_id, snapshot_lookup):
    """Avoid repeated HTTP metadata checks once an entire official model is cached."""
    try:
        snapshot = snapshot_lookup(model_id, local_files_only=True)
    except FileNotFoundError:
        return model_id
    if all((Path(snapshot) / name).is_file() for name in REQUIRED_MODEL_FILES):
        return str(snapshot)
    return model_id


def progress(message):
    print(f"TTS_PROGRESS:{message}", flush=True)


def generate(request, chunks, output):
    reference = validate_reference()
    import numpy as np
    import soundfile as sf
    import torch
    from qwen_tts import Qwen3TTSModel
    from huggingface_hub import snapshot_download

    torch.set_num_threads(min(8, os.cpu_count() or 1))
    cuda = torch.cuda.is_available()
    device, dtype = ("cuda:0", torch.bfloat16) if cuda else ("cpu", torch.float32)
    progress(f"Loading Qwen {request.model} on {'CUDA GPU' if cuda else 'CPU (slower)'}...")
    model = Qwen3TTSModel.from_pretrained(
        model_location(MODELS[request.model], snapshot_download),
        device_map=device, dtype=dtype, attn_implementation="sdpa",
    )
    audio_file, voice_prompt = None, None
    try:
        progress("Preparing the original Uncle_Fu acoustic and delivery reference once...")
        voice_prompt = create_reference_prompt(model, reference)
        model = accelerate_model(model, cuda, request.model, dtype, progress)
        progress("Reference-locked Uncle_Fu: every passage uses English and the same original recording.")
        free_bytes = torch.cuda.mem_get_info()[0] if cuda else 0
        size = batch_size(request.model, cuda, free_bytes, len(chunks))
        passages = synthesize_passages(model, request, chunks, size,
                                        oom_error=torch.cuda.OutOfMemoryError,
                                        on_oom=torch.cuda.empty_cache, progress=progress,
                                        reset_seed=lambda: torch.manual_seed(VOICE_SEED),
                                        voice_prompt=voice_prompt)
        with torch.inference_mode():
            for index, wav, rate in passages:
                samples = np.asarray(wav, dtype=np.float32).reshape(-1)
                if not samples.size or not np.isfinite(samples).all():
                    raise RuntimeError("Speech model produced invalid audio.")
                if audio_file is None:
                    audio_file = sf.SoundFile(str(output), "w", samplerate=rate, channels=1,
                                              format="WAV", subtype="PCM_16")
                if audio_file.samplerate != rate:
                    raise RuntimeError("Speech sample rate changed between passages.")
                if index:
                    audio_file.write(np.zeros(round(rate * 0.18), dtype=np.float32))
                audio_file.write(samples)
    finally:
        if audio_file is not None:
            audio_file.close()
        del model
        del voice_prompt
        if cuda:
            torch.cuda.empty_cache()
    progress("Complete narration saved; speech model released.")


def validate_profile(payload):
    if payload.get("profile") != NARRATION_PROFILE:
        raise ValueError("Restart the desktop app after the current job finishes to use English-only reference-locked Uncle_Fu.")


def main():
    payload = json.load(sys.stdin)
    validate_profile(payload)
    request = SpeechRequest(**payload["request"])
    generate(request, payload["chunks"], Path(payload["output"]))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        sys.exit(1)
