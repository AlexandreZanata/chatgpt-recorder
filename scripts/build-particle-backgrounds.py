#!/usr/bin/env python3
"""Build small seamless H.264 particle loops once, outside the rendering workflow."""

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.engine.particle_art import LOOP_SECONDS, ParticleLoop
from src.engine.particle_profiles import PARTICLE_PROFILES
from src.engine.standard_backgrounds import BACKGROUND_DIR, BACKGROUND_THEMES, PORTRAIT_BACKGROUND_FILES


def build_loop(theme: str, fps: int = 30, portrait: bool = False) -> Path:
    """Stream procedural frames to FFmpeg without storing thousands of images."""
    BACKGROUND_DIR.mkdir(parents=True, exist_ok=True)
    filename = PORTRAIT_BACKGROUND_FILES[theme] if portrait else BACKGROUND_THEMES[theme][1]
    destination = BACKGROUND_DIR / filename
    partial = destination.with_suffix(".partial.mp4")
    animation = ParticleLoop(theme, width=720, height=1280) if portrait else ParticleLoop(theme)
    profile = PARTICLE_PROFILES[theme]
    crf = profile.portrait_crf if portrait else profile.crf
    width, height = animation.base.size
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo",
        "-pix_fmt", "rgb24", "-s", f"{width}x{height}", "-r", str(fps),
        "-i", "pipe:0", "-an", "-c:v", "libx264", "-preset", "fast",
        "-crf", str(crf),
        "-pix_fmt", "yuv420p", "-g", str(fps * 2), "-movflags", "+faststart", str(partial),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for frame in range(LOOP_SECONDS * fps):
            process.stdin.write(animation.frame(frame / fps).tobytes())
        process.stdin.close()
        errors = process.stderr.read().decode()
        if process.wait() != 0:
            raise RuntimeError(errors)
        partial.replace(destination)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        process.stderr.close()
        if partial.exists():
            partial.unlink()
    animation.frame(6).save(destination.with_suffix(".jpg"), quality=92)
    if portrait and theme == "black":
        animation.base.save(BACKGROUND_DIR / "enigmatic_black_shorts_plate.png")
    print(f"Created {destination} ({destination.stat().st_size / 1024:.0f} KiB)", flush=True)
    return destination


if __name__ == "__main__":
    for selected in BACKGROUND_THEMES:
        build_loop(selected)
        build_loop(selected, portrait=True)
