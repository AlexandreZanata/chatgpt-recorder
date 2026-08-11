#!/usr/bin/env bash
# Generate a self-signed test PKCS#12 for pyHanko unit/integration tests.
# Official: https://docs.openssl.org/master/man1/openssl-pkcs12/
#
# WARNING: This certificate is NOT ICP-Brasil. Never use it for real documents.
# Never commit the output under tests/fixtures/certs/ (gitignored).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${ROOT}/tests/fixtures/certs"
PASS="${PPG_TEST_PFX_PASSWORD:-test-a1-password}"
SUBJ="/C=BR/O=PPG Test/CN=TESTE NAO VALIDO:00000000000"

mkdir -p "${OUT}"
chmod 700 "${OUT}"

echo "============================================================" >&2
echo " WARNING: NOT an ICP-Brasil certificate." >&2
echo " For automated tests only. Never sign real documents with it." >&2
echo "============================================================" >&2

openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout "${OUT}/test-ca.key" \
  -out "${OUT}/test-ca.crt" \
  -days 3650 \
  -subj "/C=BR/O=PPG Test CA/CN=PPG TEST ROOT" \
  2>/dev/null

openssl req -newkey rsa:2048 -nodes \
  -keyout "${OUT}/test-leaf.key" \
  -out "${OUT}/test-leaf.csr" \
  -subj "${SUBJ}" \
  2>/dev/null

cat > "${OUT}/leaf.ext" <<'EOF'
basicConstraints=CA:FALSE
keyUsage=critical,digitalSignature,nonRepudiation
extendedKeyUsage=clientAuth,emailProtection
EOF

openssl x509 -req \
  -in "${OUT}/test-leaf.csr" \
  -CA "${OUT}/test-ca.crt" \
  -CAkey "${OUT}/test-ca.key" \
  -CAcreateserial \
  -out "${OUT}/test-leaf.crt" \
  -days 825 \
  -extfile "${OUT}/leaf.ext" \
  2>/dev/null

openssl pkcs12 -export \
  -out "${OUT}/test-a1.pfx" \
  -inkey "${OUT}/test-leaf.key" \
  -in "${OUT}/test-leaf.crt" \
  -certfile "${OUT}/test-ca.crt" \
  -passout "pass:${PASS}" \
  -name "ppg-test-a1" \
  2>/dev/null

# Expired leaf via cryptography (OpenSSL 3.0 may lack -not_before on x509 -req).
PPG_TEST_PFX_PASSWORD="${PASS}" OUT_DIR="${OUT}" python3 - <<'PY'
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

out = Path(os.environ["OUT_DIR"])
password = os.environ["PPG_TEST_PFX_PASSWORD"].encode()
key = serialization.load_pem_private_key(
    (out / "test-leaf.key").read_bytes(), password=None
)
ca_key = serialization.load_pem_private_key(
    (out / "test-ca.key").read_bytes(), password=None
)
ca_cert = x509.load_pem_x509_certificate((out / "test-ca.crt").read_bytes())
subject = x509.Name(
    [
        x509.NameAttribute(NameOID.COUNTRY_NAME, "BR"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "PPG Test"),
        x509.NameAttribute(NameOID.COMMON_NAME, "TESTE NAO VALIDO:00000000000"),
    ]
)
start = datetime(2020, 1, 1, tzinfo=timezone.utc)
cert = (
    x509.CertificateBuilder()
    .subject_name(subject)
    .issuer_name(ca_cert.subject)
    .public_key(key.public_key())
    .serial_number(99)
    .not_valid_before(start)
    .not_valid_after(start + timedelta(days=1))
    .sign(ca_key, hashes.SHA256())
)
pfx = pkcs12.serialize_key_and_certificates(
    name=b"ppg-test-expired",
    key=key,
    cert=cert,
    cas=[ca_cert],
    encryption_algorithm=serialization.BestAvailableEncryption(password),
)
(out / "expired-a1.pfx").write_bytes(pfx)
PY

chmod 600 "${OUT}"/*.pfx "${OUT}"/*.key
printf '%s\n' "${PASS}" > "${OUT}/pfx_password"
chmod 600 "${OUT}/pfx_password"

echo "Wrote ${OUT}/test-a1.pfx and ${OUT}/expired-a1.pfx" >&2
echo "Password file: ${OUT}/pfx_password (gitignored)" >&2
openssl pkcs12 -info -in "${OUT}/test-a1.pfx" -passin "pass:${PASS}" -noout
