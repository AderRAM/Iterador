# 0035 — Instaladores Windows (.exe) e Linux (AppImage)

Status: Aceito

## Contexto

Até aqui, rodar o Iterador exigia Python, CMake, um compilador C++20 e `ninja` instalados, e
saber usar terminal (`scripts/setup_dev_env.*` + `build_backend.*` + `run_ui.*`) — inviável pra
um usuário comum. Este ADR cobre só a parte "empacotamento/instaladores" do item de roadmap
"Empacotamento/instaladores, assinatura de código, auto-update, CI/CD"
(`Guide/architecture.md`); os outros três continuam pendentes e fora de escopo aqui — decisão
explícita do usuário:
- **Sem assinatura de código** por ora — aceita o aviso do SmartScreen no Windows na primeira
  execução; certificado tem custo/processo de verificação, decisão dele se/quando quiser.
- **Sem auto-update** — cada versão nova é um instalador novo, baixado manualmente.
- **Sem CI/CD** — os scripts abaixo são rodados manualmente pelo desenvolvedor quando quer gerar
  uma versão; automação via GitHub Actions fica pro item "CI/CD" do roadmap, depois que o
  processo manual estiver estável.
- **Linux: só AppImage** (não `.deb`/Flatpak) — mais simples, roda em qualquer distro.

## Decisão: congelar com PyInstaller (`--onedir`), não Nuitka

PyInstaller foi escolhido por ter hooks prontos pra Tkinter/Tcl-Tk/Pillow/CustomTkinter e por já
ter sido validado, nesta mesma sessão, rodando por dentro do pipeline cross-compile
Linux→Windows via Wine que o projeto já usa pra testar a versão Windows (ver
[ADR-0033](0033-transaction-manual-reorder.md) sobre esse pipeline; a sessão de teste real via
Wine que motivou isso não tem ADR próprio, foi conversação). Nuitka foi considerado e descartado
por ser mais arriscado de validar sob esse mesmo pipeline.

`--onedir` (pasta com o executável + libs) em vez de `--onefile` (um único blob compactado): o
onefile precisa se autoextrair pra um diretório temporário a cada execução (inicia mais lento) e
é bem mais sujeito a falso-positivo de antivírus no Windows por causa de heurísticas contra
executáveis compactados/empacotados — onedir evita os dois problemas, ao custo de a pasta final
ter mais arquivos visíveis (não é problema pra quem só vai clicar num atalho gerado pelo próprio
instalador).

## Decisão: sem mudar código da aplicação — replicar a estrutura relativa de `UI/` no bundle

Todo caminho de asset em `UI/iterador_ui/` é resolvido via `Path(__file__).resolve().parent... /
"assets"` ou `.../"​_build"` (`app.py`, `dashboard_view.py`, `backend_bridge.py`) — relativo à
própria árvore de `UI/`, nunca hardcoded. Duas armadilhas reais do PyInstaller descobertas
testando (não assumidas):

- **Módulos zipados perdem `__file__` real.** Por padrão, pacotes Python puros vão pra dentro de
  um `PYZ` comprimido — `__file__` de um módulo lá dentro aponta pra dentro do arquivo
  comprimido, não pra um diretório de verdade, e as contas de `Path(__file__).resolve().parent /
  "assets"` quebrariam. Corrigido com `module_collection_mode={"iterador_ui": "py"}`
  (`scripts/packaging/iterador.spec`) — força o pacote inteiro a ficar como `.py` soltos em
  `_internal/iterador_ui/`, no mesmo nível relativo de `_internal/assets/` e `_internal/_build/`
  (mapeados via `datas`/`binaries` no mesmo spec) que tem em `UI/` de verdade.
- **`PIL.ImageTk` falha sozinho.** O hook padrão do PyInstaller pra Pillow não inclui
  `PIL._tkinter_finder` — sem isso, todo ícone (`CTkImage`) quebra com `ModuleNotFoundError` só
  em tempo de execução, não na hora de buildar. Corrigido com um `hiddenimports` explícito no
  spec.

