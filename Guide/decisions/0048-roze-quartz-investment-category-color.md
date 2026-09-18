# 0048 — Roze Quartz: cor de Investimento/Passiva deixa de ser rosa

Status: Aceito

## Contexto

Usuário relatou que, no perfil "Roze Quartz", a cor de "Investimento"/"Passiva" (`#C2185B`) fica
muito parecida com a de "Essencial" (`palette["VALUE_EXPENSE"]` desse perfil, `#E85D75`) — as
duas caem na mesma faixa rosa/vermelho-rosado do tema, difíceis de distinguir à primeira vista.
Pediu uma cor mais visível, ainda agradável aos olhos e compatível com o resto da paleta.

A ADR-0047 já tinha identificado esse mesmo tom como "não lê como roxo" o suficiente pro
`Prizmo_V1` (trocado lá pra `#7C3AED`), mas manteve o rosa original no Roze Quartz de propósito
("sem mudança visual pra esse perfil") — este é o follow-up que a 0047 deixou em aberto.

## Decisão: ametista/lilás suave, não o roxo vívido do `Prizmo_V1`

Nova cor pro campo `INVESTMENT_CATEGORY_COLOR`/`INVESTMENT_CATEGORY_LABEL_LIGHT_TEXT` do Roze
Quartz: `#9B43B1` (ametista), com `#DAB5E3` (lilás pastel) pro texto pequeno no modo escuro —
mesmo princípio claro/escuro já usado em todo o resto da paleta. Roxo de verdade (matiz ~288°),
não reaproveita o roxo saturado do `Prizmo_V1` (`#7C3AED`, matiz ~258°, mais frio/vívido) — esse
destoaria do resto do perfil, que é todo em tons pasteis quentes (rosa quartzo, pêssego,
sálvia). `#9B43B1` fica numa saturação/luminosidade parecida com `BRICK_EMBER`/`SUNFLOWER_GOLD`
do mesmo perfil, só numa faixa de matiz separada (~288°) da faixa rosa/vermelho-rosado que
`BRICK_EMBER`/`VALUE_EXPENSE`/`SUNFLOWER_GOLD`/`ELECTRIC_BLUE` já ocupam (~322-352°) — dá pra
distinguir "Investimento"/"Passiva" de "Essencial" só pela cor, sem depender do contorno preto
(que essas duas categorias não têm, ver ADR-0047 Decisão 2).

Mantém o mesmo princípio simbólico do `Prizmo_V1`: roxo = investimento em qualquer perfil, só
o tom muda pra combinar com a paleta de cada um.

## Migração de perfis já salvos

Roze Quartz é um perfil `"detailed"`, não editável pela UI (só perfil `"simple"` é — ver
docstring de `color_profiles.py`), então qualquer `~/.iterador/color_profiles.json` que já tenha
esse perfil só pode ter o valor antigo (`#C2185B`), nunca uma customização do usuário. Seguro
sobrescrever sem pedir confirmação. `color_profiles._migrate_roze_quartz_investment_color()`
corrige isso na próxima leitura do arquivo (mesmo padrão de `_backfill_investment_category_fields`
da ADR-0047, mas comparando o valor exato em vez de só "campo existe", pra não reaplicar depois
que já rodou uma vez).

## Consequências

- Perfil `Prizmo_V1` não muda — continua com o roxo da ADR-0047, campo por perfil desde aquela
  ADR garante isolamento entre os dois.
- Perfil "simple" novo (criado pelo usuário) continua caindo no rosa antigo como fallback
  (`_FALLBACK_INVESTMENT_CATEGORY_COLOR` em `theme.py`, inalterado) — fora do escopo deste
  pedido, que foi especificamente sobre o Roze Quartz.
