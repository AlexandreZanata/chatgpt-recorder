#!/usr/bin/env bash
# Automated Setup for AI Image Studio (Fooocus SDXL on RTX 4060)

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="${HOME}/PESSOAL-PROJETOS-ALEXANDRE/Fooocus"
VENV_DIR="${TARGET_DIR}/venv"

echo "=========================================================="
echo " 🎨 AI Image Studio (Fooocus SDXL) — Setup para RTX 4060"
echo "=========================================================="

if [ ! -d "${TARGET_DIR}" ]; then
  echo "[1/4] Clonando repositório do Fooocus..."
  git clone https://github.com/lllyasviel/Fooocus.git "${TARGET_DIR}"
else
  echo "[1/4] Repositório Fooocus já existente em ${TARGET_DIR}."
fi

cd "${TARGET_DIR}"

if [ ! -d "${VENV_DIR}" ]; then
  echo "[2/4] Criando ambiente virtual Python (venv)..."
  python3 -m venv "${VENV_DIR}"
fi

echo "[3/4] Instalando PyTorch com aceleração CUDA para RTX 4060..."
"${VENV_DIR}/bin/pip" install --upgrade pip
"${VENV_DIR}/bin/pip" install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

echo "[4/4] Instalando dependências do Fooocus..."
"${VENV_DIR}/bin/pip" install -r requirements_versions.txt

echo ""
echo "=========================================================="
echo " ✅ Instalação do AI Image Studio concluída com sucesso!"
echo "=========================================================="
