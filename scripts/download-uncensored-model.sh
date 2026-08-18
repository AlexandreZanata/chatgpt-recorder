#!/usr/bin/env bash
# Download High-Quality Uncensored SDXL Photorealistic Model (RealVisXL V4.0)

set -euo pipefail

MODELS_DIR="${HOME}/PESSOAL-PROJETOS-ALEXANDRE/Fooocus/models/checkpoints"
MODEL_NAME="RealVisXL_V4.0.safetensors"
MODEL_URL="https://huggingface.co/SG161222/RealVisXL_V4.0/resolve/main/RealVisXL_V4.0.safetensors"
DEST_FILE="${MODELS_DIR}/${MODEL_NAME}"

mkdir -p "${MODELS_DIR}"

echo "=========================================================="
echo " 📥 Download de Modelo Fotorrealista Sem Censura (SDXL)"
echo " 🌟 Modelo: RealVisXL V4.0 (Máxima Qualidade e Detalhes)"
echo " 📂 Destino: ${DEST_FILE}"
echo "=========================================================="

if [ -f "${DEST_FILE}" ]; then
  echo "[ok] O modelo ${MODEL_NAME} já está baixado e pronto para uso!"
  exit 0
fi

echo "[info] Iniciando download com suporte a resumo (-c)..."
wget -c --progress=bar:force "${MODEL_URL}" -O "${DEST_FILE}"

echo ""
echo "=========================================================="
echo " ✅ Modelo RealVisXL V4.0 baixado com sucesso!"
echo " 👉 Abra o Fooocus e selecione '${MODEL_NAME}' no menu 'Base Model'!"
echo "=========================================================="
