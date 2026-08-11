#!/usr/bin/env bash
# Full quality gate used by Lefthook pre-commit and `npm run verify`.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

GATE_START=$(date +%s)

step() {
  local num="$1"
  local total="$2"
  local label="$3"
  shift 3
  local started ended elapsed
  started=$(date +%s)
  echo ""
  echo "${num}/${total} ${label}"
  "$@"
  ended=$(date +%s)
  elapsed=$((ended - started))
  echo "  → ${elapsed}s"
}

echo "=== chatgpt-recorder quality gate ==="

step 1 4 "Size + complexity (file<=200, function<=80, cyclomatic<=10)" \
  python3 "$ROOT/scripts/check_size_complexity.py" --root "$ROOT" "$@"

step 2 4 "Lint (0 errors, 0 warnings)" \
  bash "$ROOT/scripts/check-lint.sh"

step 3 4 "System / compile (0 errors)" \
  bash "$ROOT/scripts/check-system.sh"

step 4 4 "Unit / Integration tests" \
  bash "$ROOT/scripts/run-tests.sh"

GATE_END=$(date +%s)
GATE_ELAPSED=$((GATE_END - GATE_START))
echo ""
echo "=== All quality gates passed (${GATE_ELAPSED}s) ==="
