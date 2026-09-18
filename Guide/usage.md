# Como rodar o projeto

## Pré-requisitos

- Python 3.10+
- `g++` (ou outro compilador C++20) e `ninja`
- **`cmake`** — em geral não vem instalado por padrão; instale antes de buildar:
  - Arch/Manjaro: `sudo pacman -S cmake`
  - Debian/Ubuntu: `sudo apt install cmake`
  - Windows: `winget install Kitware.CMake` (ou instalador em cmake.org)

`pybind11` é instalado via `pip` (está no `requirements.txt` de desenvolvimento, junto com
`customtkinter`) — não precisa instalar separadamente no sistema.

## Setup

```bash
./scripts/setup_dev_env.sh      # Linux/macOS
scripts\setup_dev_env.ps1       # Windows (PowerShell)
```

Cria um virtualenv em `.venv/` e instala `customtkinter` e `pybind11` (via pip).

## Build do backend

```bash
./scripts/build_backend.sh      # Linux/macOS
scripts\build_backend.ps1       # Windows (PowerShell)
```

Roda `cmake -S Backend -B Backend/build -G Ninja` e `cmake --build Backend/build`. O resultado
(`iterador_core*.so` no Linux, `iterador_core*.pyd` no Windows) é copiado automaticamente para
`UI/_build/` — é lá que `UI/iterador_ui/backend_bridge.py` procura o módulo.

Verificação manual (sem abrir a UI):

```bash
python3 -c "import sys; sys.path.insert(0, 'UI/_build'); import iterador_core; \
a = iterador_core.Application('/tmp/iterador-dev.db'); print(a.list_investments())"
```

Deve imprimir uma lista vazia (`[]`) sem lançar exceção.

## Testes do backend

```bash
ctest --test-dir Backend/build
```

## Rodar a UI

```bash
./scripts/run_ui.sh             # Linux/macOS
scripts\run_ui.ps1              # Windows (PowerShell)
```

Abre a janela CustomTkinter. Início/Investimentos/Orçamentos/Wiki/Configurações chamam o
backend de verdade — só a seção de sync/peers dentro de Configurações ainda é placeholder (ver
[`architecture.md`](architecture.md) → Roadmap).

## Ícone no menu do KDE

```bash
./scripts/install_desktop_launcher.sh
```

Instala `UI/assets/icon.svg` em `~/.local/share/icons/hicolor/scalable/apps/iterador.svg` e um
atalho em `~/.local/share/applications/iterador.desktop` (categoria Utilitários, aponta para
`scripts/run_ui.sh`). Roda `update-desktop-database`/`kbuildsycoca6`/`gtk-update-icon-cache`
automaticamente para o Plasma reconhecer o atalho sem precisar relogar. Se o projeto for movido
de lugar, rode o script de novo para regravar os caminhos.

O `Icon=` do `.desktop` aponta para o **caminho absoluto** de `UI/assets/icon.png` (não para o
nome "iterador" resolvido via tema de ícones) — em algum momento a resolução por nome ficou
caindo sozinha num ícone genérico ("irix"), causa não identificada; caminho absoluto evita
depender dessa resolução. A janela do próprio app também define seu ícone diretamente via
`iconphoto` (`UI/iterador_ui/app.py`), independente do `.desktop`.

## Gerar instalador

Pra distribuir o app pra um usuário comum (sem Python/CMake/compilador na máquina dele) — ver
[ADR-0035](decisions/0035-packaging-and-installers.md):

```bash
./scripts/build_installer_linux.sh      # Linux — gera dist-installers/Iterador-<versão>-x86_64.AppImage
scripts\build_installer_windows.ps1     # Windows — gera dist-installers\Iterador-Setup-<versão>.exe
                                         # (precisa de Inno Setup 6 instalado: https://jrsoftware.org/isdl.php)
```

Cada script builda o backend, congela a UI com PyInstaller (`scripts/packaging/iterador.spec`,
`--onedir`) e empacota (AppImage via `appimagetool`, baixado e cacheado em
`~/.cache/iterador-packaging/`; Setup.exe via `iscc`, do Inno Setup). O instalador Windows não é
assinado digitalmente — o Windows SmartScreen mostra um aviso de "app desconhecido" na primeira
execução ("Mais informações → Executar assim mesmo"), decisão aceita por ora (ver ADR-0035).
Versão lida de `UI/iterador_ui/version.py` (`APP_VERSION`).

## Troubleshooting

- **`ModuleNotFoundError: No module named 'iterador_core'`** — o backend não foi buildado, ou
  `UI/_build/` não tem o binário. Rode `./scripts/build_backend.sh` de novo e confira se
  `UI/_build/iterador_core*.so` (ou `.pyd`) existe.
- **CMake não encontra pybind11** — confirme que o venv de `setup_dev_env` está ativo antes de
  buildar (o `cmake/Dependencies.cmake` procura `pybind11` instalado via pip primeiro).
- **`cmake: command not found`** — ver seção Pré-requisitos acima.
- **Janela da UI não abre / erro de display no Linux** — confirme que há um servidor
  gráfico/Wayland/X11 disponível; CustomTkinter (Tkinter) precisa de um display.
- **`CMake Error: CMake can not determine linker language for target: sqlite3`** — falta `C` em
  `project(iterador_core LANGUAGES CXX C)` no `Backend/CMakeLists.txt` (o alvo `sqlite3` compila
  `sqlite3.c` puro). Já corrigido no repositório — se reaparecer, é sinal de que essa linha voltou
  a listar só `CXX` (ver [ADR-0031](decisions/0031-remove-investment.md)).
- **Erro de link `recompile com -fPIC` no alvo `sqlite3`** — falta
  `POSITION_INDEPENDENT_CODE ON` no alvo `sqlite3` em `Backend/cmake/Dependencies.cmake` (linkar
  uma lib estática não-PIC dentro do módulo compartilhado `iterador_core.so` falha). Já corrigido
  no repositório (ver ADR-0031).
- **Instabilidade ao arrastar lançamentos pra reordenar (ver ADR-0033)** — rode
  `ITERADOR_DEBUG_DRAG=1 ./scripts/run_ui.sh` pra gravar um log de diagnóstico em
  `/tmp/iterador_drag_debug.log` (posição do mouse, alvo calculado e posição real dos widgets a
  cada evento do arrasto, com timestamp em ms desde o clique) — foi assim que a causa raiz de uma
  instabilidade real (colapso de linha do grid ao tirar um widget dela) foi encontrada.
