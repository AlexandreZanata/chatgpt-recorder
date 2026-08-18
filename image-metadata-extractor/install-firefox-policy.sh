#!/usr/bin/env bash
# Register ChatGPT Image & Metadata Extractor in Firefox Enterprise Policies

set -euo pipefail

MODULE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${MODULE_ROOT}/.." && pwd)"
XPI_PATH="${PROJECT_ROOT}/dist/chatgpt-image-extractor-v0.1.0.xpi"

if [ ! -f "${XPI_PATH}" ]; then
  bash "${MODULE_ROOT}/package-extension.sh"
fi

echo "[info] Installing ChatGPT Image Extractor permanently in Firefox..."

sudo mkdir -p /etc/firefox/policies
sudo mkdir -p /usr/lib/firefox/distribution/policies 2>/dev/null || true

POLICIES_JSON="{
  \"policies\": {
    \"ExtensionSettings\": {
      \"chatgpt-audio-capture@zaflas.local\": {
        \"installation_mode\": \"normal_installed\",
        \"install_url\": \"file://${PROJECT_ROOT}/dist/chatgpt-audio-capture-v0.1.0.xpi\"
      },
      \"chatgpt-image-extractor@zaflas.local\": {
        \"installation_mode\": \"normal_installed\",
        \"install_url\": \"file://${XPI_PATH}\"
      }
    }
  }
}"

echo "${POLICIES_JSON}" | sudo tee /etc/firefox/policies/policies.json > /dev/null
if [ -d "/usr/lib/firefox/distribution" ]; then
  echo "${POLICIES_JSON}" | sudo tee /usr/lib/firefox/distribution/policies/policies.json > /dev/null
fi

echo "[ok] ChatGPT Image & Metadata Extractor registered permanently in Firefox Policies!"
echo "[ok] Please restart Firefox to see the extension active in about:addons."
