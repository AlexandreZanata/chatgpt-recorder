"""AI Transcriber module using faster-whisper large-v3-turbo with CUDA acceleration."""

import gc
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

_FOOOCUS_NVIDIA = Path.home() / "PESSOAL-PROJETOS-ALEXANDRE" / "Fooocus" / "venv" / "lib" / "python3.12" / "site-packages" / "nvidia"
if _FOOOCUS_NVIDIA.exists():
    _cublas = str(_FOOOCUS_NVIDIA / "cublas" / "lib")
    _cudnn = str(_FOOOCUS_NVIDIA / "cudnn" / "lib")
    _cur_ld = os.environ.get("LD_LIBRARY_PATH", "")
    if _cublas not in _cur_ld:
        os.environ["LD_LIBRARY_PATH"] = f"{_cublas}:{_cudnn}:{_cur_ld}".strip(":")


def check_whisper_available() -> bool:
    """Check if faster-whisper is available in the environment."""
    try:
        import faster_whisper  # noqa: F401
        return True
    except ImportError:
        pass
    try:
        import whisper  # noqa: F401
        return True
    except ImportError:
        return False


def format_timestamp_srt(seconds: float) -> str:
    """Format seconds into standard SRT timestamp HH:MM:SS,mmm."""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"


def transcribe_audio_to_segments(
    audio_path: str,
    model_name: str = "large-v3-turbo",
    language: Optional[str] = None,
    word_timestamps: bool = False
) -> List[Dict[str, Any]]:
    """Transcribe audio file into timestamped segments using faster-whisper on GPU."""
    try:
        from faster_whisper import WhisperModel
        import torch

        compute_type = "int8_float16" if torch.cuda.is_available() else "int8"
        device = "cuda" if torch.cuda.is_available() else "cpu"

        model = WhisperModel(model_name, device=device, compute_type=compute_type)
        segments, info = model.transcribe(
            audio_path,
            language=language,
            beam_size=1,
            vad_filter=True,
            word_timestamps=word_timestamps
        )

        formatted = []
        for s in segments:
            formatted.append({
                "id": s.id,
                "start": round(s.start, 2),
                "end": round(s.end, 2),
                "text": s.text.strip(),
                "avg_logprob": round(s.avg_logprob, 3)
            })

        # Explicit unload to free VRAM immediately for the image diffusion phase
        del model
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        return formatted
    except Exception as err:
        print(f"[WARN] faster-whisper transcription error: {err}")
        return []


def generate_srt_subtitles(
    segments: List[Dict[str, Any]],
    output_srt_path: str
) -> str:
    """Generate standard .srt file from whisper segments."""
    lines = []
    idx = 1
    for seg in segments:
        text = seg.get("text", "").strip()
        if not text:
            continue
        start_str = format_timestamp_srt(seg.get("start", 0.0))
        end_str = format_timestamp_srt(seg.get("end", 0.0))
        lines.append(f"{idx}\n{start_str} --> {end_str}\n{text}\n")
        idx += 1
    content = "\n".join(lines)
    Path(output_srt_path).write_text(content, encoding="utf-8")
    return output_srt_path


def slice_srt_for_window(
    segments: List[Dict[str, Any]],
    start_sec: float,
    end_sec: float,
    output_srt_path: str
) -> Optional[str]:
    """Slice and time-offset subtitles for an isolated scene time window."""
    lines = []
    idx = 1
    for s in segments:
        if s.get("end", 0.0) <= start_sec or s.get("start", 0.0) >= end_sec:
            continue
        c_start = max(0.0, float(s.get("start", 0.0)) - start_sec)
        c_end = min(end_sec - start_sec, float(s.get("end", 0.0)) - start_sec)
        text = str(s.get("text", "")).strip()
        if (c_end - c_start) < 0.1 or not text:
            continue
        lines.append(f"{idx}\n{format_timestamp_srt(c_start)} --> {format_timestamp_srt(c_end)}\n{text}\n")
        idx += 1
    if not lines:
        return None
    Path(output_srt_path).write_text("\n".join(lines), encoding="utf-8")
    return output_srt_path
