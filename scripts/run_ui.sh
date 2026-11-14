#!/usr/bin/env bash
# Roda a UI CustomTkinter usando o venv isolado. Ver Guide/usage.md.
# Este script ignora o script activate do venv (que pode ter caminho de outra maquina)
# e define o PATH corretamente para o venv local.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

# Garante que usaremos o Python do venv local, não o do sistema
VENUA_BIN="$PWD/.venv/bin"
if [ -x "$VENUA_BIN/python3" ]; then
  export PATH="$VENUA_BIN:$PATH"
else
  echo "Erro: nao encontrei .venv/bin/python3 em $PWD"
  exit 1
fi

cd UI
python3 main.py
