#!/usr/bin/env bash
# Run gated suites under coverage.py and enforce package thresholds.
# Official: https://coverage.readthedocs.io/en/latest/cmd.html#json-reporting
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v coverage >/dev/null 2>&1; then
  echo "[coverage] FAIL: coverage not on PATH. pip install -r requirements-dev.txt" >&2
  exit 1
fi

run_suite() {
  local suite_id="$1"
  local rc=0
  echo "[coverage] suite=${suite_id}"
  set +e
  coverage run -a -m unittest discover \
    -s "${ROOT}/tests/${suite_id}" -p 'test_*.py' -t "${ROOT}"
  rc=$?
  set -e
  # unittest exits 5 when the suite is still empty
  if [[ "${rc}" -eq 5 || "${rc}" -eq 0 ]]; then
    return 0
  fi
  return "${rc}"
}

echo "[coverage] Running gated suites: unit contract integration security"
coverage erase
run_suite unit
run_suite contract
run_suite integration
run_suite security

coverage json -o "${ROOT}/coverage.json"
coverage report
python3 "${ROOT}/scripts/quality/coverage_thresholds.py" "${ROOT}/coverage.json"
echo "[coverage] OK"
