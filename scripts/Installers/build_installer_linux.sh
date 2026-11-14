#!/usr/bin/env bash
# Gera o instalador Linux (AppImage) do Iterador — um único arquivo executável, sem precisar de
# Python/CMake/compilador na máquina de quem vai usar. Ver Guide/usage.md > Gerar instalador e
# Guide/decisions/0035-packaging-and-installers.md.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [ -f .venv/bin/activate ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

./scripts/build_backend.sh

pip install --quiet pyinstaller

VERSION=$(python3 -c "
import sys
sys.path.insert(0, 'UI')
from iterador_ui.version import APP_VERSION
print(APP_VERSION)
")

rm -rf build dist-installers/dist
pyinstaller --noconfirm --distpath dist-installers/dist --workpath build scripts/packaging/iterador.spec

CACHE_DIR="$HOME/.cache/iterador-packaging"
mkdir -p "$CACHE_DIR"
APPIMAGETOOL="$CACHE_DIR/appimagetool-x86_64.AppImage"
if [ ! -x "$APPIMAGETOOL" ]; then
  echo "Baixando appimagetool (uma vez só, fica em $CACHE_DIR)..."
  curl -sL -o "$APPIMAGETOOL" \
    https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
  chmod +x "$APPIMAGETOOL"
fi

APPDIR="build/AppDir"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
cp -r dist-installers/dist/Iterador "$APPDIR/usr/bin/"
cp UI/assets/icon.png "$APPDIR/iterador.png"
cp scripts/packaging/linux/iterador.desktop "$APPDIR/iterador.desktop"
cat > "$APPDIR/AppRun" <<'EOF'
#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"
exec "$HERE/usr/bin/Iterador/Iterador" "$@"
EOF
chmod +x "$APPDIR/AppRun"

mkdir -p dist-installers
OUTPUT="dist-installers/Iterador-${VERSION}-x86_64.AppImage"
rm -f "$OUTPUT"
# --appimage-extract-and-run: não depende de FUSE estar disponível na máquina que builda.
ARCH=x86_64 "$APPIMAGETOOL" --appimage-extract-and-run "$APPDIR" "$OUTPUT"

echo "Instalador gerado: $OUTPUT"
