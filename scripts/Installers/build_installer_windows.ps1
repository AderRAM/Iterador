# Gera o instalador Windows (Setup.exe) do Iterador — não precisa de Python/CMake/compilador
# na máquina de quem vai instalar. Ver Guide/usage.md > Gerar instalador e
# Guide/decisions/0035-packaging-and-installers.md.
#
# Pré-requisito além dos já listados em Guide/usage.md: Inno Setup 6
# (https://jrsoftware.org/isdl.php) instalado no caminho padrão, ou passe -IsccPath.
param(
    [string]$IsccPath = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (Test-Path .venv\Scripts\Activate.ps1) {
    & .\.venv\Scripts\Activate.ps1
}

.\scripts\build_backend.ps1

pip install --quiet pyinstaller

$version = python -c "import sys; sys.path.insert(0, 'UI'); from iterador_ui.version import APP_VERSION; print(APP_VERSION)"

Remove-Item -Recurse -Force build -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force dist-installers\dist -ErrorAction SilentlyContinue
pyinstaller --noconfirm --distpath dist-installers\dist --workpath build scripts\packaging\iterador.spec

if (-not (Test-Path $IsccPath)) {
    Write-Warning "Inno Setup (ISCC.exe) nao encontrado em $IsccPath."
    Write-Warning "Instale em https://jrsoftware.org/isdl.php ou rode com -IsccPath <caminho>."
    exit 1
}

New-Item -ItemType Directory -Force -Path dist-installers | Out-Null
& $IsccPath "/DMyAppVersion=$version" scripts\packaging\windows\iterador.iss

Write-Host "Instalador gerado: dist-installers\Iterador-Setup-$version.exe"
