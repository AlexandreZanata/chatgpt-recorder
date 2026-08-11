#!/usr/bin/env bash
# Nightly integrity sample: SQLite PRAGMA + audit chain (phase 25).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Prefer venv python when deployed.
PY="${PPG_PYTHON:-}"
if [[ -z "$PY" && -x /opt/ppg/venv/bin/python ]]; then
  PY=/opt/ppg/venv/bin/python
elif [[ -z "$PY" ]]; then
  PY=python3
fi

# Resolve KEK file for CLI when systemd credential name is used.
if [[ "${PPG_KEK:-}" == "kek" && -f /etc/credstore/ppg.kek ]]; then
  export PPG_KEK="$(tr -d '\n' </etc/credstore/ppg.kek)"
fi

"$PY" scripts/ppg-db.py integrity-check
"$PY" scripts/ppg-audit.py verify
echo "integrity ok"
