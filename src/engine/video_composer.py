"""FFmpeg Single-Pass Stable NVENC GPU Video Composer module."""

import subprocess
from pathlib import Path


def parse_out_time_sec(line: str) -> float:
    """Parse out_time_ms or out_time from FFmpeg progress output line."""
    if line.startswith("out_time_ms="):
        val = line.split("=")[1].strip()
        return float(val) / 1000000.0 if val.isdigit() else -1.0
    if line.startswith("out_time="):
        parts = line.split("=")[1].strip().split(":")
        if len(parts) == 3:
            try:
                return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
            except ValueError:
                return -1.0
    return -1.0


def build_single_pass_command(
    image_path: Path,
    narr_path: Path,
    bgm_path: Path | None,
    subtitle_path: Path | None,
    output_path: Path,
    narr_vol: float = 1.5,
    bgm_vol: float = 0.15,
    width: int = 1920,
    height: int = 1080,
    fps: int = 15,
    duration: float = 0.0,
) -> list[str]:
    """Construct stable single-pass FFmpeg NVENC command."""
    vf = f"scale=w={width}:h={height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,format=yuv420p"

    cmd = [
        "ffmpeg", "-y", "-thread_queue_size", "1024", "-loop", "1", "-i", str(image_path),
        "-thread_queue_size", "1024", "-i", str(narr_path)
    ]

    if bgm_path and bgm_path.is_file():
        cmd.extend(["-thread_queue_size", "1024", "-stream_loop", "-1", "-i", str(bgm_path)])
        af = f"[1:a]volume={narr_vol}[narr];[2:a]volume={bgm_vol}[bgm];[narr][bgm]amix=inputs=2:duration=first:normalize=0[aout]"
        filter_complex = f"[0:v]{vf}[vout];{af}"
        cmd.extend(["-filter_complex", filter_complex, "-map", "[vout]", "-map", "[aout]"])
    else:
        filter_complex = f"[0:v]{vf}[vout]"
        cmd.extend(["-filter_complex", filter_complex, "-map", "[vout]", "-map", "1:a", "-af", f"volume={narr_vol}"])

    if duration > 0:
        cmd.extend(["-t", f"{duration:.3f}"])

    cmd.extend([
        "-c:v", "h264_nvenc", "-preset", "p3", "-rc", "constqp", "-qp", "28",
        "-g", "150", "-r", str(fps), "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart", str(output_path)
    ])
    return cmd


def render_single_pass_video(
    image_path: Path,
    narr_path: Path,
    bgm_path: Path | None,
    subtitle_path: Path | None,
    output_path: Path,
    narr_vol: float = 1.5,
    bgm_vol: float = 0.15,
    width: int = 1920,
    height: int = 1080,
    fps: int = 15,
    progress_callback=None,
    total_duration: float = 0.0,
) -> bool:
    """Execute stable single-pass GPU video render with error capture."""
    cmd = build_single_pass_command(
        image_path, narr_path, bgm_path, subtitle_path, output_path,
        narr_vol, bgm_vol, width, height, fps, duration=total_duration
    )
    if progress_callback:
        cmd.extend(["-progress", "pipe:1", "-nostats"])
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for line in proc.stdout:
            sec = parse_out_time_sec(line.strip())
            if sec >= 0 and total_duration > 0:
                progress_callback(min(99.0, (sec / total_duration) * 100.0), sec)
        _, errs = proc.communicate()
        if proc.returncode != 0 and errs:
            print(f"[FFmpeg error]: {errs[-500:]}")
        return proc.returncode == 0

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0
