#!/usr/bin/env bash
# Desktop Application Launcher Shell Script

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$ROOT:${PYTHONPATH:-}"

PYTHON_BIN=""
CANDIDATES=(
  "${HOME}/PESSOAL-PROJETOS-ALEXANDRE/Fooocus/venv/bin/python"
  "${ROOT}/.venv/bin/python"
  "${ROOT}/venv/bin/python"
  "${HOME}/.pyenv/shims/python3"
)

for candidate in "${CANDIDATES[@]}"; do
  if [ -x "${candidate}" ] && "${candidate}" -c "import PySide6" >/dev/null 2>&1; then
    PYTHON_BIN="${candidate}"
    break
  fi
done

if [ -z "${PYTHON_BIN}" ]; then
  PYTHON_BIN="$(command -v python3 || echo "python3")"
fi

cd "$ROOT"

if [ -t 1 ]; then
  exec "${PYTHON_BIN}" "$ROOT/app_desktop.py" "$@"
else
  exec "${PYTHON_BIN}" "$ROOT/app_desktop.py" "$@" > /tmp/chatgpt-video-studio.log 2>&1
fi
