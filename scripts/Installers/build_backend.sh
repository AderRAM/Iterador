#!/usr/bin/env bash
# Configura e builda Backend/ com CMake+Ninja. Resultado vai para UI/_build/.
# Ver Guide/usage.md.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [ -f .venv/bin/activate ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

cmake -S Backend -B Backend/build -G Ninja
cmake --build Backend/build -j

echo "Build concluido. Binario esperado em UI/_build/iterador_core*.so"
