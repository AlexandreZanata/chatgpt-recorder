#!/usr/bin/env bash
# Download Top 2 Ultra-Photorealistic Uncensored SDXL Models (RealVisXL V5.0 & CyberRealistic XL)

set -euo pipefail

MODELS_DIR="${HOME}/PESSOAL-PROJETOS-ALEXANDRE/Fooocus/models/checkpoints"
mkdir -p "${MODELS_DIR}"

echo "=========================================================="
echo " 📥 Download dos 2 Melhores Modelos Fotorrealistas Sem Censura"
echo " 📂 Destino: ${MODELS_DIR}"
echo "=========================================================="

# 1. RealVisXL V5.0 (FP16)
NAME_V5="RealVisXL_V5.0_fp16.safetensors"
URL_V5="https://huggingface.co/SG161222/RealVisXL_V5.0/resolve/main/RealVisXL_V5.0_fp16.safetensors"
DEST_V5="${MODELS_DIR}/${NAME_V5}"

echo ""
echo "[1/2] Verificando ${NAME_V5}..."
if [ -f "${DEST_V5}" ]; then
  echo "     ✓ ${NAME_V5} já está baixado!"
else
  echo "     Baixando ${NAME_V5}..."
  wget -c --progress=bar:force "${URL_V5}" -O "${DEST_V5}"
fi

# 2. CyberRealistic XL (v10 FP16)
NAME_CYBER="CyberRealisticXLPlay_V10.0_FP16.safetensors"
URL_CYBER="https://huggingface.co/cyberdelia/CyberRealisticXL/resolve/main/CyberRealisticXLPlay_V10.0_FP16.safetensors"
DEST_CYBER="${MODELS_DIR}/${NAME_CYBER}"

echo ""
echo "[2/2] Verificando ${NAME_CYBER}..."
if [ -f "${DEST_CYBER}" ]; then
  echo "     ✓ ${NAME_CYBER} já está baixado!"
else
  echo "     Baixando ${NAME_CYBER}..."
  wget -c --progress=bar:force "${URL_CYBER}" -O "${DEST_CYBER}"
fi

echo ""
echo "=========================================================="
echo " ✅ Todos os modelos fotorrealistas foram baixados!"
echo " 👉 Clique em 'Refresh All Files' na aba Models do Fooocus!"
echo "=========================================================="
