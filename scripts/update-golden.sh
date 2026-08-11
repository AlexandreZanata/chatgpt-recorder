#!/usr/bin/env bash
# Regenerate every tests/golden/ snapshot. Requires PPG_UPDATE_GOLDEN=1.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ "${PPG_UPDATE_GOLDEN:-}" != "1" ]]; then
  echo "refusing: set PPG_UPDATE_GOLDEN=1 to regenerate golden snapshots" >&2
  exit 1
fi

echo "=== updating golden snapshots ==="
BEFORE="$(mktemp)"
AFTER="$(mktemp)"
git status --short tests/golden/ >"$BEFORE" || true

PPG_UPDATE_GOLDEN=1 bash "$ROOT/scripts/run-tests.sh" immutability

git status --short tests/golden/ >"$AFTER" || true
echo ""
echo "=== golden changes ==="
if command -v diff >/dev/null; then
  diff -u "$BEFORE" "$AFTER" || true
fi
git diff --stat tests/golden/ || true
rm -f "$BEFORE" "$AFTER"
echo "done — review with: git diff tests/golden/"
