#!/usr/bin/env bash
# Install an ICP-Brasil A1 PKCS#12 onto the host for PAdES signing.
# Run on the VPS as root. Password is read from stdin (never argv / env export).
# Official: docs/SIGNING-RUNBOOK.md · systemd CREDENTIALS.
set -euo pipefail

PFX_SRC="${1:-}"
DEST_DIR=/etc/ppg/certs
DEST_PFX="$DEST_DIR/a1.pfx"
CRED_FILE=/etc/credstore/ppg.pfx-password
ENV_FILE=/etc/ppg/ppg.env

die() { echo "[install-a1] ERROR: $*" >&2; exit 1; }
note() { echo "[install-a1] $*"; }

[[ "$(id -u)" -eq 0 ]] || die "run as root on the VPS"
[[ -n "$PFX_SRC" && -f "$PFX_SRC" ]] || die "usage: $0 /path/to/a1.pfx  < pfx-password.txt"
id ppg &>/dev/null || die "user ppg missing — run deploy/bootstrap-vps.sh first"

install -d -o ppg -g ppg -m 0700 "$DEST_DIR"
install -o ppg -g ppg -m 0400 "$PFX_SRC" "$DEST_PFX"
note "installed $DEST_PFX (0400 ppg:ppg)"

install -d -o root -g root -m 0700 /etc/credstore
# First line only; strip CR; do not echo the secret.
tr -d '\r' | head -n 1 | install -m 0400 /dev/stdin "$CRED_FILE"
[[ -s "$CRED_FILE" ]] || die "empty password on stdin"
note "wrote $CRED_FILE (0400 root)"

if [[ -f "$ENV_FILE" ]]; then
  if grep -qE '^[[:space:]]*PPG_SIGN_PFX_PATH=' "$ENV_FILE"; then
    sed -i 's|^[[:space:]]*#\?[[:space:]]*PPG_SIGN_PFX_PATH=.*|PPG_SIGN_PFX_PATH=/etc/ppg/certs/a1.pfx|' \
      "$ENV_FILE"
  else
    printf '\nPPG_SIGN_PFX_PATH=/etc/ppg/certs/a1.pfx\n' >>"$ENV_FILE"
  fi
  # Ensure production never keeps a password in the env file.
  sed -i '/^[[:space:]]*PPG_SIGN_PFX_PASSWORD=/d' "$ENV_FILE"
  note "enabled PPG_SIGN_PFX_PATH in $ENV_FILE"
else
  note "WARN: $ENV_FILE missing — set PPG_SIGN_PFX_PATH=/etc/ppg/certs/a1.pfx after deploy"
fi

if systemctl is-enabled ppg.service &>/dev/null; then
  systemctl reload-or-restart ppg.service
  note "restarted ppg.service"
fi

note "done. Confirm: curl -fsS http://127.0.0.1:8000/readyz | jq .signing"
note "expect: \"configured\" — password is NOT in ppg.env (systemd LoadCredential)."
