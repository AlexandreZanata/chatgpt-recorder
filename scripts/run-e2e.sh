#!/usr/bin/env bash
# Run Playwright e2e against a real uvicorn (opt-in; not part of npm run verify).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! python3 -c "from playwright.sync_api import sync_playwright" 2>/dev/null; then
  echo "Playwright Python package missing. Install: pip install -r requirements-dev.txt" >&2
  exit 1
fi

if ! python3 -c "from playwright.sync_api import sync_playwright; sync_playwright().start().chromium.launch().close()" 2>/dev/null; then
  echo "Chromium for Playwright is not installed."
  if [[ -t 0 ]]; then
    read -r -p "Install Chromium now? [y/N] " ans
    if [[ "${ans:-}" =~ ^[Yy]$ ]]; then
      python3 -m playwright install chromium
    else
      echo "Aborted. Run: python3 -m playwright install chromium" >&2
      exit 1
    fi
  else
    echo "Non-interactive shell — installing Chromium…"
    python3 -m playwright install chromium
  fi
fi

export PPG_E2E=1
mkdir -p .local/tmp/e2e

echo "======== e2e (PPG_E2E=1) ========"
set +e
python3 -m unittest discover -s "$ROOT/tests/e2e" -p 'test_*.py' -t "$ROOT" -v
rc=$?
set -e

if [[ "$rc" -eq 0 ]]; then
  echo "e2e summary: PASS"
else
  echo "e2e summary: FAIL (rc=$rc)"
  echo "Artifacts (if any): .local/tmp/e2e/"
fi
exit "$rc"
