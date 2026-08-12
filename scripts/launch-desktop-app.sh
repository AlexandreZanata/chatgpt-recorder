#!/usr/bin/env bash
# Desktop Application Launcher Shell Script

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$ROOT:${PYTHONPATH:-}"

cd "$ROOT"

exec python3 "$ROOT/app_desktop.py" "$@"
