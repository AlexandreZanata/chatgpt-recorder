#!/usr/bin/env bash
# One explicit project check, without an agent harness or Git hook framework.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
npm run lint
python3 -m compileall -q src tools scripts
bash scripts/run-tests.sh
bash scripts/package-extension.sh
python3 scripts/verify-package.py
python3 scripts/check-publication.py
