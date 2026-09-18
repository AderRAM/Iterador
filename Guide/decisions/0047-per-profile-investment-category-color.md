# 0047 — Cor de Investimento/Passiva por perfil + fundo/contorno da coluna Categoria

Status: Aceito

## Contexto

Aglomerado de 3 relatos do usuário, com screenshot da coluna Categoria da lista de lançamentos:

1. Uma caixa branca (modo escuro) ou preta (modo claro) aparecia atrás do texto de qualquer
   categoria, em qualquer perfil de cor.
2. O contorno preto das letras (ADR-0042) ficava grosso demais e ainda difícil de ler,
   especificamente em "Passiva"/"Investimento" — pediu pra simplesmente remover o contorno
   dessas duas.
3. A cor de "Investimento"/"Passiva" do perfil `Prizmo_V1` mudou de roxo pra rosa depois de uma
   mudança pensada pro perfil "Roze Quartz" — "isso é um problema". Ao perguntar se um roxo mais
   escuro/saturado (sem contorno) resolveria, o usuário esclareceu que o rosa da ADR-0043
   (`#C2185B`) nunca leu como roxo pra ele — não é questão de contraste, é a cor errada.

## Causa raiz 1: `OutlinedLabel` usava o papel de fundo errado E nunca soube de troca de tema

`OutlinedLabel.set_text()` fixava `self.configure(bg=theme.BG_APP)` — mas a lista de
lançamentos não fica sobre `BG_APP` (fundo do app inteiro), fica sobre `content_panel`, que usa
`theme.BG_PANEL_BLUE` (`DashboardView`, ver `architecture.md`). Isso por si só já seria uma cor
ligeiramente errada, mas o bug visível (uma caixa branca/preta bem óbvia, não uma cor "quase
igual") tinha uma causa maior: `OutlinedLabel` é um `tk.Canvas` **puro** (Tkinter, não
CustomTkinter) — nunca se inscreveu no `CTkAppearanceModeBaseClass`/`AppearanceModeTracker` do
CustomTkinter, então nunca era avisado quando `ctk.set_appearance_mode()` mudava. Fundo E cor do
texto ficavam "congelados" no tema de quando a linha foi desenhada por último; trocar de tema
sem re-renderizar a lista (nada em `IteradorApp._on_toggle_theme` força isso) deixava o valor do
modo ANTERIOR pintado por cima do fundo do modo ATUAL — o modo claro de `BG_APP` é bem claro
("#F5F1EA"/branco-ish) e o escuro é bem escuro (`CARBON_BLACK`), daí a caixa branca no escuro (se
o toggle foi claro→escuro) ou preta no claro (se foi escuro→claro).

Confirmado reproduzindo em Xvfb: instrumentado `OutlinedLabel` pra imprimir seu próprio `bg` e
nº de itens desenhados no Canvas antes/depois de `ctk.set_appearance_mode()` — sem o fix, `bg`
não mudava nada ao trocar de modo; com o fix (mixin `CTkAppearanceModeBaseClass` +
`_set_appearance_mode()` redesenhando), `bg` acompanha o modo atual imediatamente, sem precisar
de nenhum `refresh()` externo.

## Decisão 1: `OutlinedLabel` se inscreve no `AppearanceModeTracker`

`class OutlinedLabel(tk.Canvas, CTkAppearanceModeBaseClass)` — mesma técnica que toda classe
CustomTkinter usa por baixo. `_set_appearance_mode()` reconfigura o `bg` (papel atual, guardado
em `self._background_role` — normal é `theme.BG_PANEL_BLUE`, ou `theme.BG_SURFACE` durante o
"elevar" do arrasto, ver ADR-0033) e redesenha o texto com a cor certa pro modo novo. `destroy()`
chama `CTkAppearanceModeBaseClass.destroy()` (desinscreve do tracker) antes do `tk.Canvas.destroy()`
— relevante porque `IteradorApp.rebuild_ui()` destrói e recria a `DashboardView` inteira ao
trocar de perfil de cor (ADR-0025); sem isso, cada troca de perfil vazaria mais um callback morto
no tracker global.

## Decisão 2: sem contorno em Investimento/Passiva (`theme.CATEGORY_NO_OUTLINE`)

