"""Shared Classic video filters and unchanged NVENC quality settings."""

from pathlib import Path


def background_filter(subtitle_path, width, height, fps, animated, offset=0.0):
    fit = "increase" if animated else "decrease"
    filters = f"scale=w={width}:h={height}:force_original_aspect_ratio={fit}"
    filters += (f",crop={width}:{height},setsar=1" if animated
                else f",pad={width}:{height}:(ow-iw)/2:(oh-ih)/2")
    filters += ",format=yuv420p"
    if not animated:
        filters += f",fps={fps}"
    if offset:
        filters += f",setpts=PTS+{offset:.6f}/TB"
    if subtitle_path is not None:
        subtitle = Path(subtitle_path)
        if not subtitle.is_file():
            raise FileNotFoundError(f"Subtitle file not found: {subtitle}")
        escaped = str(subtitle.resolve()).replace("\\", "\\\\").replace(":", "\\:").replace("'", "'\\\\''")
        filters += f",subtitles=filename='{escaped}'"
    if offset:
        filters += ",setpts=PTS-STARTPTS"
    return filters


def video_encoding_args(fps):
    return ["-c:v", "h264_nvenc", "-preset", "p3", "-rc", "constqp", "-qp", "28",
            "-g", "150", "-r", str(fps)]
