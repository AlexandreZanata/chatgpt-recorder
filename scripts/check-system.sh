#!/usr/bin/env bash
# System / compile gate: 0 errors when build/typecheck script exists.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ran_any=false

if [[ -f "package.json" ]]; then
  if node -e "const p=require('./package.json'); process.exit(p.scripts && p.scripts.typecheck ? 0 : 1)"; then
    ran_any=true
    echo "[system] Running npm run typecheck..."
    npm run typecheck
  fi
fi

if ! $ran_any; then
  echo "[system] No compile/typecheck script needed yet — OK."
  exit 0
fi

echo "[system] OK — 0 errors"
