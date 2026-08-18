#!/usr/bin/env bash
# Launcher for AI Image Studio (Fooocus SDXL on RTX 4060 — Rock-Solid Safe Mode)

set -uo pipefail

TARGET_DIR="${HOME}/PESSOAL-PROJETOS-ALEXANDRE/Fooocus"
VENV_DIR="${TARGET_DIR}/venv"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -d "${VENV_DIR}" ]; then
  echo "[info] Ambiente virtual não encontrado. Iniciando setup automático..."
  bash "${SCRIPT_DIR}/setup-ai-image-studio.sh"
fi

cd "${TARGET_DIR}"

export PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True"
export CUDA_MODULE_LOADING="LAZY"

echo "=========================================================="
echo " ⚡ Iniciando AI Image Studio — RTX 4060 (Estabilidade Total)"
echo " 🛡️ VRAM Segura: 5.5GB para IA + 2.5GB para Desktop (Zero Freeze)"
echo "=========================================================="

"${VENV_DIR}/bin/python" launch.py \
  --listen 127.0.0.1 \
  --port 7865 \
  --gpu-device-id 0 \
  --in-browser \
  --always-normal-vram \
  --attention-pytorch \
  --async-cuda-allocation

echo ""
read -r -p "Pressione Enter para fechar..."
