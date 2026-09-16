"""FFmpeg Benchmark Module comparing multi-clip concatenation vs single-pass rendering."""

from pathlib import Path
import subprocess
import time
from typing import Any, Dict, List


def create_dummy_images(temp_dir: Path, count: int = 5, w: int = 1920, h: int = 1080) -> List[Path]:
    """Generate dummy test images for benchmarking."""
    img_paths = []
    colors = ["0x0f172a", "0x1e293b", "0x334155", "0x475569", "0x64748b"]
    for i in range(count):
        out = temp_dir / f"bench_img_{i}.png"
        color = colors[i % len(colors)]
        cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c={color}:s={w}x{h}:d=1", "-frames:v", "1", str(out)]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        img_paths.append(out)
    return img_paths


def benchmark_multi_clip_method(
    img_paths: List[Path],
    audio_path: Path,
    out_video: Path,
    scene_dur: float = 6.0
) -> Dict[str, Any]:
    """Benchmark the legacy multi-clip rendering approach."""
    temp_dir = out_video.parent / "tmp_multi"
    temp_dir.mkdir(exist_ok=True)
    t0 = time.perf_counter()

    clips = []
    for i, img in enumerate(img_paths):
        clip_out = temp_dir / f"clip_{i}.mp4"
        frames = int(scene_dur * 30)
        vf = f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,zoompan=z='min(zoom+0.001,1.15)':d={frames}:s=1920x1080:fps=30"
        cmd = ["ffmpeg", "-y", "-framerate", "30", "-i", str(img), "-vf", vf, "-c:v", "h264_nvenc", "-preset", "p4", "-pix_fmt", "yuv420p", str(clip_out)]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        clips.append(clip_out)

    concat_txt = temp_dir / "list.txt"
    with open(concat_txt, "w") as f:
        for c in clips:
            f.write(f"file '{c.resolve()}'\n")

    cmd_final = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt), "-i", str(audio_path), "-c:v", "copy", "-c:a", "aac", "-shortest", str(out_video)]
    subprocess.run(cmd_final, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    total_sec = time.perf_counter() - t0

    # Cleanup temp clips
    for c in clips:
        c.unlink(missing_ok=True)
    concat_txt.unlink(missing_ok=True)

    return {
        "method": "legacy_multi_clip",
        "total_time_sec": round(total_sec, 2),
        "processes_spawned": len(img_paths) + 1,
        "temp_files_created": len(img_paths) + 1,
        "video_duration_sec": round(len(img_paths) * scene_dur, 2)
    }


def benchmark_single_pass_method(
    img_paths: List[Path],
    audio_path: Path,
    out_video: Path,
    scene_dur: float = 6.0
) -> Dict[str, Any]:
    """Benchmark unified single-pass FFmpeg rendering with concat demuxer & NVENC."""
    temp_dir = out_video.parent / "tmp_single"
    temp_dir.mkdir(exist_ok=True)
    t0 = time.perf_counter()

    concat_txt = temp_dir / "input_images.txt"
    with open(concat_txt, "w") as f:
        for p in img_paths:
            f.write(f"file '{p.resolve()}'\n")
            f.write(f"duration {scene_dur}\n")
        f.write(f"file '{img_paths[-1].resolve()}'\n")

    vf = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,zoompan=z='min(zoom+0.0005,1.15)':d=1:s=1920x1080:fps=30"
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt),
        "-i", str(audio_path),
        "-vf", vf,
        "-c:v", "h264_nvenc", "-preset", "p4", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", str(out_video)
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    total_sec = time.perf_counter() - t0
    concat_txt.unlink(missing_ok=True)

    return {
        "method": "single_pass_nvenc",
        "total_time_sec": round(total_sec, 2),
        "processes_spawned": 1,
        "temp_files_created": 1,
        "video_duration_sec": round(len(img_paths) * scene_dur, 2)
    }
