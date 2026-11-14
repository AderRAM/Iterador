# Configura e builda Backend/ com CMake. Resultado vai para UI/_build/.
# Ver Guide/usage.md.
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (Test-Path .venv\Scripts\Activate.ps1) {
    & .\.venv\Scripts\Activate.ps1
}

cmake -S Backend -B Backend\build -G Ninja
cmake --build Backend\build --config Release

Write-Host "Build concluido. Binario esperado em UI\_build\iterador_core*.pyd"
