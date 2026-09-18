#!/usr/bin/env bash
# Ativa o venv e roda a UI CustomTkinter. Ver Guide/usage.md.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [ -f .venv/bin/activate ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

cd UI
python3 main.py
