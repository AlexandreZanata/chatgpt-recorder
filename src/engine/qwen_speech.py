"""Isolated Qwen speech process; never changes the desktop's Python environment."""

from collections import deque
import json
from pathlib import Path
import subprocess

from src.engine.gpu_environment import speech_environment
from src.core.narration import NARRATION_PROFILE

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SPEECH_PYTHON = PROJECT_ROOT / ".local" / "tts-venv" / "bin" / "python"


class QwenSpeechAdapter:
    def __init__(self, python_path=SPEECH_PYTHON):
        self.python_path = Path(python_path)
        self.process = None

    def cancel(self):
        process = self.process
        if process is not None and process.poll() is None:
            process.terminate()

    def synthesize(self, request, chunks, output, progress, cancelled):
        if not self.python_path.is_file():
            raise RuntimeError("Speech engine not installed. Run: bash scripts/setup-local-tts.sh")
        payload = {"request": request.payload(), "chunks": chunks, "output": str(output),
                   "profile": NARRATION_PROFILE}
        progress("Starting local speech engine; first use may download the selected model...")
        errors = deque(maxlen=12)
        process = subprocess.Popen(
            [str(self.python_path), "-u", "-m", "src.engine.qwen_runner"],
            cwd=PROJECT_ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding="utf-8",
            env={**speech_environment(self.python_path),
                 "HF_HOME": str(PROJECT_ROOT / ".local" / "tts-model-cache")},
        )
        self.process = process
        try:
            if cancelled():
                self.cancel()
                raise InterruptedError("Narration generation cancelled.")
            process.stdin.write(json.dumps(payload, ensure_ascii=False))
            process.stdin.close()
            for line in process.stdout:
                if line.startswith("TTS_PROGRESS:"):
                    progress(line.removeprefix("TTS_PROGRESS:").strip())
                else:
                    errors.append(line.strip()[:500])
            status = process.wait()
            if cancelled():
                raise InterruptedError("Narration generation cancelled.")
            if status:
                detail = next((line for line in reversed(errors) if line), "Unknown engine error.")
                raise RuntimeError(f"Local speech failed: {detail}")
        finally:
            self.cancel()
            process.wait(timeout=10)
            process.stdout.close()
            self.process = None
