"""FFmpeg Audio Mixer module for combining narration and looping background music."""

import subprocess
from pathlib import Path


def build_audio_mix_command(
    narration_path: Path,
    bgm_path: Path | None,
    output_audio_path: Path,
    narration_volume: float = 1.0,
    bgm_volume: float = 0.18,
) -> list[str]:
    """Construct FFmpeg command to mix narration and looping background music."""
    cmd = ["ffmpeg", "-y", "-i", str(narration_path)]

    if bgm_path and bgm_path.is_file():
        cmd.extend(["-stream_loop", "-1", "-i", str(bgm_path)])
        filter_complex = (
            f"[0:a]volume={narration_volume}[narr];"
            f"[1:a]volume={bgm_volume}[bgm];"
            "[narr][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        )
        cmd.extend(["-filter_complex", filter_complex, "-map", "[aout]"])
    else:
        cmd.extend(["-af", f"volume={narration_volume}"])

    cmd.extend(["-c:a", "pcm_s16le", str(output_audio_path)])
    return cmd


def mix_audio_tracks(
    narration_path: Path,
    bgm_path: Path | None,
    output_audio_path: Path,
    narration_volume: float = 1.0,
    bgm_volume: float = 0.18,
) -> bool:
    """Execute FFmpeg audio mixing."""
    cmd = build_audio_mix_command(
        narration_path, bgm_path, output_audio_path, narration_volume, bgm_volume
    )
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0
