#!/usr/bin/env bash
# Package ChatGPT Image Extractor Extension into ZIP and XPI

set -euo pipefail

MODULE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${MODULE_ROOT}/.." && pwd)"
DIST_DIR="${PROJECT_ROOT}/dist"
ZIP_NAME="chatgpt-image-extractor-v0.1.0.zip"
XPI_NAME="chatgpt-image-extractor-v0.1.0.xpi"

mkdir -p "${DIST_DIR}"

cd "${MODULE_ROOT}"

echo "[package] Creating Image Extractor distribution package..."
zip -r -FS "${DIST_DIR}/${ZIP_NAME}" \
  manifest.json \
  popup.html \
  src/ \
  icons/

cp "${DIST_DIR}/${ZIP_NAME}" "${DIST_DIR}/${XPI_NAME}"

echo "[package] OK — Created ${DIST_DIR}/${ZIP_NAME} and ${DIST_DIR}/${XPI_NAME}"
