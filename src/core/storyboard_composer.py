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
    """Render a single image into an animated Ken Burns video clip with NVENC GPU acceleration."""
    vf = build_ken_burns_filter(motion_type, duration_sec, fps, width, height)
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", image_path,
        "-vf", vf,
        "-c:v", "h264_nvenc",
        "-preset", "p4",
        "-pix_fmt", "yuv420p",
        output_clip_path
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        cmd[cmd.index("h264_nvenc")] = "libx264"
        cmd.pop(cmd.index("-preset") + 1)
        cmd.remove("-preset")
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return output_clip_path


def concatenate_scenes_with_audio(
    scene_clip_paths: List[str],
    audio_path: str,
    output_video_path: str,
    bgm_path: Optional[str] = None,
    narr_vol: float = 1.5,
    bgm_vol: float = 0.15,
    subtitles_srt_path: Optional[str] = None
) -> str:
    """Concatenate animated video clips, bind original audio with BGM, and burn subtitles."""
    concat_list = Path(output_video_path).parent / "concat_list.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for p in scene_clip_paths:
            f.write(f"file '{Path(p).resolve()}'\n")

    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-i", audio_path]

    filter_complex = []
    if bgm_path and Path(bgm_path).exists():
        cmd += ["-stream_loop", "-1", "-i", bgm_path]
        filter_complex.append(f"[1:a]volume={narr_vol:.2f}[a1];[2:a]volume={bgm_vol:.2f}[a2];[a1][a2]amix=inputs=2:duration=first[aout]")
        audio_map = ["-map", "0:v", "-map", "[aout]"]
    else:
        filter_complex.append(f"[1:a]volume={narr_vol:.2f}[aout]")
        audio_map = ["-map", "0:v", "-map", "[aout]"]

    vf_filters = []
    if subtitles_srt_path and Path(subtitles_srt_path).exists():
        srt_escaped = str(Path(subtitles_srt_path).resolve()).replace(":", "\\:")
        vf_filters.append(f"subtitles='{srt_escaped}'")

    if vf_filters:
        cmd += ["-vf", ",".join(vf_filters)]

    if filter_complex:
        cmd += ["-filter_complex", ";".join(filter_complex)]

    cmd += audio_map + ["-c:v", "h264_nvenc", "-preset", "p4", "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p", "-shortest", output_video_path]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        cmd[cmd.index("h264_nvenc")] = "libx264"
        cmd.pop(cmd.index("-preset") + 1)
        cmd.remove("-preset")
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if concat_list.exists():
        concat_list.unlink()
    return output_video_path
