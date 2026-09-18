# Ativa o venv e roda a UI CustomTkinter. Ver Guide/usage.md.
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (Test-Path .venv\Scripts\Activate.ps1) {
    & .\.venv\Scripts\Activate.ps1
}

Set-Location UI
python main.py
