"""Diffusion Benchmark Module measuring cold/warm latency and VRAM on RTX 4060."""

from pathlib import Path
import time
from typing import Any, Dict, List
import psutil
import torch


def get_vram_peak_mb() -> float:
    """Return peak allocated CUDA memory in megabytes."""
    if torch.cuda.is_available():
        return torch.cuda.max_memory_allocated() / (1024 * 1024)
    return 0.0


def benchmark_sdxl_resolution(
    pipeline: Any,
    width: int,
    height: int,
    embeds: tuple,
    steps: int = 4,
    warm_iterations: int = 2
) -> Dict[str, Any]:
    """Benchmark warm inference across a specific resolution with pre-cached embeddings."""
    p_embeds, neg_embeds, pooled_embeds, neg_pooled_embeds = embeds
    torch.cuda.reset_peak_memory_stats()

    # Warmup / cold pass
    t0 = time.perf_counter()
    _ = pipeline(
        prompt_embeds=p_embeds,
        negative_prompt_embeds=neg_embeds,
        pooled_prompt_embeds=pooled_embeds,
        negative_pooled_prompt_embeds=neg_pooled_embeds,
        num_inference_steps=steps,
        width=width,
        height=height,
        guidance_scale=1.5
    ).images[0]
    cold_sec = time.perf_counter() - t0

    warm_times = []
    for _ in range(warm_iterations):
        t_start = time.perf_counter()
        _ = pipeline(
            prompt_embeds=p_embeds,
            negative_prompt_embeds=neg_embeds,
            pooled_prompt_embeds=pooled_embeds,
            negative_pooled_prompt_embeds=neg_pooled_embeds,
            num_inference_steps=steps,
            width=width,
            height=height,
            guidance_scale=1.5
        ).images[0]
        warm_times.append(time.perf_counter() - t_start)

    avg_warm = sum(warm_times) / len(warm_times) if warm_times else 0.0
    vram_peak = get_vram_peak_mb()
    throughput = 60.0 / avg_warm if avg_warm > 0 else 0.0

    return {
        "resolution": f"{width}x{height}",
        "steps": steps,
        "cold_time_sec": round(cold_sec, 2),
        "warm_time_sec": round(avg_warm, 2),
        "throughput_imgs_min": round(throughput, 1),
        "vram_peak_mb": round(vram_peak, 1)
    }


def run_diffusion_benchmarks(
    model_path: str,
    resolutions: List[tuple] = None
) -> List[Dict[str, Any]]:
    """Load SDXL checkpoint once and benchmark across candidate resolutions."""
    from diffusers import StableDiffusionXLPipeline, EulerDiscreteScheduler

    if resolutions is None:
        resolutions = [(768, 432), (896, 504), (1024, 576)]

    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    t_load_start = time.perf_counter()

    pipe = StableDiffusionXLPipeline.from_single_file(
        model_path,
        torch_dtype=torch.float16,
        use_safetensors=True
    ).to("cuda")
    pipe.scheduler = EulerDiscreteScheduler.from_config(pipe.scheduler.config)
    pipe.vae.config.force_upcast = False
    pipe.vae.to(dtype=torch.float16)
    pipe.vae.enable_slicing()
    pipe.vae.enable_tiling()
    load_time = time.perf_counter() - t_load_start

    # Pre-encode prompt embeddings once (Visual Bible simulation)
    prompt = "Cinematic aerial view of modern metropolis at twilight, 8k documentary style"
    negative = "blurry, deformed, cartoon, low quality"
    embeds = pipe.encode_prompt(prompt=prompt, negative_prompt=negative, device="cuda")

    # Offload text encoders to CPU to free ~1.3 GB VRAM during generation
    pipe.text_encoder.to("cpu")
    pipe.text_encoder_2.to("cpu")
    torch.cuda.empty_cache()

    results = []
    for w, h in resolutions:
        res = benchmark_sdxl_resolution(pipe, w, h, embeds, steps=4)
        res["model_name"] = Path(model_path).name
        res["pipeline_load_sec"] = round(load_time, 2)
        results.append(res)

    del pipe
    torch.cuda.empty_cache()
    return results
