#!/usr/bin/env bash
# Script to install ChatGPT Audio Capture Extension permanently in Firefox via Enterprise Policies

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
XPI_PATH="${PROJECT_ROOT}/dist/chatgpt-audio-capture-v0.1.0.xpi"

if [ ! -f "${XPI_PATH}" ]; then
  echo "[error] XPI package not found at ${XPI_PATH}. Run 'npm run build' first."
  exit 1
fi

echo "[info] Installing extension permanently in Firefox..."

# Create distribution directories if they don't exist
sudo mkdir -p /etc/firefox/policies
sudo mkdir -p /usr/lib/firefox/distribution/policies 2>/dev/null || true

# Write policies.json
POLICIES_JSON="{
  \"policies\": {
    \"ExtensionSettings\": {
      \"chatgpt-audio-capture@zaflas.local\": {
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

echo "[ok] ChatGPT Audio Capture extension registered permanently in Firefox Enterprise Policies!"
echo "[ok] Please restart Firefox and check about:addons to see your permanent extension."
