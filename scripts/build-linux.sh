#!/usr/bin/env bash
# Build the ecoclock-cli binary for Linux x86_64 using PyInstaller.
#
# Uso:
#   ./scripts/build-linux.sh
#
# Resultado:
#   dist/ecoclock-cli  (binario standalone, ~30 MB)
#
# Notas:
#   - Crea un venv aparte (.venv-build) para no contaminar tu Python global.
#   - Requiere python3 (probado con 3.12/3.13; en 3.14 PyInstaller puede
#     necesitar ajustes, ver README).
#   - No toca tu server ni tu base de datos.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="$ROOT/build"
DIST_DIR="$ROOT/dist"
SPEC="$ROOT/client/cli.spec"
VENV_DIR="$ROOT/.venv-build"

cd "$ROOT"

echo "==> Limpiando build/ y dist/"
rm -rf "$BUILD_DIR" "$DIST_DIR"

if [ ! -d "$VENV_DIR" ]; then
	echo "==> Creando venv de build en $VENV_DIR"
	python3 -m venv "$VENV_DIR"
fi

echo "==> Activando venv de build"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "==> Actualizando pip"
pip install --quiet --upgrade pip

echo "==> Instalando dependencias de runtime + PyInstaller"
pip install --quiet -r client/requirements.txt
pip install --quiet pyinstaller

echo "==> Ejecutando PyInstaller con $SPEC"
pyinstaller "$SPEC"

echo ""
echo "==> Binario generado:"
ls -lh "$DIST_DIR/ecoclock-cli"
echo ""
echo "==> Smoke test: --help"
"$DIST_DIR/ecoclock-cli" --help | head -20 || true

echo ""
echo "==> Smoke test: --version (si existe)"
"$DIST_DIR/ecoclock-cli" --version 2>/dev/null || echo "(no --version, OK)"

echo ""
echo "Listo. Para usar:"
echo "  $DIST_DIR/ecoclock-cli --base-url https://api.ecoclock.org login"
