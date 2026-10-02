#!/usr/bin/env bash
# Instala el lanzador e icono de Eco'clock para el usuario actual (sin sudo).
# Uso: ./install-desktop.sh ruta/al/logo.png
set -euo pipefail

ICON_SRC="${1:?Uso: $0 ruta/al/logo.png (idealmente 256x256 o mayor)}"
APPS="$HOME/.local/share/applications"
ICONS="$HOME/.local/share/icons/hicolor/256x256/apps"

mkdir -p "$APPS" "$ICONS"
cp "$ICON_SRC" "$ICONS/ecoclock.png"
cp "$(dirname "$0")/ecoclock.desktop" "$APPS/ecoclock.desktop"

# Verifica que ecoclock-gui está en el PATH
command -v ecoclock-gui >/dev/null || \
  echo "Aviso: ecoclock-gui no está en el PATH (¿pipx ensurepath?)"

update-desktop-database "$APPS" 2>/dev/null || true
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
echo "Listo: busca 'Eco'clock' en el menú de aplicaciones."
