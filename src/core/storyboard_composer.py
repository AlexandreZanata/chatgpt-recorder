from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import shutil
import subprocess
from typing import Any, Callable, Dict, List, Optional

from src.core.motion_renderer import build_cinematic_transition_filter, build_ken_burns_filter


def render_scene_clip(
    image_path: str,
    duration_sec: float,
    output_clip_path: str,
    motion_type: str = "zoom_in_center",
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
    subtitles_srt_path: Optional[str] = None
) -> str:
    """Render a single image into an authentic animated Ken Burns clip using NVENC."""
    vf = build_ken_burns_filter(motion_type, duration_sec, fps, width, height)
    transition = build_cinematic_transition_filter(duration_sec)
    if transition:
        vf = f"{vf},{transition}"
    if subtitles_srt_path and Path(subtitles_srt_path).exists():
        escaped_srt = str(Path(subtitles_srt_path).resolve()).replace(":", "\\:").replace("'", "\\'")
        vf = f"{vf},subtitles='{escaped_srt}'"
    total_frames = int(max(1.0, duration_sec) * fps)
    cmd = [
        "ffmpeg", "-y", "-hide_banner",
        "-framerate", str(fps),
        "-i", image_path,
        "-vf", vf,
        "-frames:v", str(total_frames),
        "-c:v", "h264_nvenc",
        "-preset", "p2",
        "-pix_fmt", "yuv420p",
        output_clip_path
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        cmd[cmd.index("h264_nvenc")] = "libx264"
        cmd[cmd.index("p2")] = "veryfast"
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_clip_path


def assemble_clips_to_video(
    clip_paths: List[Path],
    audio_path: str,
    output_video_path: str,
    bgm_path: Optional[str] = None,
    narr_vol: float = 2.0,
    bgm_vol: float = 0.15,
    subtitles_srt_path: Optional[str] = None,
    subtitles_preburned: bool = False
) -> str:
    """Assemble rendered video clips with audio and subtitles using NVENC / stream-copy."""
    out_dir = Path(output_video_path).parent / f"tmp_asm_{Path(output_video_path).stem}"
    out_dir.mkdir(parents=True, exist_ok=True)

    concat_txt = out_dir / "concat_list.txt"
    with open(concat_txt, "w", encoding="utf-8") as f:
        for p in clip_paths:
            f.write(f"file '{p.resolve()}'\n")

    cmd = ["ffmpeg", "-y", "-hide_banner", "-f", "concat", "-safe", "0", "-i", str(concat_txt), "-i", str(audio_path)]
    filter_complex = []
    if bgm_path and Path(bgm_path).exists():
        cmd += ["-stream_loop", "-1", "-i", str(bgm_path)]
        filter_complex.append(f"[1:a]volume={narr_vol:.2f}[a1];[2:a]volume={bgm_vol:.2f}[a2];[a1][a2]amix=inputs=2:duration=first[aout]")
        audio_map = ["-map", "0:v", "-map", "[aout]"]
    else:
        filter_complex.append(f"[1:a]volume={narr_vol:.2f}[aout]")
        audio_map = ["-map", "0:v", "-map", "[aout]"]

    vf_filters = []
    if not subtitles_preburned and subtitles_srt_path and Path(subtitles_srt_path).exists():
        escaped_srt = str(Path(subtitles_srt_path).resolve()).replace(":", "\\:").replace("'", "\\'")
        vf_filters.append(f"subtitles='{escaped_srt}'")

    if filter_complex:
        cmd += ["-filter_complex", ";".join(filter_complex)]
    if vf_filters:
        cmd += ["-vf", ",".join(vf_filters)]

    vcodec = ["-c:v", "copy"] if not vf_filters else ["-c:v", "h264_nvenc", "-preset", "p2", "-pix_fmt", "yuv420p"]
    cmd += audio_map + vcodec + ["-c:a", "aac", "-b:a", "192k", "-shortest", str(output_video_path)]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)

    return output_video_path


def render_single_pass_storyboard(
    scenes: List[Dict[str, Any]],
    audio_path: str,
    output_video_path: str,
    bgm_path: Optional[str] = None,
    narr_vol: float = 2.0,
    bgm_vol: float = 0.15,
    subtitles_srt_path: Optional[str] = None,
    subtitles_preburned: bool = False,
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> str:
    """Render authentic Ken Burns motions in parallel and assemble final video with NVENC."""
    out_dir = Path(output_video_path).parent / f"clips_{Path(output_video_path).stem}"
    out_dir.mkdir(parents=True, exist_ok=True)
    total = len(scenes)
    clip_paths: List[Optional[Path]] = [None] * total

    def _render_task(item):
        idx, sc = item
        p = out_dir / f"clip_{idx+1}.mp4"
        dur = max(1.0, float(sc.get("duration_sec", 5.0)))
        m_type = sc.get("motion_type", "zoom_in_center")
        render_scene_clip(sc["image_path"], dur, str(p), motion_type=m_type, width=width, height=height, fps=fps)
        return idx, p

    with ThreadPoolExecutor(max_workers=3) as pool:
        for idx, p in pool.map(_render_task, enumerate(scenes)):
            clip_paths[idx] = p
            if progress_callback:
                done = sum(1 for c in clip_paths if c is not None)
                pct = int(80 + (done / max(1, total)) * 12)
                progress_callback(pct, f"Animando cena {done}/{total} (NVENC Paralelo)...")

    if progress_callback:
        progress_callback(94, "Montando áudio, legendas e vídeo final...")

    try:
        assemble_clips_to_video(
            clip_paths=[c for c in clip_paths if c is not None],
            audio_path=audio_path,
            output_video_path=output_video_path,
            bgm_path=bgm_path,
            narr_vol=narr_vol,
            bgm_vol=bgm_vol,
            subtitles_srt_path=subtitles_srt_path,
            subtitles_preburned=subtitles_preburned
        )
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)

    return output_video_path
