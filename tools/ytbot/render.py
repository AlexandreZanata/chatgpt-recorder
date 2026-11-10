"""Render the final 16:9 video with the channel's standard settings."""

from __future__ import annotations

import threading
import time
from pathlib import Path

from . import config
from .audio_tools import fit_narration


RENDER_LOCK = threading.Lock()


def log(message: str) -> None:
    print(f"[render] {message}", flush=True)


def render_video(run_dir: Path) -> Path:
    with RENDER_LOCK:
        return _render_video(run_dir)


def _render_video(run_dir: Path) -> Path:
    from src.core.ai_transcriber import transcribe_audio_to_segments
    from src.engine.audio_mixer import get_audio_duration
    from src.engine.classic_parallel import parallel_workers, render_parallel_video
    from src.engine.standard_backgrounds import resolve_standard_background
    from src.engine.subtitle_generator import save_ass_subtitles
    from src.engine.video_composer import render_single_pass_video

    narration = fit_narration(run_dir)
    output = run_dir / "video.mp4"
    background, is_video = resolve_standard_background(
        config.ROOT / "assets/backgrounds/fallem_prince.jpg", config.THUMBNAIL_THEME)
    duration = get_audio_duration(narration) + config.QUICK_OUTRO_SECONDS
    log(f"narration {get_audio_duration(narration):.1f}s, output {duration:.1f}s")
    segments = transcribe_audio_to_segments(str(narration))
    log(f"transcribed {len(segments)} segments")
    subtitle = save_ass_subtitles(
        segments, run_dir / "narration.ass",
        font_size=round(min(config.VIDEO_WIDTH, config.VIDEO_HEIGHT) * 0.09),
        width=config.VIDEO_WIDTH, height=config.VIDEO_HEIGHT, alignment=5,
        outline_width=4, margin_horizontal=round(config.VIDEO_WIDTH * 0.10),
    )
    start = time.time()
    last = [0.0]

    def progress(pct, seconds):
        if pct - last[0] >= 5:
            last[0] = pct
            log(f"{pct:.1f}% ({seconds:.1f}s / {duration:.1f}s) elapsed {time.time()-start:.0f}s")

    parallel = parallel_workers(duration, is_video) > 1
    renderer = render_parallel_video if parallel else render_single_pass_video
    ok = renderer(
        background, narration, None, subtitle, output,
        narr_vol=config.NARRATION_VOLUME, bgm_vol=0.0,
        width=config.VIDEO_WIDTH, height=config.VIDEO_HEIGHT, fps=config.VIDEO_FPS,
        progress_callback=progress, total_duration=duration, background_is_video=is_video,
    )
    if not ok:
        raise RuntimeError("video rendering failed")
    log(f"video saved: {output} ({output.stat().st_size} bytes)")
    return output
