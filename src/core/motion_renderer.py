"""Motion Renderer: creates cinematic Ken Burns Pan & Zoom dynamic animations with FFmpeg."""

import random
from typing import Dict, List


MOTION_PATTERNS = [
    "zoom_in",
    "zoom_out",
    "pan_left",
    "pan_right"
]


def build_ken_burns_filter(
    motion_type: str,
    duration_sec: float,
    fps: int = 30,
    width: int = 1920,
    height: int = 1080
) -> str:
    """Build fast and clean FFmpeg zoompan filter string for smooth Ken Burns motion."""
    total_frames = int(max(1.0, duration_sec) * fps)
    step = 0.20 / max(1, total_frames)

    if motion_type == "zoom_in":
        return f"scale=2560:-2,zoompan=z='min(zoom+{step:.5f},1.20)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s={width}x{height}:fps={fps}"
    elif motion_type == "zoom_out":
        return f"scale=2560:-2,zoompan=z='if(lte(zoom,1.0),1.0,max(1.001,1.20-{step:.5f}*on))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s={width}x{height}:fps={fps}"
    elif motion_type == "pan_left":
        return f"scale=2560:-2,zoompan=z=1.15:x='if(lte(on,1),(iw-iw/zoom),max(0,x-1.0))':y='ih/2-(ih/zoom/2)':d={total_frames}:s={width}x{height}:fps={fps}"
    else:
        # Pan right
        return f"scale=2560:-2,zoompan=z=1.15:x='min(iw-iw/zoom,x+1.0)':y='ih/2-(ih/zoom/2)':d={total_frames}:s={width}x{height}:fps={fps}"


def assign_random_motions(scenes: List[Dict]) -> List[Dict]:
    """Assign distinct random Ken Burns motion patterns across scenes."""
    last_motion = None
    for scene in scenes:
        candidates = [m for m in MOTION_PATTERNS if m != last_motion]
        chosen = random.choice(candidates)
        scene["motion_type"] = chosen
        last_motion = chosen
    return scenes
