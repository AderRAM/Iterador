# 0029 — Comparativo mensal no Início + seletor de cor modernizado + categoria com quebra de linha + contraste em Perfis de cor

Status: Aceito

## Contexto

Quatro pedidos independentes, cada um com uma imagem de referência do usuário:

1. O espaço vazio ao lado do gráfico de pizza "Consumo do mês" devia ter um gráfico comparando
   os valores deste mês com os meses passados, com um resumo em números do que mudou (ex.
   "gastei mais com Lazer que mês passado"). Perguntado se era uma linha só (total) ou uma linha
   por categoria — usuário escolheu **uma linha por categoria**.
2. A janela "Escolher cor" da criação de perfil de cor é o seletor nativo do sistema
   (`tkinter.colorchooser.askcolor()`) — destoa visualmente do resto do app (CTk).
3. No formulário de lançamento, o seletor de Categoria (`CTkSegmentedButton`) não quebra em
   várias linhas (confirmado lendo o código do pacote) — com mais de ~4 categorias (possível
   desde as categorias personalizadas, ADR-0028) os nomes ficam espremidos e ilegíveis.
4. Os botões da seção "Perfis de cor" em Configurações (borda azul + texto escuro sobre fundo
   levemente azulado) ficaram com pouca visibilidade no modo claro.

## Decisão

- **`UI/iterador_ui/widgets/line_chart.py`** — novo método `update_series(series)` ao lado do já
  existente `update_data()` (intocado, ainda usado pelo histórico do CDI na Wiki). Uma linha
  suave por categoria (`theme.category_color`, mesma cor da fatia do gráfico de pizza) + legenda
  embutida com variação % vs mês anterior (`_format_delta`: `"novo"` se a categoria não tinha
  valor no mês anterior, `"-100%"` se tinha e não tem mais).
- **`UI/iterador_ui/views/dashboard_view.py`** — `self._trend_chart` (`LineChart`) ao lado do
  `ConsumptionChart` em `top_row`. `_monthly_category_series()` gera 6 meses civis terminando no
  mês selecionado (`_shift_month`, aritmética simples em `"YYYY-MM"`, sem `datetime`), soma
  despesas por categoria por mês (mesma regra do gráfico de pizza), mês sem lançamento entra como
  `0.0` (eixo do tempo uniforme). Só as categorias do mês selecionado agora entram — mesmo
  conjunto do gráfico de pizza, sem acumular categoria antiga irrelevante.
- **`UI/iterador_ui/widgets/color_picker_dialog.py`** (novo) — `ColorPickerDialog`, mesmo layout
  conceitual do nativo (3 sliders R/G/B + hex + preview + OK/Cancelar) em widgets CTk, sincronia
  bidirecional slider↔hex. Usa `dialog_utils.make_modal`/`open_singleton`, mesmo padrão de todo
  diálogo do app. `color_profile_dialog.py` troca `colorchooser.askcolor()` por esse diálogo.
- **`UI/iterador_ui/widgets/category_picker.py`** (novo) — `CategoryPicker`, grade de `CTkButton`
  "chips" (`_COLUMNS = 4`) em vez de `CTkSegmentedButton` só pra Categoria (Despesa/Receita, só 2
  valores, continua segmented button). Mais de `_MAX_VISIBLE_ROWS = 2` linhas → grade dentro de
  um `CTkScrollableFrame` de altura fixa; até 2, `CTkFrame` comum. A picker observa a própria
  `StringVar` (`trace_add`) pra se re-destacar sozinha, tanto por clique quanto por `.set()`
  externo — não precisa de um `command` feito à mão. `transaction_form_dialog.py`:
  `_HEIGHT_BASE`/`_HEIGHT_WITH_INVESTMENT` +50px (`"320x670"`/`"320x750"`) pra caber até 2 linhas
  de chips, fixo independente de quantas categorias existem.
- **`UI/iterador_ui/theme.py`** — `outline_button_style(strong_border=False)`: com
  `strong_border=True`, troca `border_color` de `BORDER_ACCENT` (azul) pra um par neutro
  `(CARBON_BLACK, TEXT_ON_BLACK)` (preto no claro, quase-branco no escuro) + fonte em negrito.
  `CTkButton` só aceita 1 par borda/cor (confirmado lendo o código do customtkinter) — não dá pra
  "empilhar" duas bordas, então isso SUBSTITUI a cor de destaque nesses botões em vez de somar. Só
  os 5 botões de "Perfis de cor" em `settings_view.py` usam `strong_border=True` — o resto do
  app (Desfazer/Refazer etc.) mantém o padrão, o problema relatado foi só nessa seção.

## Consequências

- `LineChart` agora tem dois modos de uso mutuamente exclusivos (`update_data`/`update_series`)
  numa mesma classe — cada instância usa um ou outro, nunca os dois na mesma tela.
- `CategoryPicker` reconstrói todos os chips a cada `set_values()` (poucos, ~10 no máximo) —
  diferente do pool de widgets da lista de lançamentos (ADR-0026), que lida com centenas; aqui
  reconstruir é barato o bastante pra não precisar de pooling.
- Duas categorias diferentes cujo mês mais recente empate em valor ficam em ordem "de desempate"
  arbitrária (ordem do dict) na legenda do comparativo mensal — cosmético, sem impacto funcional.
