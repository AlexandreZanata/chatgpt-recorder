#!/usr/bin/env bash
# Desktop Application Launcher Shell Script

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH="/data/dev/python/shims:/home/iiii/.pyenv/shims:$PATH"
export PYTHONPATH="$ROOT:${PYTHONPATH:-}"

cd "$ROOT"

if [ -f "/data/dev/python/shims/python3" ]; then
  exec /data/dev/python/shims/python3 "$ROOT/app_desktop.py" "$@"
elif [ -f "/home/iiii/.pyenv/shims/python3" ]; then
  exec /home/iiii/.pyenv/shims/python3 "$ROOT/app_desktop.py" "$@"
else
  exec python3 "$ROOT/app_desktop.py" "$@"
fi
