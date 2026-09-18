# 0043 — Investimento/Passiva: de roxo (Indigo) pra rosa

Status: Aceito

## Contexto

Usuário relatou baixa legibilidade da cor da categoria "Passiva" no tema claro, pediu pra trocar
pra rosa "mesmo com investimento" — ou seja, o mesmo problema/troca vale pra "Investimento", já
que as duas sempre compartilharam a mesma cor (`palette["INDIGO"]`, ver ADR-0012: são as duas
categorias ligadas a um investimento).

## Decisão: nova cor dedicada, não reaproveitar `INDIGO`

`INDIGO` continua existindo e com o mesmo valor — é usado em bem mais lugares que só essas 2
categorias (`ACCENT_INCOME`, botão "Receita", etc., ver `theme._fixed_roles()`/perfis
`"detailed"`); mudar `INDIGO` em si mudaria a cor de botões em todo o app, não só das categorias.
Nova constante `_CATEGORY_INVESTMENT_ROSE = "#C2185B"` (+ variante clara pro texto pequeno da
lista no modo escuro, `_CATEGORY_INVESTMENT_ROSE_DARK_TEXT = "#F48FB1"`, mesmo princípio já usado
antes com o roxo) em `theme.py`, usada só na montagem de `CATEGORY_COLORS`/
`CATEGORY_LABEL_COLORS` dentro de `apply_profile()` — sempre a mesma cor rosa em qualquer perfil
de cor (é um rótulo de dado, não uma cor de interface, mesmo princípio de `CATEGORY_COLORS` já
documentado).

Escolhido mais escuro/saturado que os tons pastel de `_AUTO_CATEGORY_PALETTE` (categorias
personalizadas sem cor própria, ver ADR-0028) de propósito — os últimos 3 tons dali já ocupam a
faixa rosa/magenta; um rosa no mesmo brilho faria "Investimento"/"Passiva" parecerem uma
categoria personalizada qualquer.

## Consequências

- Combina com o contorno preto da coluna Categoria (ver ADR-0042, implementado antes desta) —
  os dois resolvem legibilidade de ângulos diferentes (cor de fundo/traço vs. contorno), ambos
  pedidos pelo usuário.
- Testado (Xvfb, tema claro, perfil padrão Prizmo_V1): "Investimento"/"Passiva" aparecem em rosa
  com contraste bom contra fundo claro, tanto no texto da lista quanto na fatia do gráfico de
  consumo.
