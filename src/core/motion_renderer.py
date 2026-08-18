"""Motion Renderer: creates cinematic Ken Burns Pan & Zoom dynamic animations with FFmpeg."""

import random
from typing import Dict, List


MOTION_PATTERNS = [
    "zoom_in",
    "zoom_out",
    "pan_left",
    "pan_right",
    "pan_up",
    "pan_down"
]


def build_ken_burns_filter(
    motion_type: str,
    duration_sec: float,
    fps: int = 30,
    width: int = 1920,
    height: int = 1080
) -> str:
    """Build FFmpeg zoompan filter string for smooth Ken Burns motion."""
    total_frames = int(duration_sec * fps)
    max_z = 1.25

    if motion_type == "zoom_in":
        # Smooth zoom from 1.0 to 1.25 centered
        return f"zoompan=z='min(zoom+0.0015,{max_z})':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s={width}x{height}:fps={fps}"
    elif motion_type == "zoom_out":
        # Smooth zoom out from 1.25 to 1.0 centered
        return f"zoompan=z='if(lte(zoom,1.0),1.0,max(1.001,zoom-0.0015))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s={width}x{height}:fps={fps}"
    elif motion_type == "pan_left":
        # Pan across from right to left
        return f"zoompan=z=1.15:x='if(lte(on,1),(iw-iw/zoom),max(0,x-1.2))':y='ih/2-(ih/zoom/2)':d={total_frames}:s={width}x{height}:fps={fps}"
    elif motion_type == "pan_right":
        # Pan across from left to right
        return f"zoompan=z=1.15:x='min(iw-iw/zoom,x+1.2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s={width}x{height}:fps={fps}"
    elif motion_type == "pan_up":
        # Pan from bottom to top
        return f"zoompan=z=1.15:x='iw/2-(iw/zoom/2)':y='if(lte(on,1),(ih-ih/zoom),max(0,y-1.2))':d={total_frames}:s={width}x{height}:fps={fps}"
    else:
        # Default pan down
        return f"zoompan=z=1.15:x='iw/2-(iw/zoom/2)':y='min(ih-ih/zoom,y+1.2)':d={total_frames}:s={width}x{height}:fps={fps}"


def assign_random_motions(scenes: List[Dict]) -> List[Dict]:
    """Assign distinct random Ken Burns motion patterns across a list of scenes."""
    last_motion = None
    for scene in scenes:
        candidates = [m for m in MOTION_PATTERNS if m != last_motion]
        chosen = random.choice(candidates)
        scene["motion_type"] = chosen
        last_motion = chosen
    return scenes
