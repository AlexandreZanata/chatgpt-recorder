"""FFmpeg NVENC GPU Video Composer module."""

import subprocess
from pathlib import Path


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
) -> bool:
    """Execute FFmpeg GPU video render."""
    cmd = build_ffmpeg_composer_command(
        image_path, audio_path, subtitle_path, output_video_path, width, height, fps
    )
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0
