#!/usr/bin/env bash
# Repeatable Ubuntu/Debian setup; private accounts and media are never reset.
set -euo pipefail
umask 077
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
OPEN=1
DEPS=1
for option in "$@"; do
  case "$option" in
    --no-open) OPEN=0 ;;
    --skip-system-deps) DEPS=0 ;;
    -h|--help) echo 'Usage: bash scripts/install-linux.sh [--no-open] [--skip-system-deps]'; exit 0 ;;
    *) echo "Unknown option: $option" >&2; exit 2 ;;
  esac
done
if [[ "$EUID" == 0 ]]; then
  echo 'Run as the desktop owner, without sudo. Only missing OS packages require administrator access.' >&2
  exit 1
fi
if [[ "$(uname -s)" != Linux || "$(uname -m)" != x86_64 ]]; then
  echo 'Assisted installation currently supports Linux x86_64.' >&2
  exit 1
fi
if [[ "$DEPS" == 1 ]]; then
  PACKAGES=(python3-venv ffmpeg xvfb libegl1 libopengl0 libxkbcommon0 libpulse0 libxcb-cursor0 libnss3 libgbm1 libasound2t64)
  # Debian releases before the t64 transition use libasound2 instead.
  if ! apt-cache show libasound2t64 >/dev/null 2>&1; then
    PACKAGES[${#PACKAGES[@]}-1]=libasound2
  fi
  MISSING=()
  for package in "${PACKAGES[@]}"; do
    if [[ "$(dpkg-query -W -f='${Status}' "$package" 2>/dev/null || true)" != 'install ok installed' ]]; then
      MISSING+=("$package")
    fi
  done
  if ((${#MISSING[@]})); then
    ADMIN=(sudo)
    if ! command -v sudo >/dev/null; then ADMIN=(pkexec); fi
    "${ADMIN[@]}" apt-get update
    "${ADMIN[@]}" apt-get install -y "${MISSING[@]}"
  fi
fi
python3 -c 'import sys; assert sys.version_info >= (3, 11), "Python 3.11 or newer is required"'
if [[ ! -x .venv/bin/python ]]; then python3 -m venv .venv; fi
PYTHON="$ROOT/.venv/bin/python"
# Keep an existing CPU/CUDA installation. A new PC gets the official CPU build.
if ! "$PYTHON" -c 'import torch' >/dev/null 2>&1; then
  "$PYTHON" -m pip install torch --index-url https://download.pytorch.org/whl/cpu
fi
"$PYTHON" -m pip install -r requirements-desktop.txt
"$PYTHON" -m pip check
"$PYTHON" scripts/build-chrome.py
"$PYTHON" -m tools.ytbot.browser_install
"$PYTHON" -m tools.ytbot.onboarding
if [[ "$OPEN" == 1 ]]; then
  exec "$PYTHON" -m tools.ytbot accounts ui
fi
