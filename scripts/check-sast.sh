#!/usr/bin/env bash
# SEC-37/38/39: bandit + pip-audit + gitleaks (working tree and history).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PATH="${HOME}/.local/bin:${PATH}"

fail=0

echo "=== SAST / supply-chain gate ==="

echo ""
echo "[1/3] bandit (no High/Medium on backend + scripts)"
if bandit -ll -r backend scripts -q -f txt; then
  echo "  PASS: bandit clean (no High/Medium)"
else
  echo "  FAIL: bandit reported High/Medium findings"
  fail=1
fi

echo ""
echo "[2/3] pip-audit (requirements + requirements-dev)"
# PYSEC-2026-3412: WeasyPrint — no fix published yet; see docs/SECURITY.md ACC-002.
# Clear local intercept proxies (e.g. ZAP SOCKS) so the audit can reach PyPI.
# shellcheck disable=SC2030,SC2031
if env -u ALL_PROXY -u all_proxy -u HTTP_PROXY -u HTTPS_PROXY \
    -u http_proxy -u https_proxy \
    pip-audit -r requirements.txt -r requirements-dev.txt \
    --ignore-vuln PYSEC-2026-3412; then
  echo "  PASS: pip-audit clean (accepted ignores documented)"
else
  echo "  FAIL: pip-audit found known vulnerabilities"
  fail=1
fi

echo ""
echo "[3/3] gitleaks (working tree + git history)"
if ! command -v gitleaks >/dev/null 2>&1; then
  echo "  FAIL: gitleaks not on PATH (install to ~/.local/bin)"
  fail=1
else
  if gitleaks detect --no-banner --redact --source "$ROOT" \
      -c "$ROOT/.gitleaks.toml"; then
    echo "  PASS: gitleaks clean (tree + history)"
  else
    echo "  FAIL: gitleaks reported secrets"
    fail=1
  fi
fi

echo ""
if [[ "$fail" -ne 0 ]]; then
  echo "=== SAST gate FAILED ==="
  exit 1
fi
echo "=== SAST gate PASSED ==="
