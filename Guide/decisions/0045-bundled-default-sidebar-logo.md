# 0045 — Imagem padrão da Sidebar embutida no instalador ("Atlas")

Status: Aceito

## Contexto

Até aqui, a Sidebar sem imagem customizada do usuário (ver ADR-0037/0040) mostrava só o mosaico
"Iterador" (`TriangleHeading`). Usuário pediu uma imagem padrão pra já aparecer logo depois da
instalação, sem precisar configurar nada em Configurações — carregada de dentro do próprio
pacote do app (`UI/assets/`, já embutido no `.AppImage`/`Setup.exe`, ver ADR-0035), não de
`~/.iterador/` (aquilo é dado do usuário, ver `sidebar_image.py`).

## Decisão: nome fixo "Atlas", extensão livre

`sidebar_image._find_default_logo_source()` procura em `UI/assets/` por um arquivo cujo nome
(sem extensão, case-insensitive) seja `atlas` — `Atlas.png`, `Atlas.jpg`, `Atlas.webp`, etc.,
todos funcionam, sem precisar mudar código pra trocar o formato do arquivo depois. Ausência do
arquivo é um estado válido (sem imagem padrão) — cai de volta no mosaico, mesmo comportamento de
antes.

## Decisão: emoldurada a cada exibição, nunca gravada em disco

A imagem custom do usuário é processada uma vez no envio e salva como PNG em
`~/.iterador/sidebar_logo.png` (ver `sidebar_image.set_custom_logo`). A imagem padrão **não pode
seguir o mesmo caminho** — `UI/assets/` é o pacote do app (pode estar em `/opt/...` ou dentro do
AppImage, somente leitura em uso normal), e é errado tratar um asset do app como se fosse dado do
usuário. Em vez disso, `_frame_logo()` (extraída de `set_custom_logo`, agora compartilhada) roda
em memória a cada vez que a Sidebar é construída, sobre o arquivo aberto direto de `assets/` —
custo desprezível (arquivo pequeno, Sidebar só reconstrói em troca de perfil/imagem/tema, não a
cada frame).

## Decisão: prioridade — custom do usuário > padrão embutida > mosaico

`sidebar_image.get_display_image()` centraliza essa prioridade (usada por `sidebar.py`);
`get_logo_path()` continua existindo só pra "tem imagem custom do usuário?" (usado por
`settings_view.py` pra habilitar o botão "Remover imagem" e pro texto de status — precisa saber
se existe *esse* arquivo especificamente, não se tem *alguma* imagem aparecendo). `remove_custom_logo()`
não muda: apaga só o custom, cai de volta na padrão embutida se houver uma (não pula direto pro
mosaico) — comportamento esperado, "remover" desfaz a personalização do usuário, não a imagem que
já vinha com o app.

## Consequências

- `sidebar_image.py`: `_frame_logo()` extraída (usada por `set_custom_logo` e
  `get_display_image()`), `get_display_image()` e `has_bundled_default()` novas.
- `sidebar.py` passa a chamar `get_display_image()` em vez de `get_logo_path()` +
  `Image.open()` direto.
- `settings_view.py`: texto de status em Configurações passa a distinguir 3 estados (custom do
  usuário / padrão embutida / só mosaico), não só 2.
- Arquivo de imagem em si (`UI/assets/Atlas.<ext>`) não é gerado por código — precisa ser
  colocado manualmente em `UI/assets/` (mesmo processo de `icon.png`/`search.png`, ver
  `file-map.md`).
