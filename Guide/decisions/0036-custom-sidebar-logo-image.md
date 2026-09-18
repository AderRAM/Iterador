# 0036 — Imagem customizada no lugar do logo "Iterador" da Sidebar

Status: Superseded by [ADR-0037](0037-custom-sidebar-logo-image-overlay.md) — a decisão de
"substituir o mosaico" abaixo estava errada (relato do usuário depois de testar: a marca
"Iterador" nunca deveria sumir). O resto deste documento (processamento da imagem, formato de
persistência, rename do callback) continua válido — só a composição visual mudou.

## Contexto

Usuário pediu, em Configurações, poder enviar uma imagem própria (PNG/JPEG/etc.) pra aparecer
no lugar do logo padrão da Sidebar — hoje sempre `TriangleHeading`
(`UI/iterador_ui/widgets/triangle_heading.py`), um `tk.Canvas` de 156×44px com mosaico
triangular laranja + texto "Iterador" (ver ADR-0025). Requisitos do usuário: tamanhos de imagem
variam, então precisa ajustar mantendo proporção; o espaço final deve ser maior que o retângulo
atual mas sem encostar na borda da Sidebar; a imagem final ganha borda preta.

## Decisão: substituir o mosaico, não sobrepor

"Aparecer em cima de Iterador caso selecionado" foi lido como "no lugar de", não "por cima de"
ao mesmo tempo — uma foto e o texto "Iterador" competindo pelo mesmo espaço de 156×90px ficaria
poluído. Sem imagem customizada configurada, o comportamento é idêntico a antes
(`TriangleHeading` continua existindo sem nenhuma mudança).

## Decisão: 156×90px, borda preta de 4px, processado uma vez no envio

Largura igual à do retângulo atual (156px — já comprovado que cabe no `padx=12` da Sidebar de
180px sem encostar na borda dela, ver `sidebar.py`), altura quase dobrada (44→90) — área mais
que dobra, satisfaz "maior" sem arriscar layout novo na largura. `PIL.ImageOps.contain` ajusta a
imagem enviada mantendo proporção pra caber dentro de 148×82 (156×90 menos 4px de borda de cada
lado); `ImageOps.pad` centraliza sobre fundo `theme.CARBON_BLACK` (letterbox preta se a
proporção não bater exatamente — combina com a borda, dá efeito de moldura); `ImageOps.expand`
adiciona a borda de 4px por fora, resultado final sempre 156×90px.

Processado **uma vez, no momento do envio** (`sidebar_image.set_custom_logo`), não a cada vez
que a Sidebar é construída — mais rápido (não reprocessa imagem grande toda hora que o usuário
troca de aba/perfil) e mais simples (o que fica salvo em disco já é exatamente o que vai ser
mostrado, sem lógica de fit espalhada pelo widget).

## Decisão: sempre salvar como PNG, um arquivo só, sem JSON de flag novo

`UI/iterador_ui/sidebar_image.py` (novo módulo, formato de `color_profiles.py`: funções +
`SidebarImageError(ValueError)` próprio) salva sempre em `~/.iterador/sidebar_logo.png` — Pillow
lê qualquer formato de entrada popular (png/jpg/jpeg/bmp/gif) e grava sempre PNG de saída,
elimina qualquer necessidade de rastrear extensão original. A **existência do arquivo já é o
estado**: existe = usar a imagem customizada, não existe = usar o mosaico padrão — não precisou
de nenhuma chave nova em `preferences.json` nem de um JSON próprio (diferente de
`color_profiles.json`, que precisa de estrutura porque tem vários perfis nomeados; aqui só existe
"tem" ou "não tem"). `preferences.py` foi propositalmente deixado de fora — ele hoje é só
`appearance_mode`, um valor só, sobrescreve o arquivo inteiro sem merge; não era o encaixe certo
pra um segundo campo não relacionado.

## Decisão: reaproveitar e renomear o callback de rebuild

Trocar/remover a imagem customizada tem exatamente o mesmo problema que trocar de perfil de cor
(ADR-0025): o widget da Sidebar já foi construído, CustomTkinter não o atualiza sozinho (só
troca de tema claro/escuro faz isso nativamente) — precisa `IteradorApp.rebuild_ui()` (destrói e
recria Sidebar + views). Esse mecanismo já chegava em `SettingsView` como `on_profile_applied`;
como agora serve dois motivos diferentes, foi renomeado pra `on_visuals_changed` em `app.py` e
`settings_view.py` (troca mecânica, sem mudar comportamento) — o nome antigo já estava errado
pro segundo uso.

## UI: novo card "Imagem da barra lateral" em Configurações

Mesmo padrão visual dos outros cards de `settings_view.py` (`BG_PANEL_BLUE`/`CARBON_BLACK`,
título + botões + status label). "Escolher imagem..." via `filedialog.askopenfilename`
(`filetypes=[("Imagens", "*.png *.jpg *.jpeg *.bmp *.gif")]`, mesmo padrão de
`_import_spreadsheet`/`_import_statement`); erros de arquivo inválido/corrompido
(`SidebarImageError`) aparecem na status label, mesmo padrão de erro que os outros cards já
usam — nunca derruba a UI. "Remover imagem" fica desabilitado quando não há imagem customizada
ativa (`_refresh_sidebar_image_status`).

## Consequências

- `sidebar.py` ganhou uma checagem condicional simples (`sidebar_image.get_logo_path()`) no
  lugar da construção incondicional de `TriangleHeading` — sem widget novo, só um
  `ctk.CTkLabel`/`CTkImage` exibindo o PNG já pronto.
- Testado (Xvfb, sem interação humana, `$HOME` sempre isolado — nunca
  `~/.iterador/iterador.db` real): 3 proporções de imagem diferentes (quadrada, bem larga, bem
  alta) sempre saindo 156×90 com letterbox/borda corretos; arquivo inválido/corrompido rejeitado
  com erro amigável sem corromper um logo válido já existente; troca ao vivo (Escolher/Remover)
  atualizando a Sidebar sem reiniciar o app, inclusive junto com troca de perfil de cor logo em
  seguida (mesmo `rebuild_ui()` cobrindo os dois).
