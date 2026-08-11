#!/usr/bin/env bash
# Package extension files into dist/ zip distribution archive
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DIST_DIR="$ROOT/dist"
ZIP_FILE="$DIST_DIR/chatgpt-audio-capture-v0.1.0.zip"

mkdir -p "$DIST_DIR"
rm -f "$ZIP_FILE"

echo "[package] Creating extension distribution package: $ZIP_FILE"
zip -r "$ZIP_FILE" manifest.json popup.html src/ icons/ README.md >/dev/null

echo "[package] OK — Package created at $ZIP_FILE"
