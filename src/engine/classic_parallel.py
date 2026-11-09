"""Bounded frame-exact Classic encoding, followed by lossless video assembly."""

from concurrent.futures import ThreadPoolExecutor, as_completed
import math
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from src.engine.audio_mixer import get_audio_duration
from src.engine.classic_filters import background_filter, video_encoding_args
from src.engine.video_composer import render_single_pass_video


def parallel_workers(duration, animated, cpus=None):
    available = (os.cpu_count() or 1) if cpus is None else cpus
    return 4 if duration >= 120 and available >= 8 else 1


def frame_ranges(duration, fps, count):
    frames = math.ceil(duration * fps)
    return [(frames * index // count, frames * (index + 1) // count) for index in range(count)]


def build_part_command(background, subtitle, output, start, end, width, height, fps,
                       animated, loop_seconds=0):
    offset = start / fps
    prefix = ""
    if animated:
        if loop_seconds <= 0:
            raise ValueError("Cannot determine background loop duration.")
        inputs = ["-stream_loop", "-1", "-i", str(background)]
        phase_frames = start % max(1, round(loop_seconds * fps))
        prefix = f"trim=start_frame={phase_frames},setpts=PTS-STARTPTS,"
    else:
        inputs = ["-loop", "1", "-framerate", "1", "-i", str(background)]
    filters = prefix + background_filter(subtitle, width, height, fps, animated, offset)
    return ["ffmpeg", "-nostdin", "-hide_banner", "-v", "error", "-y",
            "-filter_complex_threads", "1", *inputs, "-filter_complex", f"[0:v]{filters}[vout]",
            "-map", "[vout]", "-frames:v", str(end-start), "-an", *video_encoding_args(fps), str(output)]


def build_mux_command(concat, narration, music, output, duration, n_volume, m_volume):
    command = ["ffmpeg", "-nostdin", "-hide_banner", "-v", "error", "-y", "-f", "concat",
               "-safe", "0", "-i", str(concat), "-i", str(narration)]
    if music and Path(music).is_file():
        command += ["-stream_loop", "-1", "-i", str(music)]
        filters = (f"[1:a]volume={n_volume}[narr];[2:a]volume={m_volume}[bgm];"
                   "[narr][bgm]amix=inputs=2:duration=longest:normalize=0[aout]")
        command += ["-filter_complex", filters, "-map", "0:v", "-map", "[aout]"]
    else:
        command += ["-map", "0:v", "-map", "1:a", "-af", f"volume={n_volume}"]
    return command + ["-t", f"{duration:.3f}", "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
                      "-movflags", "+faststart", str(output)]


def run_command(command):
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr[-1000:] or "Parallel video encoding failed.")


def encode_parts(folder, background, subtitle, duration, width, height, fps, animated, progress):
    ranges = frame_ranges(duration, fps, 4)
    loop_seconds = get_audio_duration(background) if animated else 0
    clips = [folder / f"part-{index}.mp4" for index in range(4)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        pending = {}
        for index, (start, end) in enumerate(ranges):
            command = build_part_command(background, subtitle, clips[index], start, end,
                                         width, height, fps, animated, loop_seconds)
            pending[pool.submit(run_command, command)] = end-start
        completed = 0
        for future in as_completed(pending):
            future.result()
            completed += pending[future]
            if progress:
                progress(min(95, completed / fps / duration * 95), completed / fps)
    concat = folder / "concat.txt"
    concat.write_text("".join(f"file '{clip.as_posix()}'\n" for clip in clips), encoding="utf-8")
    return concat


def render_parallel_video(image_path, narr_path, bgm_path, subtitle_path, output_path,
                          narr_vol=2.0, bgm_vol=0.15, width=1920, height=1080, fps=15,
                          progress_callback=None, total_duration=0.0, background_is_video=False):
    try:
        with TemporaryDirectory(prefix="classic-parallel-") as temporary:
            concat = encode_parts(Path(temporary), image_path, subtitle_path, total_duration,
                                  width, height, fps, background_is_video, progress_callback)
            run_command(build_mux_command(concat, narr_path, bgm_path, output_path,
                                           total_duration, narr_vol, bgm_vol))
        return True
    except (OSError, RuntimeError, ValueError) as error:
        print(f"[Classic parallel] {error}; retrying the same-quality single-pass renderer.")
        return render_single_pass_video(
            image_path, narr_path, bgm_path, subtitle_path, output_path,
            narr_vol=narr_vol, bgm_vol=bgm_vol, width=width, height=height, fps=fps,
            progress_callback=progress_callback,
            total_duration=total_duration, background_is_video=background_is_video,
        )
