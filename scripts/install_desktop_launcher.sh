#!/usr/bin/env bash
# Instala o ícone e o atalho do Iterador no menu de aplicativos do usuário (KDE/freedesktop),
# categoria Utilitários. Ver Guide/usage.md > Ícone no menu do KDE.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
PROJECT_ROOT="$(pwd)"

ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
APPS_DIR="$HOME/.local/share/applications"
mkdir -p "$ICON_DIR" "$APPS_DIR"

cp "$PROJECT_ROOT/UI/assets/icon.svg" "$ICON_DIR/iterador.svg"

# Icon= aponta pro caminho absoluto do PNG, não pro nome "iterador" resolvido via tema de
# ícones — em algum momento essa resolução por nome ficou caindo num fallback ("irix") sozinha
# neste ambiente (causa não identificada). Caminho absoluto é permitido pela spec freedesktop e
# não depende de nenhuma resolução/cache de tema.
cat > "$APPS_DIR/iterador.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Iterador
Comment=Gerenciador de finanças pessoais
Exec=$PROJECT_ROOT/scripts/run_ui.sh
Icon=$PROJECT_ROOT/UI/assets/icon.png
Terminal=false
Categories=Utility;Office;Finance;
EOF
chmod +x "$APPS_DIR/iterador.desktop"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$APPS_DIR"
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
fi
if command -v kbuildsycoca6 >/dev/null 2>&1; then
  kbuildsycoca6 --noincremental 2>/dev/null || true
elif command -v kbuildsycoca5 >/dev/null 2>&1; then
  kbuildsycoca5 --noincremental 2>/dev/null || true
fi

echo "Atalho instalado: $APPS_DIR/iterador.desktop"
echo "Icone instalado: $ICON_DIR/iterador.svg"
echo "Se nao aparecer no menu imediatamente, pode ser preciso relogar ou reiniciar o Plasma."
