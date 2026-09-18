# 0030 — Cor editável por categoria + hover interativo no comparativo mensal

Status: Aceito

## Contexto

Depois do comparativo mensal por categoria (ADR-0029), o usuário pediu 4 refinamentos:

1. A cor da linha devia combinar com a cor da categoria.
2. Na criação de categoria (Configurações), poder definir/editar a cor dela — com uma cor
   aleatória pré-selecionada por padrão.
3. Passar o mouse sobre uma posição da linha no comparativo mensal devia mostrar uma informação
   breve daquele ponto (categoria, mês, valor).
4. A linha sob o mouse devia mudar de tonalidade (destaque sutil).

O pedido 1 já era verdade tecnicamente (`LineChart.update_series()`/`ConsumptionChart` sempre
usaram `theme.category_color()`, a mesma função) — só que uma categoria personalizada tinha sua
cor **calculada** por hash do nome (ADR-0028), nunca escolhida/guardada. Resolver o pedido 2
(guardar uma cor de verdade) resolveu o 1 de graça, sem mexer em nenhum gráfico.

## Decisão

- **`custom_categories.py`** — cada categoria ganha um campo `"color"`. `add_custom_category()`
  passa a exigir `color` (quem decide o padrão aleatório é `settings_view.py`, não este módulo —
  mantém `custom_categories.py` sem depender de `theme.py`). Novo
  `update_custom_category_color(name, color)`, só troca a cor (nome/tipo/comportamento intactos
  — mudar esses depois de já existirem lançamentos complicaria a lógica de Despesa/Receita sem
  necessidade; cor é só rótulo visual).
- **`theme.category_color()`** — antes de cair no hash determinístico, procura a cor guardada em
  `custom_categories.list_custom_categories()`. Só as 5 fixas continuam com cor fixa de verdade;
  qualquer personalizada usa a cor escolhida pelo usuário.
- **`settings_view.py`** (seção "Categorias") — form de criar ganha um botão-amostra pré-marcado
  com `random.choice(theme._AUTO_CATEGORY_PALETTE)`, reaberto pra um novo aleatório a cada
  categoria criada; clicar abre `ColorPickerDialog` (o mesmo diálogo modernizado da ADR-0029,
  reaproveitado) pra trocar antes de criar. Cada categoria já criada ganha um botão-amostra na
  lista, clicável pra editar a cor a qualquer momento.
- **`line_chart.py`** — hover só em modo `update_series()` (`self._hover_state`, `None` em modo
  `update_data()`/CDI, que não ganhou hover). Guarda por categoria: id da linha no canvas, cor
  normal, pontos reais `(x, y, valor)` em coordenadas de canvas (pro conteúdo do tooltip — mês/
  valor de verdade), e os **pontos da curva já suavizada** (`dense_points`, os mesmos pixels
  usados em `create_line`, ~10px de espaçamento). `<Motion>` compara `event.y` contra
  `dense_points`, não contra o dado bruto de cada mês — a 1ª versão comparava só com os ~6 pontos
  de dado por categoria (bem espaçados no eixo X), então longe de um ponto de dado exato o
  "contato" da linha com o mouse ficava impreciso (relato do usuário, com screenshot: cursor bem
  longe da linha realçada). Como todas as categorias amostram a curva nos mesmos instantes (só o
  valor muda, não a posição X), um único índice de amostra (calculado uma vez a partir de
  `event.x`) serve pra testar todas as categorias, sem busca por categoria. Categoria mais perto
  dentro de `_HOVER_RADIUS_PX = 14` fica em hover; fora do raio, nenhuma. Só usa `itemconfig` pra
  recolorir a linha em hover (`theme.shade_color`, já existente desde o hover do botão Pago/A
  pagar) e desenha um tooltip (retângulo + texto, 2 itens rastreados à parte) ancorado no ponto
  da curva sob o cursor (não no dado bruto do mês mais próximo — sem isso o tooltip também
  parecia "grudado" longe do mouse ao passar entre dois meses) — sem reconstruir o gráfico
  inteiro a cada movimento do mouse. `<Leave>` desfaz tudo.

## Consequências

- Duas categorias personalizadas podem, por coincidência, ter a mesma cor se o usuário escolher
  igual pras duas (sem verificação de unicidade de cor) — aceitável, é só visual.
- Hover não existe no histórico do CDI (Wiki) — só no comparativo mensal do Início, que foi o
  único lugar pedido.
