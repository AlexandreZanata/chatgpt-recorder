#!/usr/bin/env bash
# Test execution gate.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -d "./tests" ]] && find ./tests -type f \( -name '*.test.js' -o -name '*.test.mjs' \) -print 2>/dev/null | grep -q .; then
  echo "[test] Running node --test suite..."
  node --test tests/*.test.mjs
else
  echo "[test] No tests found yet in tests/ — OK."
fi
