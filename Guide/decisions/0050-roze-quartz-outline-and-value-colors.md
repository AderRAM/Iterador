# 0050 — Roze Quartz: remove contorno da coluna Categoria, texto de Valor legível nos dois temas

Status: Aceito

## Contexto

Dois ajustes de legibilidade específicos do perfil "Roze Quartz":

1. O contorno preto da coluna Categoria (ADR-0042) em Essencial/Ativa/Lazer ficava difícil de
   ler contra o fundo pastel desse perfil, ao contrário do efeito pretendido — piorava em vez de
   ajudar. Investimento/Passiva já não tinham contorno desde a ADR-0047/0048.
2. Os números da coluna Valor/card "Total do mês" (`VALUE_INCOME`/`VALUE_EXPENSE`) usavam tons
   pastel claros demais pra esse perfil, difíceis de ler.

## Decisão 1: `CATEGORY_NO_OUTLINE` vira campo por perfil

Antes era uma constante global fixa (`{"Investimento", "Passiva"}`, ver ADR-0042/0047) — igual
em qualquer perfil de cor. Mesmo padrão já usado pra `INVESTMENT_CATEGORY_COLOR` (ADR-0047):
`theme.apply_profile()` lê `palette.get("CATEGORY_NO_OUTLINE", _FALLBACK_CATEGORY_NO_OUTLINE)` e
injeta como `set` no nível de módulo. `Prizmo_V1` mantém o conjunto de sempre
(`{"Investimento", "Passiva"}`); `Roze Quartz` desliga o contorno nas 5 categorias fixas
(`{"Essencial", "Lazer", "Investimento", "Ativa", "Passiva"}`). Perfil "simple"/qualquer
"detailed" sem o campo cai no fallback antigo.

`color_profiles._backfill_category_no_outline_field()` preenche o campo em qualquer
`color_profiles.json` já salvo que não o tenha — separado de `_backfill_investment_category_fields`
(ADR-0047) porque esse checa só `"INVESTMENT_CATEGORY_COLOR" in profile` como trigger, o que
pularia perfis que já passaram pela ADR-0047/0048 e nunca ganhariam o campo novo.

## Decisão 2: `VALUE_INCOME`/`VALUE_EXPENSE` do Roze Quartz, 20% mais escuros

`#A8D5BA` → `#86AA95` (verde-sálvia) e `#E85D75` → `#BA4A5E` (vermelho-rosado), cada canal RGB
multiplicado por 0,8. Só o perfil Roze Quartz — esses dois campos já são por-perfil desde sempre
(fazem parte do dict "detailed" completo), `Prizmo_V1` não é afetado.
`color_profiles._migrate_roze_quartz_value_colors()` corrige um `color_profiles.json` já salvo
com os 2 valores antigos exatos — Roze Quartz é "detailed", não editável pela UI, então qualquer
valor salvo só pode ter vindo do seed antigo, seguro sobrescrever.

## Decisão 3 (follow-up): `VALUE_INCOME_TEXT`/`VALUE_EXPENSE_TEXT` — par claro/escuro só pro texto

O "20% mais escuro" da Decisão 2 ainda não bastava como TEXTO contra o fundo claro deste perfil
(`#86AA95` sobre `#FAF0F2`: razão de contraste ~2,3:1, abaixo do mínimo de legibilidade — medido
com a fórmula de luminância relativa do WCAG). Mas `VALUE_INCOME`/`VALUE_EXPENSE` não podem virar
simplesmente mais escuros ou virar um par claro/escuro: eles também pintam o FUNDO do badge
"Pago"/"A pagar" (que tem texto preto fixo em cima — escurecer demais o fundo quebraria esse
contraste) e a fatia do gráfico de consumo (que é cor única nos dois temas de propósito, ver
ADR-0029/0043) — nenhum dos dois é um `CTkLabel`/`CTkFrame` que resolve tupla `(claro, escuro)`
sozinho (`Canvas` puro no gráfico; texto de badge fixo em preto).

Por isso dois campos NOVOS, só pro texto: `VALUE_INCOME_TEXT`/`VALUE_EXPENSE_TEXT` — tupla
`(claro, escuro)`, calculada em `theme.apply_profile()` a partir de `palette.get(campo, (flat,
flat))` (perfil sem campo próprio cai na cor única de sempre nos dois temas, sem mudança de
comportamento — mesmo padrão de `CATEGORY_NO_OUTLINE`/`INVESTMENT_CATEGORY_COLOR`). Só `Roze
Quartz` define um valor de verdade: `VALUE_INCOME_TEXT = ("#255638", "#A8D5BA")` — verde escuro
de verdade (mesmo matiz do sálvia, ~144°, saturação/luminosidade recalculadas por HSL) no claro,
contraste ~7,6:1; o sálvia pastel ORIGINAL de volta no escuro, que já tinha ótimo contraste lá
(~10:1) — não precisou de um tom novo. `VALUE_EXPENSE_TEXT` não ganhou override (o vermelho-
rosado já lia bem como texto; só o verde foi relatado como fraco).

Call sites que mostram NÚMERO/TEXTO passam a usar as variantes `_TEXT` (coluna Valor, "Fim do
mês", "Saldo atual", cards "Receitas/Despesas do mês") — o badge "Pago"/"A pagar" continua na
`VALUE_INCOME`/`VALUE_EXPENSE` flat (fundo do botão, não texto). `CATEGORY_LABEL_COLORS["Ativa"/
"Lazer"]` (nome da categoria na lista, mesma técnica já usada em Investimento/Passiva desde a
ADR-0047) também passa a usar `VALUE_INCOME_TEXT` — a cor de fundo/gráfico continua vindo de
`CATEGORY_COLORS` (inalterado).

`color_profiles._backfill_roze_quartz_value_income_text()` preenche o campo num
`color_profiles.json` já salvo do Roze Quartz que não o tenha ainda — só esse perfil precisa,
`Prizmo_V1`/"simple" não ganham o campo (caem no par calculado dinamicamente).

## Consequências

- `VALUE_INCOME`/`VALUE_EXPENSE` (flat) continuam pintando o fundo do badge "Pago"/"A pagar" e a
  fatia do gráfico de consumo — inalterados desde a Decisão 2. O texto da coluna Valor, dos
  cards do topo e do nome de categoria Ativa/Lazer usa as variantes `_TEXT` da Decisão 3.
- `Prizmo_V1`/perfil "simple" continuam idênticos a antes desta ADR em todos os 3 pontos — os 3
  campos novos (`CATEGORY_NO_OUTLINE`, `VALUE_INCOME_TEXT`, `VALUE_EXPENSE_TEXT`) só têm valor
  de verdade no Roze Quartz; em qualquer outro perfil, o fallback reproduz o comportamento
  anterior sem diferença visível.
- Testado (Xvfb, banco sintético isolado, config isolada — nunca `~/.iterador/`): perfil novo
  (sem `color_profiles.json`), perfil já salvo em formato pré-ADR-0048/0049/0050 (migração
  completa), texto verde escuro no claro/pastel no escuro renderizado de verdade nos dois modos,
  badge "Pago" com fundo inalterado, e app rodando de ponta a ponta com Roze Quartz ativo, sem
  erro.
