"""Build lightweight cinematic motion and transition filters for AI Story scenes."""

import random
from typing import Dict, List


MOTION_PATTERNS = [
    "pan_right",
    "pan_left",
    "tilt_up",
    "tilt_down",
    "zoom_in",
]
_SUPPORTED_MOTIONS = {*MOTION_PATTERNS, "zoom_out"}
_MOTION_ALIASES = {"zoom_in_center": "zoom_in", "zoom_out_center": "zoom_out"}
_MOTION_OVERSAMPLE = 2.0


def _even(value: float) -> int:
    """Round a video dimension down to an encoder-safe even integer."""
    return max(2, int(value) // 2 * 2)


def _base_filter(width: int, height: int, scale: float = 1.0) -> str:
    """Scale and crop without changing source or sample aspect ratio."""
    scaled_width, scaled_height = _even(width * scale), _even(height * scale)
    return (
        f"scale={scaled_width}:{scaled_height}:flags=lanczos:force_original_aspect_ratio=increase,"
        f"crop={scaled_width}:{scaled_height},setsar=1"
    )


def _pan_filter(
    motion_type: str,
    progress: str,
    width: int,
    height: int,
    total_frames: int,
    fps: int,
) -> str:
    """Build an eased pan on an aspect-ratio-safe overscan canvas."""
    zoom = 1.12
    base = _base_filter(width, height, _MOTION_OVERSAMPLE)
    inverse = f"(1-{progress})"
    phase = progress if motion_type in {"pan_right", "tilt_down"} else inverse
    centered_x = "floor((iw-iw/zoom)/2)"
    centered_y = "floor((ih-ih/zoom)/2)"
    x = f"floor((iw-iw/zoom)*{phase})" if motion_type.startswith("pan_") else centered_x
    y = f"floor((ih-ih/zoom)*{phase})" if motion_type.startswith("tilt_") else centered_y
    return (
        f"{base},zoompan=z='{zoom:.2f}':x='{x}':y='{y}':"
        f"d={total_frames}:s={width}x{height}:fps={fps}"
    )


def _zoom_filter(
    motion_type: str,
    progress: str,
    duration_sec: float,
    width: int,
    height: int,
    total_frames: int,
    fps: int,
) -> str:
    """Build a duration-aware centered push-in or pull-out."""
    span = min(0.16, max(0.10, 0.10 + duration_sec * 0.002))
    start = 1.02
    if motion_type == "zoom_out":
        zoom = f"{start + span:.4f}-{span:.4f}*{progress}"
    else:
        zoom = f"{start:.4f}+{span:.4f}*{progress}"
    return (
        f"{_base_filter(width, height, _MOTION_OVERSAMPLE)},zoompan=z='{zoom}':"
        f"x='floor((iw-iw/zoom)/2)':y='floor((ih-ih/zoom)/2)':"
        f"d={total_frames}:s={width}x{height}:fps={fps}"
    )


def build_ken_burns_filter(
    motion_type: str,
    duration_sec: float,
    fps: int = 30,
    width: int = 1920,
    height: int = 1080,
) -> str:
    """Build a smooth Ken Burns filter with eased, duration-aware movement."""
    total_frames = int(max(1.0, duration_sec) * fps)
    last_frame = max(1, total_frames - 1)
    linear = f"(on/{last_frame})"
    progress = f"({linear}*{linear}*(3-2*{linear}))"
    normalized = _MOTION_ALIASES.get(motion_type, motion_type)
    if normalized == "static":
        return (
            f"{_base_filter(width, height)},zoompan=z='1.0':x='0':y='0':"
            f"d={total_frames}:s={width}x{height}:fps={fps}"
        )
    if normalized in {"pan_right", "pan_left", "tilt_up", "tilt_down"}:
        return _pan_filter(normalized, progress, width, height, total_frames, fps)
    safe_motion = normalized if normalized in _SUPPORTED_MOTIONS else "zoom_in"
    return _zoom_filter(safe_motion, progress, duration_sec, width, height, total_frames, fps)


def build_cinematic_transition_filter(
    duration_sec: float,
    fade_in: bool = True,
    fade_out: bool = True,
) -> str:
    """Build an inline dip transition that preserves fast stream-copy assembly."""
    duration = max(1.0, float(duration_sec))
    transition = min(0.45, max(0.18, duration * 0.04))
    filters = []
    if fade_in:
        filters.append(f"fade=t=in:st=0:d={transition:.3f}")
    if fade_out:
        start = max(0.0, duration - transition)
        filters.append(f"fade=t=out:st={start:.3f}:d={transition:.3f}")
    return ",".join(filters)


def apply_motion_preference(scenes: List[Dict], enabled: bool) -> List[Dict]:
    """Apply the user-visible motion preference to every planned scene."""
    if enabled:
        return scenes
    for scene in scenes:
        scene["motion_type"] = "static"
    return scenes


def assign_random_motions(scenes: List[Dict]) -> List[Dict]:
    """Assign diverse motion patterns without consecutive repetition."""
    last_motion = None
    for scene in scenes:
        candidates = [motion for motion in MOTION_PATTERNS if motion != last_motion]
        chosen = random.choice(candidates)
        scene["motion_type"] = chosen
        last_motion = chosen
    return scenes
