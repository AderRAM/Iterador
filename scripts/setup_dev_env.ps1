# Cria o virtualenv e instala as dependencias Python (customtkinter, pybind11).
# Ver Guide/usage.md.
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Get-Command cmake -ErrorAction SilentlyContinue)) {
    Write-Warning "cmake nao encontrado no PATH. Instale antes de rodar build_backend.ps1:"
    Write-Warning "  winget install Kitware.CMake"
}

python -m venv .venv
& .\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r UI\requirements.txt pybind11

Write-Host "Ambiente pronto. Ative com: .\.venv\Scripts\Activate.ps1"
