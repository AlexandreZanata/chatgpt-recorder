#!/usr/bin/env bash
# Fail when tests/golden/ and backend/ change together without golden-update: in
# the commit message.
#
# Message source (first match wins):
#   1) $1 — commit-msg hook file (lefthook {1})
#   2) $GIT_COMMIT_MESSAGE
#   3) .git/COMMIT_EDITMSG (may be stale on pre-commit with git commit -m)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "[golden-guard] not a git repo — skip"
  exit 0
fi

if ! git diff --cached --quiet 2>/dev/null; then
  STAGED_GOLDEN=$(git diff --cached --name-only -- 'tests/golden/' || true)
  STAGED_BACKEND=$(git diff --cached --name-only -- 'backend/' || true)
else
  echo "[golden-guard] no staged changes — skip"
  exit 0
fi

if [[ -z "${STAGED_GOLDEN}" || -z "${STAGED_BACKEND}" ]]; then
  echo "[golden-guard] OK — no simultaneous backend+golden staged change"
  exit 0
fi

MSG=""
if [[ -n "${1:-}" && -f "$1" ]]; then
  MSG=$(cat "$1")
elif [[ -n "${GIT_COMMIT_MESSAGE:-}" ]]; then
  MSG=$GIT_COMMIT_MESSAGE
elif [[ -f "${ROOT}/.git/COMMIT_EDITMSG" ]]; then
  MSG=$(cat "${ROOT}/.git/COMMIT_EDITMSG")
fi

if grep -q 'golden-update:' <<<"$MSG"; then
  echo "[golden-guard] OK — commit message contains golden-update:"
  exit 0
fi

echo "[golden-guard] FAILED — staged changes touch backend/ and tests/golden/"
echo "  Include 'golden-update:' in the commit message and review every snapshot diff."
echo "  Staged golden files:"
echo "$STAGED_GOLDEN" | sed 's/^/    /'
exit 1
