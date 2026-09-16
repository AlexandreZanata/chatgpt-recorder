"""ASR Benchmark Module measuring latency, RTF, and VRAM for Whisper variants."""

from pathlib import Path
import time
from typing import Any, Dict, List
import psutil
import torch


def get_vram_mb() -> float:
    """Return current peak allocated VRAM in megabytes."""
    if torch.cuda.is_available():
        return torch.cuda.max_memory_allocated() / (1024 * 1024)
    return 0.0


def run_single_asr_benchmark(
    audio_path: str,
    model_size: str = "large-v3-turbo",
    compute_type: str = "float16",
    vad_filter: bool = True
) -> Dict[str, Any]:
    """Execute a single ASR test run and collect performance metrics."""
    from faster_whisper import WhisperModel

    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()

    process = psutil.Process()
    ram_start = process.memory_info().rss / (1024 * 1024)

    t_load_start = time.perf_counter()
    model = WhisperModel(model_size, device="cuda", compute_type=compute_type)
    t_load = time.perf_counter() - t_load_start

    t_inf_start = time.perf_counter()
    segments, info = model.transcribe(audio_path, beam_size=1, vad_filter=vad_filter)
    segment_list = list(segments)
    t_inf = time.perf_counter() - t_inf_start

    audio_dur = info.duration if info.duration > 0 else 1.0
    rtf = t_inf / audio_dur
    vram_peak = get_vram_mb()
    ram_peak = (process.memory_info().rss / (1024 * 1024)) - ram_start

    del model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    sample_text = segment_list[0].text.strip() if segment_list else ""
    return {
        "model": model_size,
        "compute_type": compute_type,
        "vad": vad_filter,
        "audio_dur_sec": round(audio_dur, 2),
        "load_time_sec": round(t_load, 2),
        "inf_time_sec": round(t_inf, 2),
        "rtf": round(rtf, 4),
        "vram_peak_mb": round(vram_peak, 1),
        "ram_peak_mb": round(ram_peak, 1),
        "detected_lang": info.language,
        "lang_prob": round(info.language_probability, 2),
        "segments_count": len(segment_list),
        "sample_text": sample_text[:60]
    }


def benchmark_all_asr_configs(audio_path: str) -> List[Dict[str, Any]]:
    """Benchmark target ASR configurations and return aggregated results."""
    configs = [
        ("small", "float16", True),
        ("large-v3-turbo", "float16", True),
        ("large-v3-turbo", "int8_float16", True),
        ("large-v3-turbo", "float16", False)
    ]
    results = []
    for model_size, ctype, vad in configs:
        res = run_single_asr_benchmark(audio_path, model_size, ctype, vad)
        results.append(res)
    return results
