#!/usr/bin/env bash
# Launcher for AI Image Studio (Fooocus SDXL on RTX 4060)

set -euo pipefail

TARGET_DIR="${HOME}/PESSOAL-PROJETOS-ALEXANDRE/Fooocus"
VENV_DIR="${TARGET_DIR}/venv"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -d "${VENV_DIR}" ]; then
  echo "[info] Ambiente virtual não encontrado. Iniciando setup automático..."
  bash "${SCRIPT_DIR}/setup-ai-image-studio.sh"
fi

cd "${TARGET_DIR}"

echo "[info] Iniciando AI Image Studio (Fooocus) na GPU RTX 4060..."
"${VENV_DIR}/bin/python" launch.py --listen 127.0.0.1 --port 7865 --gpu-device-id 0 --auto-launch
