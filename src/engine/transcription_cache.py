"""Reuse complete ASR results without changing the recognition model or settings."""

import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
import math
import os
from pathlib import Path
from tempfile import mkstemp

CACHE_DIR = Path(__file__).resolve().parents[2] / ".local" / "transcription-cache"


def engine_versions():
    versions = []
    for package in ("faster-whisper", "ctranslate2"):
        try:
            versions.append(version(package))
        except PackageNotFoundError:
            versions.append("unavailable")
    return versions


def cache_key(audio_path, model, language, words):
    options = ["asr-cache-v1-beam1-vad", model, language, words, engine_versions()]
    digest = hashlib.sha256(json.dumps(options, sort_keys=True).encode())
    with Path(audio_path).open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def valid_segments(segments):
    if not isinstance(segments, list) or not segments:
        return False
    try:
        for segment in segments:
            start, end = float(segment["start"]), float(segment["end"])
            if not math.isfinite(start) or not math.isfinite(end):
                return False
            if start < 0 or end <= start:
                return False
            if not isinstance(segment["text"], str) or not segment["text"].strip():
                return False
    except (TypeError, KeyError, ValueError):
        return False
    return True


def save_entry(path, segments):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = mkstemp(prefix=".transcription-", suffix=".part", dir=path.parent)
    partial = Path(temporary)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(segments, output, ensure_ascii=False, allow_nan=False)
        partial.replace(path)
    finally:
        partial.unlink(missing_ok=True)


def cached_transcription(audio_path, model_name, language, word_timestamps, transcribe,
                         cache_dir=None):
    try:
        folder = CACHE_DIR if cache_dir is None else Path(cache_dir)
        path = folder / f"{cache_key(audio_path, model_name, language, word_timestamps)}.json"
    except OSError:
        return transcribe(str(audio_path), model_name, language, word_timestamps)
    try:
        segments = json.loads(path.read_text(encoding="utf-8"))
        if valid_segments(segments):
            print("[Transcription] Reusing complete cached subtitle timestamps.")
            return segments
    except (OSError, ValueError):
        pass
    segments = transcribe(str(audio_path), model_name, language, word_timestamps)
    if valid_segments(segments):
        try:
            save_entry(path, segments)
        except (OSError, ValueError):
            pass  # Cache failures must not discard a successful transcription.
    return segments
