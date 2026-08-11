#!/usr/bin/env bash
# Test execution gate.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -d "./tests" ]] && find ./tests -type f \( -name '*.test.js' -o -name '*.test.mjs' \) -print 2>/dev/null | grep -q .; then
  echo "[test] Running node --test suite..."
  node --test tests/*.test.mjs
fi

if [[ -d "./tests" ]] && find ./tests -type f -name 'test_*.py' -print 2>/dev/null | grep -q .; then
  echo "[test] Running python3 unittest suite..."
  python3 -m unittest discover -s tests/
fi

