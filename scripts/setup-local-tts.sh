#!/usr/bin/env bash
# Optional local speech environment, separate from Fooocus and the desktop GUI.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SPEECH_ENV="${PROJECT_DIR}/.local/tts-venv"
python3 -m venv "${SPEECH_ENV}"
"${SPEECH_ENV}/bin/python" -m pip install --upgrade pip
"${SPEECH_ENV}/bin/python" -m pip install -r "${PROJECT_DIR}/requirements-tts.txt"
"${SPEECH_ENV}/bin/python" -c 'from qwen_tts import Qwen3TTSModel; import torch; print("Speech engine ready. CUDA available:", torch.cuda.is_available())'
echo "Restart the video app. Model weights download on your first voice test."
