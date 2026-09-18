; Script do Inno Setup — gera o Setup.exe do Iterador a partir do onedir já congelado pelo
; PyInstaller (scripts/packaging/iterador.spec). Ver Guide/usage.md > Gerar instalador e
; Guide/decisions/0035-packaging-and-installers.md.
;
; Rodar via scripts/build_installer_windows.ps1 (compila com `iscc /DMyAppVersion=<versão> ...`)
; — não abrir/compilar direto sem passar MyAppVersion, a não ser pra teste rápido (cai no valor
; padrão abaixo).

#define MyAppName "Iterador"
#ifndef MyAppVersion
#define MyAppVersion "0.0.0"
#endif
#define MyAppExeName "Iterador.exe"

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppName}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
; Caminhos relativos a este arquivo (scripts/packaging/windows/) — ..\..\.. é a raiz do repo.
OutputDir=..\..\..\dist-installers
OutputBaseFilename=Iterador-Setup-{#MyAppVersion}
SetupIconFile=icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar um ícone na área de trabalho"; GroupDescription: "Ícones adicionais:"

[Files]
Source: "..\..\..\dist-installers\dist\Iterador\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Executar o {#MyAppName}"; Flags: nowait postinstall skipifsilent
