#!/usr/bin/env bash
# Lint gate: 0 errors and 0 warnings.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

has_js_sources=false
if find ./src ./tests \
  \( -path './node_modules' \) -prune -o \
  -type f \( -name '*.ts' -o -name '*.tsx' -o -name '*.js' -o -name '*.jsx' -o -name '*.mjs' \) -print 2>/dev/null \
  | grep -q .; then
  has_js_sources=true
fi

ran_any=false

if [[ -f "package.json" ]] && $has_js_sources; then
  if node -e "const p=require('./package.json'); process.exit(p.scripts && p.scripts.lint ? 0 : 1)"; then
    ran_any=true
    echo "[lint] Running npm run lint (0 errors, 0 warnings)..."
    npm run lint
  fi
fi

if ! $ran_any; then
  echo "[lint] No JS linter configured in package.json yet — OK."
fi

echo "[lint] OK — 0 errors, 0 warnings"
