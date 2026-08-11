"""FFmpeg NVENC GPU Video Composer module."""

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


def build_ffmpeg_composer_command(
    image_path: Path,
    audio_path: Path,
    subtitle_path: Path | None,
    output_video_path: Path,
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
) -> list[str]:
    """Construct FFmpeg NVENC command for composing video from static image + audio + subtitles."""
    video_filter = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
    if subtitle_path and subtitle_path.is_file():
        escaped_sub = str(subtitle_path.resolve()).replace(":", "\\:")
        video_filter += f",subtitles='{escaped_sub}'"

    cmd = [
        "ffmpeg",
        "-y",
        "-loop", "1",
        "-i", str(image_path),
        "-i", str(audio_path),
        "-vf", video_filter,
        "-c:v", "h264_nvenc",
        "-preset", "p7",
        "-cq", "18",
        "-r", str(fps),
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(output_video_path),
    ]
    return cmd


def render_video(
    image_path: Path,
    audio_path: Path,
    subtitle_path: Path | None,
    output_video_path: Path,
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
    progress_callback=None,
    total_duration: float = 0.0,
) -> bool:
    """Execute FFmpeg GPU video render with real-time progress parsing."""
    cmd = build_ffmpeg_composer_command(
        image_path, audio_path, subtitle_path, output_video_path, width, height, fps
    )
    if progress_callback:
        cmd.extend(["-progress", "pipe:1", "-nostats"])
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for line in proc.stdout:
            sec = parse_out_time_sec(line.strip())
            if sec >= 0 and total_duration > 0:
                pct = min(99.0, (sec / total_duration) * 100.0)
                progress_callback(pct, sec)
        proc.wait()
        return proc.returncode == 0

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0
