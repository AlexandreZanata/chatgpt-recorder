"""CLI Runner for automated end-to-end and component benchmarks."""

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.benchmark.benchmark_asr import benchmark_all_asr_configs
from src.benchmark.benchmark_diffusion import run_diffusion_benchmarks
from src.benchmark.benchmark_ffmpeg import (
    benchmark_multi_clip_method,
    benchmark_single_pass_method,
    create_dummy_images
)


def run_asr_suite(audio_file: Path) -> Dict[str, Any]:
    """Run ASR benchmark suite on the provided audio."""
    print(f"\n[BENCHMARK] Running ASR Suite on: {audio_file.name}")
    results = benchmark_all_asr_configs(str(audio_file))
    for r in results:
        print(f"  > {r['model']:<16} ({r['compute_type']:<13}) VAD={str(r['vad']):<5} -> "
              f"Inf: {r['inf_time_sec']}s | RTF: {r['rtf']} | VRAM: {r['vram_peak_mb']} MB")
    return {"asr_results": results}


def run_diffusion_suite(checkpoint_path: Path) -> Dict[str, Any]:
    """Run Diffusion benchmark suite across resolutions."""
    print(f"\n[BENCHMARK] Running Diffusion Suite on: {checkpoint_path.name}")
    results = run_diffusion_benchmarks(str(checkpoint_path))
    for r in results:
        print(f"  > Res: {r['resolution']:<10} Steps: {r['steps']} -> "
              f"Warm: {r['warm_time_sec']}s/img | Throughput: {r['throughput_imgs_min']} imgs/min | VRAM: {r['vram_peak_mb']} MB")
    return {"diffusion_results": results}


def run_ffmpeg_suite(audio_file: Path, out_dir: Path) -> Dict[str, Any]:
    """Run FFmpeg comparison benchmark."""
    print(f"\n[BENCHMARK] Running FFmpeg Engine Benchmark")
    tmp_dir = out_dir / "bench_ffmpeg"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    imgs = create_dummy_images(tmp_dir, count=5)
    legacy = benchmark_multi_clip_method(imgs, audio_file, tmp_dir / "legacy.mp4")
    single = benchmark_single_pass_method(imgs, audio_file, tmp_dir / "single.mp4")

    print(f"  > Legacy Multi-Clip : {legacy['total_time_sec']}s ({legacy['processes_spawned']} procs, {legacy['temp_files_created']} files)")
    print(f"  > Single-Pass NVENC : {single['total_time_sec']}s ({single['processes_spawned']} proc, {single['temp_files_created']} file)")
    speedup = round(legacy['total_time_sec'] / max(0.1, single['total_time_sec']), 2)
    print(f"  ==> Single-Pass Speedup: {speedup}x faster!")

    # Cleanup test outputs
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)

    return {"ffmpeg_legacy": legacy, "ffmpeg_single_pass": single, "speedup_factor": speedup}


def main():
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Auto AI Story Benchmark Suite")
    parser.add_argument("--stage", choices=["all", "asr", "diffusion", "ffmpeg"], default="all")
    parser.add_argument("--audio", default=str(_ROOT / "audio" / "1.aac"))
    parser.add_argument("--model", default=str(Path.home() / "PESSOAL-PROJETOS-ALEXANDRE" / "Fooocus" / "models" / "checkpoints" / "RealVisXL_V5.0_fp16.safetensors"))
    parser.add_argument("--out", default=str(_ROOT / "benchmark_results.json"))
    args = parser.parse_args()

    audio_p = Path(args.audio)
    model_p = Path(args.model)
    out_p = Path(args.out)

    report = {"target_gpu": "NVIDIA GeForce RTX 4060 Laptop (8GB)", "metrics": {}}

    if args.stage in ("all", "asr"):
        report["metrics"].update(run_asr_suite(audio_p))

    if args.stage in ("all", "diffusion"):
        if model_p.exists():
            report["metrics"].update(run_diffusion_suite(model_p))
        else:
            print(f"[WARN] Model checkpoint not found at {model_p}, skipping diffusion stage.")

    if args.stage in ("all", "ffmpeg"):
        report["metrics"].update(run_ffmpeg_suite(audio_p, out_p.parent))

    out_p.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n[BENCHMARK] Full report saved to: {out_p.resolve()}\n")


if __name__ == "__main__":
    main()
