#!/usr/bin/env bash
# Create GNOME Desktop Application Shortcut for AI Image Studio

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APPS_DIR="${HOME}/.local/share/applications"
DESKTOP_FILE="${APPS_DIR}/ai-image-studio.desktop"
LAUNCHER="${ROOT}/scripts/launch-ai-image-studio.sh"
ICON_PATH="${ROOT}/image-metadata-extractor/icons/app-icon.svg"

mkdir -p "${APPS_DIR}"
chmod +x "${LAUNCHER}"

cat <<EOF > "${DESKTOP_FILE}"
[Desktop Entry]
Version=1.0
Type=Application
Name=AI Image Studio (RTX 4060)
GenericName=Gerador de Imagens IA Local
Comment=Gerador de Imagens SDXL Local de Alta Qualidade sem Filtros
Exec=gnome-terminal -- bash -c "${LAUNCHER}; exec bash"
Icon=${ICON_PATH}
Terminal=false
Categories=Graphics;Photography;AI;
Keywords=Image;AI;SDXL;Fooocus;Generation;
StartupNotify=true
EOF

chmod +x "${DESKTOP_FILE}"
update-desktop-database "${APPS_DIR}" 2>/dev/null || true

echo "[ok] Atalho de aplicativo criado com sucesso em:"
echo "     ${DESKTOP_FILE}"
echo "[ok] O 'AI Image Studio (RTX 4060)' agora está disponível no menu de aplicativos do Pop!_OS!"
