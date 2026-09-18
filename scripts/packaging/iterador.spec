# Spec do PyInstaller — congela a UI (CustomTkinter) + o backend compilado num pacote
# "onedir" (pasta com o executável + libs, não um único blob). Ver
# Guide/decisions/0035-packaging-and-installers.md e Guide/usage.md > Gerar instalador.
#
# Rodar sempre via scripts/build_installer_linux.sh ou scripts/build_installer_windows.ps1.
# Caminhos abaixo são relativos a este arquivo (SPECPATH, injetado pelo PyInstaller), não ao
# diretório de trabalho de quem chama `pyinstaller` — assim funciona de qualquer cwd.

import os

from PyInstaller.utils.hooks import collect_data_files

_REPO_ROOT = os.path.normpath(os.path.join(SPECPATH, "..", ".."))
_UI_DIR = os.path.join(_REPO_ROOT, "UI")

datas = [(f"{_UI_DIR}/assets", "assets")]
datas += collect_data_files("customtkinter")

binaries = []
# iterador_core.pyd (Windows) ou .cpython-*.so (Linux) — só existe depois de
# scripts/build_backend.sh/.ps1 já ter rodado. Colocado em "_build" no bundle, no mesmo nível
# relativo de iterador_ui/ que tem em UI/ — é onde backend_bridge.py (via __file__) procura.
import glob
for _compiled in glob.glob(f"{_UI_DIR}/_build/iterador_core.*"):
    binaries.append((_compiled, "_build"))

if not binaries:
    raise SystemExit(
        "Nenhum iterador_core.* encontrado em UI/_build — rode "
        "scripts/build_backend.sh (ou .ps1) antes de gerar o instalador."
    )

a = Analysis(
    [os.path.join(_UI_DIR, "main.py")],
    pathex=[_UI_DIR],
    binaries=binaries,
    datas=datas,
    # PIL.ImageTk precisa disso pra achar o _tkinter certo em runtime; o hook padrão do
    # PyInstaller pra Pillow não inclui esse módulo (bug conhecido) — sem isso, todo ícone
    # (CTkImage) quebra com "ModuleNotFoundError: No module named 'PIL._tkinter_finder'".
    hiddenimports=["PIL._tkinter_finder"],
    # Mantém iterador_ui/ como arquivos .py soltos em vez de zipados dentro do PYZ — o código
    # calcula caminho de assets/backend via Path(__file__).resolve().parent... (ver
    # iterador_ui/app.py, dashboard_view.py, backend_bridge.py); zipado, __file__ apontaria pra
    # dentro do arquivo comprimido, não pra um diretório real, e essas contas quebrariam.
    module_collection_mode={"iterador_ui": "py"},
    noarchive=False,
)

pyz = PYZ(a.pure)

_ICON_ICO = os.path.join(SPECPATH, "windows", "icon.ico")

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Iterador",
    console=False,
    icon=_ICON_ICO if os.path.isfile(_ICON_ICO) else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="Iterador",
)
