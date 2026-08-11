#!/usr/bin/env bash
# Desktop Application Launcher Shell Script

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH="/home/iiii/.pyenv/shims:/home/iiii/.pyenv/bin:$PATH"
export PYTHONPATH="$ROOT:${PYTHONPATH:-}"

cd "$ROOT"
if command -v python3 >/dev/null 2>&1; then
  exec python3 "$ROOT/app_desktop.py" "$@"
else
  exec /home/iiii/.pyenv/versions/3.12.2/bin/python3 "$ROOT/app_desktop.py" "$@"
fi
