"""Validated local speech requests and lossless, bounded text segmentation."""

from dataclasses import dataclass, replace
import hashlib
import json
import re
from typing import Protocol

MODELS = {
    "0.6B": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
    "1.7B": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
}
VOICES = {
    "Aiden": "American male · clear, bright",
    "Ryan": "English male · rhythmic, energetic",
    "Serena": "Chinese female · warm, gentle",
    "Vivian": "Chinese female · bright, youthful",
    "Uncle_Fu": "Chinese male · low, mellow",
    "Dylan": "Chinese male · youthful, Beijing",
    "Eric": "Chinese male · slightly husky, Sichuan",
    "Ono_Anna": "Japanese female · playful, light",
    "Sohee": "Korean female · warm, expressive",
}
DEFAULT_VOICE = "Uncle_Fu"
VOICE_SEED = 321
VOICE_REFERENCE_SHA256 = "37c0f7ecb126f36e96723cef6e9f7d6f9efc251879ae9cf5e32981b6399ada76"
NARRATION_PROFILE = "qwen-uncle-fu-base-icl-english-seed321-v4:" + VOICE_REFERENCE_SHA256


@dataclass(frozen=True)
class SpeechRequest:
    text: str
    voice: str = DEFAULT_VOICE
    language: str = "English"
    model: str = "0.6B"
    instruction: str = ""

    def __post_init__(self):
        if not isinstance(self.text, str) or not self.text.strip():
            raise ValueError("Paste narration text before generating speech.")
        if self.voice != DEFAULT_VOICE:
            raise ValueError("Narration is locked to Uncle_Fu, your selected default voice.")
        if self.language != "English":
            raise ValueError("Narration language is locked to English for all scripts.")
        if self.model not in MODELS:
            raise ValueError("Select a supported speech model.")

    def payload(self):
        return {"text": self.text, "voice": self.voice, "language": self.language,
                "model": self.model, "instruction": ""}

    def cache_key(self):
        payload = json.dumps(self.payload(), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256((NARRATION_PROFILE + ":" + payload).encode()).hexdigest()[:24]

    def excerpt(self):
        return replace(self, text=preview_text(self.text))


def preview_text(text: str, words: int = 60) -> str:
    """Audition the start of a script without silently shortening the full request."""
    return " ".join(text.split()[:words])


def split_narration(text: str, limit: int = 450) -> list[str]:
    """Prefer punctuation boundaries, but never discard a word or long token."""
    if limit < 1:
        raise ValueError("Chunk length must be positive.")
    remaining = " ".join(text.split())
    chunks = []
    while len(remaining) > limit:
        boundaries = list(re.finditer(r"[.!?;:]\s", remaining[:limit + 1]))
        split_at = boundaries[-1].start() + 1 if boundaries else remaining.rfind(" ", 0, limit + 1)
        if split_at <= 0:
            split_at = limit
        chunks.append(remaining[:split_at])
        remaining = remaining[split_at:].lstrip()
    if remaining:
        chunks.append(remaining)
    return chunks


class SpeechAdapter(Protocol):
    def synthesize(self, request, chunks, output, progress, cancelled):
        """Write a complete WAV or raise; report progress without exposing script text."""