Ambas confirmadas rodando o bundle congelado de verdade (não só assumidas) — screenshot com
mosaico/ícones certos, CRUD funcionando, num `$HOME` isolado.

## Decisão: backend estático no Windows (mingw-w64)

`iterador_core.pyd` (compilado com mingw-w64, ver sessão de teste via Wine) dependia de 3 DLLs
de runtime do GCC (`libgcc_s_seh-1.dll`, `libstdc++-6.dll`, `libwinpthread-1.dll`) — confirmado
com `objdump -p | grep "DLL Name"`. Isso funcionava sem problema numa máquina de desenvolvimento
(o PATH já tem o mingw), mas um usuário comum instalando só o Setup.exe não teria essas DLLs em
lugar nenhum. `Backend/CMakeLists.txt` ganhou um bloco `if(MINGW)` com `target_link_options(...
-static-libgcc -static-libstdc++ -static -lwinpthread)` — confirmado (mesmo `objdump`) que o
`.pyd` final não depende mais de nenhuma DLL do compilador, só de `python3XX.dll` (fornecida pelo
próprio bundle do PyInstaller) e das `api-ms-win-crt-*.dll`/`KERNEL32.dll` que já vêm com
qualquer Windows 10+ (mesma dependência que o próprio Python já tem).

## Decisão: Inno Setup (Windows) / AppImage feito à mão com `appimagetool` (Linux)

**Windows**: Inno Setup é o padrão de facto pra instalador de app pequeno/indie nesse formato —
um `.iss` simples (`scripts/packaging/windows/iterador.iss`), compilável via `iscc` (inclusive
sob Wine, mesmo pipeline já validado). Gera Setup.exe com atalho no Menu Iniciar, ícone opcional
na área de trabalho, e desinstalador — sem precisar de mais nada instalado na máquina de destino.

**Linux**: `linuxdeploy` foi tentado primeiro mas descartado — ele existe pra resolver
dependências de bibliotecas dinâmicas de um executável simples, e o PyInstaller já resolveu isso
tudo sozinho; usar os dois juntos seria complexidade redundante. Em vez disso, o script monta a
`AppDir` à mão (copiando o onedir do PyInstaller pra dentro, mais um `AppRun`/`.desktop`/ícone —
mesmo texto de `.desktop` já usado por `scripts/install_desktop_launcher.sh`) e chama só
`appimagetool` pra empacotar. Mais simples e com menos partes móveis pra debugar.

Ambas as ferramentas (`appimagetool`, Inno Setup) são baixadas/cacheadas pelos próprios scripts
de build (`scripts/build_installer_linux.sh` baixa `appimagetool` uma vez pra
`~/.cache/iterador-packaging/`; `scripts/build_installer_windows.ps1` espera Inno Setup já
instalado, com aviso claro se não achar).

## Verificação

Testado de ponta a ponta nesta sessão (nunca tocando `~/.iterador/iterador.db` real — sempre
`$HOME`/db isolados, ver regra do `CLAUDE.md`):
- **Backend estático**: rebuild Windows via mingw-w64, `objdump` confirmando ausência das 3 DLLs.
- **Linux**: `scripts/build_installer_linux.sh` do zero → `Iterador-1.0-x86_64.AppImage` →
  rodado contra um `$HOME` fake, tela renderizada certa (mosaico, ícones), formulário de
  lançamento abrindo.
- **Windows**: mesmo pipeline via Wine já usado antes — PyInstaller com o Python real instalado
  no prefixo Wine, `iscc` gerando `Iterador-Setup-1.0.exe`, instalado de verdade
  (`/VERYSILENT`) num prefixo Wine, executável instalado aberto e renderizando a UI completa.

## Consequências

- `dist-installers/` (saída) e `build/`/`build-win/` (diretórios de trabalho do PyInstaller) são
  novas entradas no `.gitignore` — nunca versionados.
- Gerar um instalador novo é responsabilidade manual do desenvolvedor por ora (rodar o script
  correspondente); não há automação de release.
- `scripts/packaging/windows/icon.ico` é gerado uma vez a partir de `UI/assets/icon.png`
  (Pillow) e versionado — não é regenerado a cada build.