`OutlinedLabel._draw()` só desenha as 4 cópias de contorno preto se
`text not in theme.CATEGORY_NO_OUTLINE`. As outras categorias continuam com o contorno normal —
o pedido do usuário foi específico pra essas duas, cuja cor dedicada (ver Decisão 3) já resolve
contraste sozinha.

## Decisão 3: cor de Investimento/Passiva vira campo por perfil, não mais constante global

Causa raiz do bug 3: desde a ADR-0043, essa cor era uma constante global em `theme.py`
(`_CATEGORY_INVESTMENT_ROSE`), a MESMA pra qualquer perfil de cor — não fazia parte do dict de
nenhum perfil. Mudar essa constante (motivado por legibilidade no perfil `Roze Quartz`) mudava
**todo mundo**, inclusive `Prizmo_V1`, que nunca teve esse problema (o roxo original,
`palette["INDIGO"]`, já era assim antes da ADR-0043 — também global, só que outra cor).

Virou 3 campos por perfil — `INVESTMENT_CATEGORY_COLOR` (fatia do gráfico + texto no claro),
`INVESTMENT_CATEGORY_LABEL_LIGHT_TEXT`, `INVESTMENT_CATEGORY_LABEL_DARK_TEXT` (texto no escuro,
mesma ideia clara/escura de sempre) — cada perfil "detailed" guarda o próprio valor:

- **`Prizmo_V1`**: roxo/violeta novo, `#7C3AED` (+ `#C4B5FD` pro texto no escuro) — NÃO é o
  `INDIGO` de `_fixed_roles()` (que também pinta `ACCENT_INCOME`/botão de Receita; mudar ali
  mudaria botão em todo perfil). Escolhido especificamente pra ler como roxo de verdade (não
  cair na faixa magenta/rosa) e ter contraste suficiente pra dispensar o contorno (Decisão 2) —
  testado visualmente em Xvfb, claro e escuro, perfil Prizmo_V1: legível nos dois sem contorno.
- **`Roze Quartz`**: mantém exatamente o rosa que já estava em uso (`#C2185B`/`#F48FB1`) — sem
  mudança visual pra esse perfil.
- Perfil **"simple"** novo (criado pelo usuário): cai no mesmo rosa de `Roze Quartz` como
  default (`_expand_simple_profile`) — não ganhou campo próprio nos 4 editáveis, mesmo
  comportamento que todo perfil tinha antes desta ADR.

`theme.apply_profile()` lê esses 3 campos de `palette.get(..., fallback)` (nunca `palette[...]`
direto) — perfis "detailed" já persistidos em `~/.iterador/color_profiles.json` de antes desta
ADR não têm esses campos ainda. `color_profiles._backfill_investment_category_fields()` corrige
isso na próxima leitura (mesmo padrão do backfill que já existia pra garantir que `Roze Quartz`
existe como perfil, ver `_load()`): preenche `Prizmo_V1`/`Roze Quartz` já salvos com os valores
das próprias funções de seed (nunca duplica os hex), salva de volta no arquivo. Testado
isoladamente (arquivo de perfis num diretório temporário, nunca `~/.iterador/`): perfil
`Prizmo_V1` salvo ANTES desta ADR (sem os 3 campos) é corrigido pra roxo na primeira leitura e
persiste corrigido no arquivo.

## Consequências

- `OutlinedLabel.set_text(category_name)` — API mudou (antes recebia `(text, color)`; agora só
  o nome da categoria, resolve a cor sozinho via `theme.category_label_color()`, inclusive de
  novo a cada troca de tema). Único call site, `DashboardView._render_transaction_list()`,
  atualizado.
- Testado em Xvfb (screenshot real, claro e escuro, perfil `Prizmo_V1`): sem caixa branca/preta
  atrás de nenhuma categoria; "Investimento"/"Passiva" em roxo sem contorno, legível nos dois
  temas; outras categorias continuam com o contorno normal.
- Perfil `Roze Quartz` sem mudança visual (mesmo rosa de antes, agora isolado — editar/trocar
  `Prizmo_V1` não afeta mais `Roze Quartz` e vice-versa).
