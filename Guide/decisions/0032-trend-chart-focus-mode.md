# 0032 — Modo foco no comparativo mensal (clicar categoria na legenda)

Status: Aceito

## Contexto

No comparativo mensal por categoria (`LineChart.update_series()`, ADR-0029/0030), quando duas ou
mais linhas se aproximam/cruzam num trecho do gráfico, fica difícil saber visualmente (e pro
hover acertar) qual linha é qual — o usuário mandou um screenshot mostrando exatamente esse caso
(Essencial e Lazer quase coincidindo entre 05/2026 e 07/2026). Pedido: clicar numa categoria na
legenda "foca" ela — nesse modo, se várias categorias se sobrepõem, a categoria selecionada é
priorizada.

## Decisão

`UI/iterador_ui/widgets/line_chart.py`:

- Clicar em qualquer parte de uma linha da legenda (bolinha, nome ou variação %) alterna
  `self._hover_state["focused"]` pra essa categoria — clicar de novo (ou na mesma já focada)
  desliga (`_toggle_focus`). Precisou bindar `<Button-1>` em CADA widget filho da linha da
  legenda, não só no `CTkFrame` container — em Tk um clique num filho nunca "vaza" pro pai.
- Clicar na própria linha da categoria dentro do gráfico faz o mesmo efeito (pedido do usuário
  depois do modo foco já existir só via legenda) — `<Button-1>` no `_plot_canvas`
  (`_on_canvas_click`) acha a categoria mais perto do ponto exato do clique
  (`_category_at`, mesmo raio de tolerância do hover, mas ignora o foco de propósito: o clique
  sempre mira a linha fisicamente mais perto daquele pixel, não a que já estava focada) e chama
  o mesmo `_toggle_focus`. Clicar em espaço vazio (nenhuma linha por perto) não faz nada.
- **Visual**: com foco ativo, a categoria focada fica na cor cheia e por cima das outras
  (`tag_raise`); as demais ficam esmaecidas (`theme.shade_color(cor, -0.55)`) — reaproveita o
  mesmo helper já usado pro hover do botão Pago/A pagar e pelo destaque de hover deste próprio
  gráfico (ADR-0030), só com um valor negativo (escurecer) em vez de positivo (clarear). A linha
  da legenda da categoria focada também ganha um fundo levemente diferente (`theme.BG_APP`).
- **Hover**: dentro do raio de tolerância (`_HOVER_RADIUS_PX`), a categoria focada vence sobre
  qualquer outra mesmo que não seja a pixel-a-pixel mais próxima do mouse — é exatamente esse o
  "prioriza a categoria selecionada" pedido pra quando as linhas se sobrepõem. Fora do raio da
  focada mas dentro do de outra, a outra ainda pode ser hoverada normalmente (o foco desambigua
  sobreposição, não desliga a interação com as demais linhas).
- **Sem foco ativo**: `state["hovered"]` deixou de ser uma categoria só (`str | None`) e virou
  uma lista — quando NENHUMA categoria está focada e o ponto do mouse tem mais de uma categoria
  dentro do raio ao mesmo tempo (linhas se cruzando), o tooltip lista todas as que se sobrepõem
  ali (mês + valor de cada), e todas ficam destacadas juntas, em vez de escolher uma "vencedora"
  arbitrária entre elas (pedido do usuário: sem uma categoria selecionada pra desambiguar, mostra
  todas as candidatas em vez de adivinhar qual o usuário quer). Com foco ativo, a lista sempre
  colapsa pra 1 item (a focada, se estiver no raio; senão a mais próxima entre todas).
- **Persistência**: a categoria focada sobrevive a um `update_series()` novo (troca de mês,
  marcar Pago/A pagar etc. disparam `refresh()` do Início, que chama `update_series()` de novo) —
  sem isso, qualquer atualização do Início desfaria o foco escolhido sem aviso. Só é descartada se
  a categoria focada não existir mais no novo conjunto (ex. usuário trocou de mês e ela não tem
  gasto naquele mês).

## Correção: tooltip cortado na borda do gráfico

O tooltip original era 2 itens desenhados dentro do `_plot_canvas` (retângulo + texto) — um
`tkinter.Canvas` nunca desenha fora da própria área (é sempre cortado nas bordas do widget), então
perto de qualquer borda do gráfico o texto ficava cortado em vez de continuar visível por cima do
resto da tela (relato do usuário, com screenshot). Trocado por uma janela `tk.Toplevel` sem
decoração (`overrideredirect(True)`, `-topmost`), criada uma vez em `__init__` e reaproveitada via
`deiconify()`/`withdraw()`/`geometry()` — uma janela de verdade não tem esse limite, pode se
sobrepor a qualquer frame vizinho (o pedido explícito do usuário), só é cortada pelas bordas da
TELA (`winfo_screenwidth()`/`winfo_screenheight()`), que é o comportamento normal de qualquer
tooltip de sistema. Posição calculada em coordenadas de tela (`winfo_rootx()`/`winfo_rooty()` do
próprio canvas + a posição local do ponto), com fallback pra virar a janela pra baixo/esquerda do
ponto só quando bateria numa borda real da tela, nunca mais nas bordas do gráfico/card.

## Consequências

- `_display_color()` centraliza "qual é a cor de repouso desta linha agora" (cheia ou esmaecida
  por foco) — todo lugar que antes restaurava pra `state["colors"][cat]` direto (fim do hover)
  passou a restaurar pra isso, senão sair do hover apagaria o esmaecimento do modo foco.
- Sem indicação além da cor/fundo pra "isto é clicável" na legenda (sem cursor de mão, sem
  hover state próprio na legenda) — aceitável por ora, mas pode confundir se não for óbvio; ver se
  vira feedback real de uso.
