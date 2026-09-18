# 0041 — Perfil de cor "Roze Quartz"

Status: Aceito

## Contexto

Usuário pediu um tema pronto mais feminino, chamado "Roze Quartz" (inspirado na Rose Quartz das
Crystal Gems — rosa quartzo/rose gold em vez do laranja/roxo do visual padrão).

## Decisão: perfil `mode: "detailed"`, não `"simple"`

O sistema de perfis (ADR-0020/0025) tem dois modos: `"simple"` (4 campos —
`static_text`/`primary`/`secondary`/`tertiary` — o que a UI de "Novo perfil" cria) e
`"detailed"` (todos os ~30 papéis, hoje só usado por `Prizmo_V1`). Um perfil `"simple"` só troca
fundo/painel/texto/borda — os papéis "fixos" (`BRICK_EMBER`/despesa, `INDIGO`/receita,
`SUNFLOWER_GOLD`/destaque, cores de valor monetário, botão de tema) continuam laranja/roxo/
vermelho/verde de sempre, porque `theme.apply_profile()` só troca esses papéis quando o perfil é
`"detailed"` (modo `"simple"` sempre mescla com `_fixed_roles()` por cima). Pra "Roze Quartz"
parecer de verdade outro tema (não só um fundo diferente), precisava ser `"detailed"`, com
valores próprios pra cada papel — inclusive despesa/receita/destaque/valores monetários.

## Decisão: paleta rosa quartzo + rose gold, com sálvia como par complementar

Não deriva de `theme._fixed_roles()`/`snapshot_default_palette()` — escrito à mão em
`color_profiles._seed_roze_quartz_profile()`, mesma pasta que guarda a definição de
`Prizmo_V1` (`_seed_detailed_profile()`), sem precisar importar `theme.py` (só replica o
formato de chaves esperado, sem depender de nenhuma função de lá):
- **Despesa** (`BRICK_EMBER`/`ACCENT_EXPENSE`/`VALUE_EXPENSE`): rosa quartzo (`#D46A85`) e uma
  variante rosa-vermelha (`#E85D75`) pro valor monetário — vermelho suavizado, não vermelho puro.
- **Receita** (`INDIGO`/`ACCENT_INCOME`): ameixa/malva (`#8B5D7B`) — mantém a família "roxa" da
  paleta original (diferenciar visualmente de despesa), só mais suave.
- **`VALUE_INCOME`**: verde-sálvia (`#A8D5BA`) em vez do verde-claro original — sálvia é o par
  complementar clássico do rosa em paletas florais, mantém a leitura "positivo" (verde) sem
  destoar do resto.
- **Destaque/`SUNFLOWER_GOLD`**: rose gold (`#B76E79`) — metal associado ao tema, usado também
  no botão de tema (modo escuro) e borda do card "Fim do mês".
- **Fundo/superfície**: rosa muito claro quase branco no modo claro (`#FAF0F2`), preto-ameixa
  (não neutro) no escuro (`#2B1B22`) — mesmo princípio do `light_panel_blue` original (um tom
  sutil puxado pra cor do tema, não um cinza neutro).
- `DEEP_SAFFRON` (status "a pagar") virou pêssego suave (`#E8A87C`) — combina com o resto sem
  ficar destoante como um laranja puro ficaria.

## Decisão: sempre presente, adicionado a arquivos já existentes

`Prizmo_V1` só é semeado se `color_profiles.json` não existir ainda (`_load()`, primeira
execução). Isso não bastava pra "Roze Quartz" — quem já tem um `color_profiles.json` de antes
(como o usuário, neste caso) nunca ganharia o perfil novo sozinho. `_load()` agora, depois de
garantir que o arquivo tem pelo menos `Prizmo_V1`, checa separadamente se `"Roze Quartz"` existe
em `data["profiles"]` e adiciona (+ salva) se não — idempotente, roda em todo carregamento mas só
escreve no disco na primeira vez que o perfil realmente falta.

O mosaico triangular "Iterador" da Sidebar (`widgets/triangle_heading.py`, `ICON_ORANGE_CLUSTER`)
continua laranja em qualquer perfil, incl. Roze Quartz — cor amostrada do ícone do app de
verdade, não faz parte do sistema de perfis (mesmo comportamento que já tinha pro `Prizmo_V1` e
qualquer perfil `"simple"` — não é uma limitação nova desta ADR).

## Consequências

- Editável só por "Renomear"/"Remover" na UI (mesma limitação de `Prizmo_V1` — perfis
  `"detailed"` não têm formulário de edição campo-a-campo, só os `"simple"`).
- Testado (Xvfb, `$HOME` isolado com um `color_profiles.json` PRÉ-EXISTENTE sem o perfil, pra
  confirmar que ele é adicionado de verdade, não só funciona em arquivo novo): perfil aparece no
  seletor, aplica corretamente nos modos claro e escuro, cores de receita/despesa/destaque
  seguem a paleta rosa em vez de laranja/roxo padrão.
