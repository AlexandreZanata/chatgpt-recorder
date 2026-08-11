#!/usr/bin/env bash
# Encrypted backup: VACUUM INTO + age (phase 25 minimal; full DR in phase 24).
# Official: https://www.sqlite.org/lang_vacuum.html · https://github.com/FiloSottile/age
set -euo pipefail

OUT_DIR="${PPG_BACKUP_DIR:-/var/backups/ppg}"
RECIPIENT="${PPG_BACKUP_AGE_RECIPIENT:-}"
DB_PATH="${PPG_DB_PATH:-/var/lib/ppg/app.db}"
BLOB_DIR="${PPG_BLOB_DIR:-/var/lib/ppg/documents}"
DRY_RUN=0
VERIFY=0

usage() {
  echo "Usage: ppg-backup.sh [--dry-run] [--verify] [--out-dir DIR]" >&2
  exit 2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    --verify) VERIFY=1 ;;
    --out-dir) OUT_DIR="$2"; shift ;;
    -h|--help) usage ;;
    *) usage ;;
  esac
  shift
done

[[ -n "$RECIPIENT" ]] || { echo "PPG_BACKUP_AGE_RECIPIENT required" >&2; exit 1; }
command -v age >/dev/null || { echo "age not installed" >&2; exit 1; }
command -v sqlite3 >/dev/null || { echo "sqlite3 not installed" >&2; exit 1; }

TS="$(date -u +%Y%m%dT%H%M%SZ)"
STAGE="$(mktemp -d "${TMPDIR:-/tmp}/ppg-backup.XXXXXX")"
trap 'rm -rf "$STAGE"' EXIT

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "dry-run ok recipient=$RECIPIENT db=$DB_PATH blobs=$BLOB_DIR out=$OUT_DIR"
  exit 0
fi

mkdir -p "$OUT_DIR"
chmod 700 "$OUT_DIR"
sqlite3 "$DB_PATH" "VACUUM INTO '${STAGE}/app.db';"
if [[ -d "$BLOB_DIR" ]]; then
  tar -C "$(dirname "$BLOB_DIR")" -cf "$STAGE/blobs.tar" "$(basename "$BLOB_DIR")"
else
  : >"$STAGE/blobs.tar"
fi
(
  cd "$STAGE"
  sha256sum app.db blobs.tar > manifest.sha256
  tar -cf - app.db blobs.tar manifest.sha256 \
    | age -r "$RECIPIENT" -o "$OUT_DIR/ppg-${TS}.tar.age"
)
chmod 600 "$OUT_DIR/ppg-${TS}.tar.age"
SIZE="$(stat -c%s "$OUT_DIR/ppg-${TS}.tar.age")"
echo "backup ok file=ppg-${TS}.tar.age bytes=$SIZE"

if [[ "$VERIFY" -eq 1 ]]; then
  [[ "$SIZE" -gt 64 ]] || { echo "verify failed: artifact too small" >&2; exit 1; }
  # Ciphertext must not look like SQLite.
  head -c 16 "$OUT_DIR/ppg-${TS}.tar.age" | grep -q 'SQLite format 3' \
    && { echo "verify failed: plaintext sqlite" >&2; exit 1; } || true
  echo "verify ok"
fi
