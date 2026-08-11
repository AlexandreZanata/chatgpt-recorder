"""Subtitle Generation and ASS Formatting Module with GPU-accelerated faster-whisper."""

from pathlib import Path


def format_ass_time(seconds: float) -> str:
    """Format seconds float into ASS timestamp H:MM:SS.cs."""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centisecs = int(round((seconds - int(seconds)) * 100))
    if centisecs >= 100:
        secs += 1
        centisecs = 0
    return f"{hrs}:{mins:02d}:{secs:02d}.{centisecs:02d}"


def generate_ass_content(
    segments: list[dict],
    font_name: str = "DejaVu Sans",
    font_size: int = 24,
    primary_color: str = "&H00FFFFFF",
    outline_color: str = "&H00000000",
) -> str:
    """Build ASS subtitle file content from segment timestamps."""
    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "PlayResX: 1920\n"
        "PlayResY: 1080\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,{font_name},{font_size},{primary_color},&H000000FF,{outline_color},"
        "&H80000000,1,0,0,0,100,100,0,0,1,2,1,2,20,20,40,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )

    events = []
    for seg in segments:
        start_str = format_ass_time(seg["start"])
        end_str = format_ass_time(seg["end"])
        text = seg["text"].strip()
        events.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{text}")

    return header + "\n".join(events) + "\n"


def save_ass_subtitles(
    segments: list[dict],
    output_path: Path,
    font_name: str = "DejaVu Sans",
    font_size: int = 24,
) -> Path:
    """Generate and write ASS subtitle file to disk."""
    content = generate_ass_content(segments, font_name=font_name, font_size=font_size)
    output_path.write_text(content, encoding="utf-8")
    return output_path


def transcribe_audio_to_ass(
    audio_path: Path,
    output_ass_path: Path,
    font_name: str = "DejaVu Sans",
    font_size: int = 24,
    model_size: str = "tiny.en",
) -> Path | None:
    """Transcribe audio to ASS subtitles using GPU-accelerated faster-whisper."""
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel(model_size, device="cuda", compute_type="float16")
        segments, _ = model.transcribe(str(audio_path), language="en", vad_filter=True)
        seg_list = [{"start": s.start, "end": s.end, "text": s.text} for s in segments]
        return save_ass_subtitles(seg_list, output_ass_path, font_name=font_name, font_size=font_size)
    except Exception as err:
        print(f"Subtitle transcription warning: {err}")
        return None
