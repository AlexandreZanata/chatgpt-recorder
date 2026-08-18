"""Storyboard Video Composer: combines animated scenes, audio track, and subtitles into a finished MP4."""

from pathlib import Path
import subprocess
from typing import Any, Dict, List, Optional

from src.core.motion_renderer import build_ken_burns_filter


def render_scene_clip(
    image_path: str,
    duration_sec: float,
    output_clip_path: str,
    motion_type: str = "zoom_in",
    width: int = 1920,
    height: int = 1080,
    fps: int = 30
) -> str:
    """Render a single image into an animated Ken Burns video clip with FFmpeg."""
    vf = build_ken_burns_filter(motion_type, duration_sec, fps, width, height)
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-t", str(duration_sec),
        "-i", image_path,
        "-vf", vf,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-r", str(fps),
        output_clip_path
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_clip_path


def concatenate_scenes_with_audio(
    scene_clip_paths: List[str],
    audio_path: str,
    output_video_path: str,
    subtitles_srt_path: Optional[str] = None
) -> str:
    """Concatenate animated video clips, bind original audio, and optionally burn subtitles."""
    concat_list = Path(output_video_path).parent / "concat_list.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for p in scene_clip_paths:
            f.write(f"file '{Path(p).resolve()}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list),
        "-i", audio_path
    ]

    if subtitles_srt_path and Path(subtitles_srt_path).exists():
        srt_escaped = str(Path(subtitles_srt_path).resolve()).replace(":", "\\:")
        cmd += ["-vf", f"subtitles='{srt_escaped}'"]

    cmd += [
        "-c:v", "libx264",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        output_video_path
    ]

    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if concat_list.exists():
        concat_list.unlink()
    return output_video_path
