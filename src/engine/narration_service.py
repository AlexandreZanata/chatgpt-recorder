"""Complete WAV publication and separate preview caches, independent of Qt."""

import os
from pathlib import Path
from shutil import copyfile
from tempfile import mkstemp
import wave

from src.core.narration import SpeechAdapter, SpeechRequest, split_narration


def valid_wav(path: Path) -> bool:
    try:
        with wave.open(str(path)) as audio:
            frames = audio.getnframes()
            if frames <= 0:
                return False
            frame_size = audio.getsampwidth() * audio.getnchannels()
            while frames:
                count = min(frames, 65536)
                if len(audio.readframes(count)) != count * frame_size:
                    return False
                frames -= count
            return True
    except (OSError, EOFError, wave.Error):
        return False


class NarrationService:
    def __init__(self, audio_dir: Path, adapter: SpeechAdapter):
        self.audio_dir, self.adapter = Path(audio_dir), adapter

    def generate(self, request: SpeechRequest, preview=False, progress=lambda message: None,
                 cancelled=lambda: False) -> Path:
        effective = request.excerpt() if preview else request
        folder = self.audio_dir / ("previews" if preview else "generated")
        folder.mkdir(parents=True, exist_ok=True)
        output = folder / f"qwen-{effective.cache_key()}.wav"
        if cancelled():
            raise InterruptedError("Narration generation cancelled.")
        if valid_wav(output):
            progress("Reusing completed narration.")
            return output
        descriptor, temporary = mkstemp(prefix=".narration-", suffix=".part", dir=folder)
        os.close(descriptor)
        partial = Path(temporary)
        try:
            excerpt = effective.excerpt()
            preview_file = self.audio_dir / "previews" / f"qwen-{excerpt.cache_key()}.wav"
            if not preview and split_narration(effective.text) == split_narration(excerpt.text) and valid_wav(preview_file):
                progress("Reusing voice test: it contains the complete narration with identical settings.")
                copyfile(preview_file, partial)
            else:
                self.adapter.synthesize(effective, split_narration(effective.text), partial, progress, cancelled)
            if cancelled():
                raise InterruptedError("Narration generation cancelled.")
            if not valid_wav(partial):
                raise RuntimeError("Speech engine did not produce a complete WAV.")
            partial.replace(output)
        finally:
            partial.unlink(missing_ok=True)
        return output
