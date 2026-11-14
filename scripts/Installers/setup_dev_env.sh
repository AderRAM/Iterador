#!/usr/bin/env bash
# Cria o virtualenv e instala as dependências Python (customtkinter, pybind11).
# Ver Guide/usage.md.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if ! command -v cmake >/dev/null 2>&1; then
  echo "AVISO: cmake nao encontrado no PATH. Instale antes de rodar build_backend.sh:" >&2
  echo "  Arch/Manjaro: sudo pacman -S cmake" >&2
  echo "  Debian/Ubuntu: sudo apt install cmake" >&2
fi

python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip
pip install -r UI/requirements.txt pybind11

echo "Ambiente pronto. Ative com: source .venv/bin/activate"
