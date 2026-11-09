"""Narration duration checks and ACCEPTED (35 min to 80 min) fitting."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

MAX_NARRATION_SECONDS = 80 * 60
TARGET_NARRATION_SECONDS = 79 * 60 + 30
MIN_NARRATION_SECONDS = 35 * 60


def log(message: str) -> None:
    print(f"[audio] {message}", flush=True)


def find_narration(run_dir: Path) -> Path:
    for name in ("narration.aac", "narration.webm", "narration.m4a", "narration.wav"):
        path = run_dir / name
        if path.is_file():
            return path
    raise FileNotFoundError("narration file is missing")


def fit_narration(run_dir: Path) -> Path:
    from src.engine.audio_mixer import get_audio_duration

    narration = find_narration(run_dir)
    duration = get_audio_duration(narration)
    if duration < MIN_NARRATION_SECONDS:
        log(f"warning: narration is shorter than the accepted 35 minutes ({duration:.1f}s)")
    if duration <= MAX_NARRATION_SECONDS:
        return narration
    tempo = duration / TARGET_NARRATION_SECONDS
    log(f"narration {duration:.1f}s exceeds 80 min; speeding up by {tempo:.4f}x")
    temporary = run_dir / "narration.fitted.aac"
    subprocess.run([
        "ffmpeg", "-nostdin", "-hide_banner", "-v", "error", "-y",
        "-i", str(narration), "-filter:a", f"atempo={tempo:.6f}",
        "-c:a", "aac", "-b:a", "192k", str(temporary),
    ], check=True)
    shutil.copy2(narration, run_dir / f"narration.original{narration.suffix}")
    if narration.suffix.lower() != ".aac":
        narration.unlink(missing_ok=True)
    temporary.replace(run_dir / "narration.aac")
    fitted = run_dir / "narration.aac"
    log(f"narration fitted: {get_audio_duration(fitted):.1f}s")
    return fitted
