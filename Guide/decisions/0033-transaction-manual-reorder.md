# 0033 — Reordenação manual de lançamentos (arrastar, tipo playlist)

Status: Aceito

## Contexto

A lista de lançamentos (`DashboardView`) sempre foi ordenada por `occurred_at DESC` — não existia
nenhum conceito de ordem manual. O usuário pediu uma alça de arrastar (ícone
`UI/assets/sort-arrows-couple-pointing-up-and-down.png`) à esquerda de cada linha pra poder
reordenar livremente, "tipo playlist de música/YouTube Music", com a linha seguindo o mouse
durante o arrasto. Decisões tomadas com o usuário antes de implementar:

- Ordem manual **livre entre datas** — não fica presa a "só dentro do mesmo dia". A coluna Data
  continua mostrando a data real de cada lançamento, só a posição na lista deixa de depender dela.
- Clicar no cabeçalho "Data" **inverte a ordem por data** (ascendente/descendente) como uma
  visualização alternativa, sem precisar arrastar nada.
- Arrastar entra na pilha de Desfazer/Refazer (`UndoStack`, ADR-0013), igual criar/editar/remover.
- Os assets `Pin-on.png`/`Pin-off.png` (adicionados junto) não têm feature associada aqui — ficam
  reservados pra uma feature futura.

## Decisão: `sort_order` fracionário (não uma reordenação por inteiro completo)

Nova coluna `transactions.sort_order REAL` (migration `0004_add_transaction_sort_order.sql`,
nunca editar 0001-0003 — ver CLAUDE.md). Maior valor = aparece mais acima;
`TransactionRepository::listAll()` passou a ordenar por `sort_order DESC` em vez de
`occurred_at DESC`. Backfill da migration reproduz a ordem visual de antes via
`ROW_NUMBER() OVER (ORDER BY occurred_at ASC, rowid ASC)` — ninguém vê a lista embaralhar no
primeiro uso depois do update.

Ao soltar um lançamento arrastado, o novo `sort_order` é calculado por **indexação fracionária**
entre os vizinhos finais (não por uma renumeração completa da tabela): média dos dois vizinhos, ou
`vizinho + 1`/`vizinho - 1` nas pontas (sem vizinho acima/abaixo). Isso mantém a operação um
`UPDATE` de uma linha só, sem precisar tocar em nenhuma outra transação a cada arrasto. Colisão de
precisão de ponto flutuante depois de muitíssimos micro-ajustes repetidos no mesmo ponto é um
risco aceito, mesmo espírito da colisão de dedup aceita no ADR-0023 — não é um caso prático real
num app pessoal com uso normal.

A UI calcula o valor (é quem sabe os vizinhos do arrasto); `TransactionRepository::updateSortOrder`/
`Application::updateTransactionSortOrder`/`backend_bridge.update_transaction_sort_order` são só um
`UPDATE` fino, mesmo formato de `setStatus()` — sem lógica de negócio nova no C++.

Todo lançamento novo nasce com `sort_order = MAX(sort_order) + 1` (topo da lista) — preserva o
comportamento de "o mais novo aparece primeiro" mesmo sem o usuário nunca arrastar nada.

## Decisão: clicar em "Data" é uma view local, nunca persiste

`DashboardView._date_sort_mode` (`None`/`"asc"`/`"desc"`) só reordena o que já está na tela
(`_apply_date_sort`, sort estável por `occurred_at`) — nunca grava `sort_order` nenhum. Arrastar
qualquer linha, mesmo com esse modo ativo, sempre volta pro modo manual (`_date_sort_mode = None`)
e persiste a nova ordem calculada a partir dos vizinhos **como estavam sendo exibidos** naquele
momento (que pode ser a visualização por data) — o usuário que arrasta está tomando controle
manual de propósito, então não faz sentido a view "por data" continuar ativa depois disso.

## Decisão: mecânica de arrastar em CustomTkinter/Tkinter

Tkinter não tem física de mola nem opacidade por widget — depois de várias rodadas de relato do
usuário (mouse saindo do frame, várias linhas deslocando de uma vez, item sem "forma" durante o
arrasto), a mecânica final ficou assim:

- **O item arrastado sempre ocupa um slot de verdade** — nunca uma posição de pixel contínua
  vinda direto do mouse. `_on_handle_motion` só atualiza `pending_target` (onde o mouse aponta
  agora, com clamp em `[0, n-1]` — sair do frame prende no topo/fim em vez de "sumir" longe da
  lista); quem de fato move qualquer coisa na tela é `_advance_drag_target`, rodando em ritmo
  próprio (`_DRAG_TARGET_STEP_INTERVAL_MS = 100`, não a cada evento de mouse) — avança
  `target_offset` **uma posição por vez** em direção a `pending_target`. Um mouse físico normal
  pula mais de uma altura de linha entre dois eventos `<B1-Motion>`; sem esse ritmo próprio, o
  alvo saltava direto pra posição final e várias linhas (às vezes quase a lista inteira)
  deslocavam juntas num salto só. Ao soltar, o cálculo final usa `pending_target` (não
  `target_offset`, que pode estar atrasado) — o drop sempre respeita a posição real do mouse.
- Cada troca de slot — tanto do item arrastado quanto do único vizinho que "abre espaço" — é
  animada por `_animate_row_to_offset` (~6 passos via `self.after`, dentro da janela de 100ms),
  nunca instantânea. Um token por linha (`anim_token`) cancela uma animação anterior se o alvo
  mudar de direção antes dela terminar.
- **"Forma" durante o arrasto/deslize**: só **2 widgets fixos** (`self._drag_card`/
  `self._neighbor_card`, criados uma vez em `__init__`) — nunca um `card_bg` por linha do pool.
  Antes disso, a linha era só os campos individuais (Label/Button cada um com seu próprio fundo,
  com espaço transparente entre eles) flutuando via `.place()` — ao cruzar outra linha, o
  conteúdo de baixo aparecia por trás nos vãos entre os campos, texto embaralhado (relato do
  usuário, com screenshot). A primeira tentativa (um `card_bg` por linha, empilhamento via
  `.lift()`/`.lower()` soltos) melhorou mas ainda deixava o cartão de uma linha na FRENTE do
  próprio conteúdo em certos casos — 2 linhas duplicando esse mecanismo ao mesmo tempo (a
  arrastada + a vizinha deslizando) é ambíguo demais pra acertar só com `.lift()` relativo (outro
  screenshot do usuário mostrou exatamente isso: um retângulo escuro cobrindo o texto da própria
  linha). Só 2 widgets dedicados elimina a ambiguidade: `_show_card_bg(card, row_widgets)` sempre
  faz `card.tkraise()` (sem argumento, joga esse widget específico pro topo de tudo) e SÓ DEPOIS
  levanta o conteúdo da linha — sem depender de que outra chamada aconteceu antes/depois pra
  linhas diferentes.
- **Corrida real entre vizinhas pelo `_neighbor_card` compartilhado**: `anim_token` (cancela uma
  animação anterior) é rastreado por LINHA (`pool_index`), não pelo widget do cartão em si. Se
  dois "hops" disparassem antes do primeiro terminar (~72ms de animação contra 100ms de ritmo —
  qualquer soluço do sistema, ou um arrasto cruzando várias linhas rápido, deixa essa margem
  curta demais), a animação da vizinha ANTERIOR continuava achando válida (seu token não mudou)
  e seguia chamando `.place()` no MESMO widget físico que a vizinha NOVA também controlava — as
  duas brigando pela posição do cartão compartilhado, pulando entre as duas linhas (relato do
  usuário: "uma cópia dele fica aparecendo e sumindo no topo"). Corrigido com
  `self._drag["neighbor_card_owner"]` — reivindicado por quem começa a usar `_neighbor_card`,
  checado dentro do `step()` além do `anim_token`; perder a posse faz a animação anterior parar
  de mexer em qualquer coisa na hora, em vez de brigar pelo cartão. Testado forçando o pior caso
  (chamando `_advance_drag_target()` manualmente em sequência, sem esperar a animação anterior
  terminar) — sem exceção, sem cartão fantasma sobrando, resultado final correto.
- **Ritmo acelerado fora dos limites da lista**: com o ritmo fixo de 100ms/passo, arrastar o
  mouse pra fora do frame (relato do usuário: "perde totalmente o track do mouse") fazia o item
  demorar `nº de linhas × 100ms` (podendo passar de 1-2s numa lista longa) pra alcançar a borda,
  parecendo sem resposta. `_on_handle_motion` agora também guarda `drag["outside_bounds"]`
  (mouse de verdade fora do intervalo `[0, n-1]`, não só encostando nele); `_advance_drag_target`
  usa um intervalo bem menor (`_DRAG_TARGET_OUTSIDE_BOUNDS_INTERVAL_MS = 20`) nesse caso — continua
  trocando uma linha de cada vez (nunca volta a pular várias juntas, isso ficaria idêntico ao bug
  original), só que bem mais rápido até chegar na borda.
- **Robustez contra travar de vez**: `_advance_drag_target` reagenda a si mesma
  (`self.after(...)`) — uma exceção não tratada no meio mataria esse reagendamento pra sempre,
  deixando o arrasto visualmente parado no meio do caminho sem nenhum jeito de sair a não ser
  soltar o mouse. O corpo agora roda dentro de um `try/except` que loga (`traceback.print_exc()`)
  e deixa o próximo ciclo tentar de novo, em vez de matar o laço de vez.
- **Armadilha real encontrada**: CTk proíbe passar `width`/`height` em `.place()` ("must be passed
  to the constructor, not the place method", vale pra `CTkFrame` também) — só `x`/`y` no
  `.place()`; largura/altura dos cartões vêm de `.configure()` antes.

### Log de diagnóstico e a causa raiz real da instabilidade

As correções acima ajudaram mas o usuário ainda relatava instabilidade real em uso — a essa
altura, ficou claro que só ler o código e testar com eventos sintéticos (onde eu escolho os
valores) não bastava: o TIMING real do mouse importa. Adicionado um log de diagnóstico
(`_log_drag`/`_flush_drag_log`, desligado por padrão — liga com `ITERADOR_DEBUG_DRAG=1
./scripts/run_ui.sh`, grava em `/tmp/iterador_drag_debug.log`, nunca no banco) registrando
posição do mouse, alvo calculado e a posição REAL (`winfo_y()`) dos widgets a cada evento.

O log revelou a causa raiz de verdade, mais fundamental que tudo que tinha sido corrigido até
aqui: **assim que a linha arrastada sai do grid (`.place()`), a linha do grid que ela ocupava
fica sem nenhum widget, e o Tk encolhe a altura dela pra 0** — empurrando TODAS as linhas
seguintes pra cima. Confirmado isolado (fora do fluxo de arrasto): tirar só a linha 0 do grid
fazia as linhas 1/2/3 subirem um `row_step` inteiro cada uma, na hora.

Isso é grave porque `row_step`/`list_top` são medidos **uma única vez**, no início do arrasto
(`_on_handle_press`), e usados como "régua" pra calcular a posição de tudo — o alvo a partir do
mouse, o `pixel_delta` de cada animação, tudo. Assim que a primeira linha saía do grid, essa
régua ficava desalinhada da realidade pro resto do arrasto inteiro, e cada vizinha adicional
tocada (mais uma saindo do grid) desalinhava ainda mais — explicando tremor generalizado,
posições erradas e o "fantasma" (o `_neighbor_card`, ao ler a posição real da próxima vizinha pra
saber de onde partir, pegava uma posição já corrompida por esse colapso).

Corrigido travando a altura de CADA linha do grid em uso (`grid_rowconfigure(row, minsize=...)`,
medida via `grid_bbox` antes de qualquer `.place()`) logo no início do arrasto — `minsize`
garante que aquela linha do grid reserva aquele espaço mesmo sem nenhum widget dentro dela.
Revertido (`minsize=0`) fora de um arrasto, pra não deixar espaço reservado sobrando de uma lista
que depois encolhe (ex. filtro de busca). Confirmado pelo log: todas as posições (`card_start_y`)
batem exatamente com o esperado (`list_top + offset × row_step`) do início ao fim de arrastos
longos, sem nenhuma anomalia.

### `<B1-Motion>` não é confiável — consulta ativa da posição do mouse

Mesmo depois de tudo acima, o usuário ainda relatava o item "falhando em seguir o mouse" e
"travando numa posição" **com o botão ainda pressionado** (não era travamento de verdade — dava
pra continuar depois). O log de diagnóstico (ver seção acima) de um arrasto de ~18s mostrou algo
revelador: o "tick" (`self.after`, ritmo próprio) disparou certinho o tempo todo, sem nenhum
hiato maior que ~300ms — mas os eventos `<B1-Motion>` **pararam de chegar por vários segundos
seguidos**, mais de uma vez no mesmo arrasto, mesmo com o botão presumivelmente ainda
pressionado e o mouse se movendo de verdade. O Tk (ou o gerenciador de janela/sessão gráfica —
bem plausível numa sessão Wayland/XWayland do KDE) não está entregando esses eventos de forma
confiável o tempo todo.

Corrigido trocando a fonte da posição do mouse: `_advance_drag_target` agora consulta
`winfo_pointery()` (posição real do ponteiro, sem depender de NENHUM evento chegar) a cada
"tick" — `_compute_pending_target()` centraliza esse cálculo, chamado tanto por
`<B1-Motion>` (quando chega, dá uma resposta mais imediata entre um tick e outro) quanto pelo
próprio tick (a fonte confiável de verdade, já que o log confirmou que ele nunca para de
disparar). Testado forçando o cenário exato do bug: só um evento de motion no início, NENHUM
depois — mesmo assim o arrasto completa corretamente, porque o tick consulta a posição sozinho.

### "Fantasmas" — buracos vazios deixados por linhas que nunca voltavam pro grid

A correção do tremor fora da lista (seção acima) tinha um efeito colateral não percebido na hora:
evitar QUALQUER `.grid()` durante o arrasto inteiro significava que toda linha tocada (arrastada
ou vizinha) ficava presa em `.place()` até soltar de vez — a posição de grid que ela abandonou
ficava vazia (mas reservada por `minsize`) pro resto do arrasto, já que nada mais a ocupava.
Num arrasto que passa por várias linhas, isso deixava vários "buracos" simultâneos — o usuário
relatou e numerou num screenshot: posição do mouse, dois espaços vazios diferentes, e a transação
flutuando numa QUARTA posição, sem bater com nenhum dos outros três.

Testado isolado: com `minsize` já travado (a correção anterior), voltar a chamar `.grid()` no
meio do arrasto **não dispara mais nenhum recálculo de `scrollregion`** — a causa raiz do tremor
era só o colapso da altura da linha do grid, e isso já tinha sido resolvido; evitar `.grid()`
por completo era uma correção a mais do que o necessário, e essa correção extra é o que criava
os buracos. `_animate_row_to_offset` volta a chamar `_grid_row_widgets` assim que uma linha
termina de deslizar (arrastada ou vizinha) — nunca mais fica "flutuando" indefinidamente. A
arrastada mostra o cartão de novo por cima assim que assenta (senão sumiria entre um "hop" e o
outro). Testado num arrasto de 8 posições: nenhuma linha fica sem nenhum gerenciador de geometria
(nem grid nem place) em momento nenhum, e `scrollregion` continua em zero disparos.

**Segunda rodada de fantasmas**: mesmo depois disso, o usuário ainda relatou buracos — com uma
pista valiosa: "os espaços vazios são consertados quando ele passa por aquele mesmo espaço
novamente". Isso apontou pra um caso específico não coberto: quando o cartão compartilhado
(`_neighbor_card`) é "roubado" por uma vizinha NOVA antes da vizinha ANTERIOR terminar de
deslizar, o `step()` da vizinha anterior cancela (`neighbor_card_owner != pool_index`) e
retornava sem nunca chamar `_grid_row_widgets` — diferente do cancelamento por `anim_token`
(onde uma animação MAIS NOVA da MESMA linha assume e vai terminar o serviço mais tarde), aqui
ninguém mais cuida daquela linha: o token dela continua válido, só o cartão que não pode mais
usar. Ela ficava órfã, flutuando numa posição intermediária pra sempre — só "consertava" se essa
MESMA linha fosse tocada de novo num arrasto futuro (batendo exatamente com o relato). Corrigido
assentando direto no destino (`_grid_row_widgets(row_widgets, to_offset)`, sem terminar a
animação suave) nesse cancelamento específico, já que não tem mais como usar o cartão pra
deslizar. Testado forçando o cenário exato (duas reivindicações do cartão antes da primeira
terminar) — a linha abandonada sempre acaba assentada na posição certa, nunca órfã.

### `<ButtonRelease-1>` também pode se perder — item continuava seguindo o mouse sozinho

Consequência direta da correção acima: como `_advance_drag_target` passou a consultar a posição
do mouse ativamente (sem depender de nenhum evento), se o **`<ButtonRelease-1>`** também se
perdesse pelo mesmo motivo do `<B1-Motion>` (mesmo mecanismo de entrega, mesma causa provável),
`self._drag` nunca era limpo — e o "tick" continuava "arrastando" o item atrás do mouse pra
sempre, mesmo bem depois do usuário soltar o botão de verdade (relato do usuário, com
screenshot, "bastante reproduzível").

Corrigido com uma rede de segurança que não depende de nenhum evento específico de soltar:
`_on_handle_press` liga `<Motion>` (sem prefixo de botão — parece chegar de forma mais confiável
que `<B1-Motion>`/`<ButtonRelease-1>`) na JANELA RAIZ via `bind_all` — checa o bit `0x100`
(Button1) do campo `state` do evento; se o botão não estiver mais pressionado enquanto ainda
achávamos que o arrasto seguia, chama `_on_handle_release()` na hora, como se tivesse soltado
agora mesmo. **Armadilha real**: `bind_all`/`unbind_all` são bloqueados em qualquer widget CTk
comum (`CTkBaseClass.bind_all` levanta `AttributeError` de propósito, "could result in undefined
behavior") — só a janela raiz (`CTk`, que não herda dessa classe) permite, então precisa ser
`self.winfo_toplevel().bind_all(...)`, nunca `self.bind_all(...)`.

### Investigação: "coisas fora da lista tremendo" durante o arrasto

O usuário pediu pra ler o HTML salvo da página da YouTube Music
(`/run/media/Prizmo/Prizmo/Code/HTML_Sites/YouTube Music.html`) procurando a técnica deles de
estabilizar o item arrastado. O HTML salvo em si é só a casca inicial da página (Polymer/Shadow
DOM, carregado dinamicamente) — a lógica de arrastar de verdade estava no bundle
`YouTube Music_files/music_polymer_inlined_html.js`, na classe `Vtb` (o
`reorderableListController`). O trecho relevante (`onDragStart`):

```js
d.style.cursor="move";
d.style.width=e.clientWidth+"px";       // largura travada explicitamente
d.style.zIndex="9";                      // empilhamento por número, sem ambiguidade
d.style.backgroundColor="var(--ytmusic-brand-background-solid)";  // "forma" sólida
d.style.transform="translateX(-"+(c.clientX-e)+"px)";  // offset SÓ visual
```

O ponto central: `transform` no CSS é só de composição/pintura — o navegador NUNCA recalcula
layout por causa dele, então nenhum outro elemento da página é afetado enquanto o item flutua. A
ordem real do DOM só muda de fato ao soltar.

Isso levou a procurar o equivalente em Tkinter: `.place()` não deveria disparar layout dos
pais... só que **retirar um widget do `.grid()` (pra colocar em `.place()`) já conta como mudança
de geometria** — por padrão (`grid_propagate` ligado), o `_list_frame` recalcula seu tamanho
"necessário" toda vez que um filho grid sai/entra, mesmo sem nenhuma chamada `.grid()` explícita
durante o arrasto. Isso se propaga por `transactions_frame` → `content_panel` →
`page_scroll` (`CTkScrollableFrame`, a página inteira do Início) — que tem, no próprio
`customtkinter` (`ctk_scrollable_frame.py`):

```python
self.bind("<Configure>", lambda e: self._parent_canvas.configure(scrollregion=self._parent_canvas.bbox("all")))
```

Ou seja: qualquer `<Configure>` no `page_scroll` recalcula a região de rolagem da tela inteira —
exatamente o "coisas fora da lista tremendo" relatado (gráfico, cards, tudo que divide o mesmo
`page_scroll`). Duas correções, achadas nessa ordem:

1. `_animate_row_to_offset` **nunca mais chama `.grid()`** durante o arrasto — a linha
   (arrastada ou vizinha) fica em `.place()` até o `refresh()` final de `_on_handle_release`, que
   recoloca tudo no grid de uma vez só (a única "mudança de layout de verdade" da operação
   inteira, igual a YouTube Music só reordenar o DOM de fato ao soltar). **Revisto depois** (ver
   seção "Fantasmas" mais abaixo) — isso criava outro bug (buracos vazios); a correção 2 abaixo
   (`minsize`) sozinha já resolve o tremor, e `.grid()` voltou a ser chamado normalmente no fim
   de cada deslize.
2. Mesmo sem `.grid()`, o simples `.place()` inicial (tirando o widget do grid) ainda mexia no
   tamanho — `_on_handle_press` agora trava a altura do `_list_frame`
   (`.configure(height=winfo_height())` + `grid_propagate(False)`) assim que o arrasto começa, e
   `_render_transaction_list` liga `grid_propagate` de volta fora de um arrasto (pra continuar
   acompanhando o tamanho real quando o nº de lançamentos muda por outro motivo).

Confirmado por teste automatizado espionando `canvas.configure(scrollregion=...)` do
`CTkScrollableFrame` e `CTkBaseClass.grid`: zero chamadas de qualquer um dos dois durante um
arrasto inteiro (vários "hops"), depois das duas correções.

Ao soltar, sempre chama `refresh()` (recarrega do backend) — qualquer `.place()` residual é
descartado porque `_render_transaction_list`/`_grid_row_widgets` volta todo mundo pro `.grid()`
numa única passada.
- `_render_transaction_list` ignora chamadas enquanto um arrasto está em andamento (`self._drag is
  not None`) — evita que um refresh disparado por outra coisa no meio do caminho (ex. debounce de
  busca atrasado) brigue com as posições temporárias do arrasto.

Testado programaticamente (sem interação humana) simulando os eventos de mouse via objetos falsos
com `.y_root` — os handlers só leem esse atributo, então dá pra exercitar arrastar pro topo, pro
fim, pra cima e pra baixo, saltos grosseiros de mouse (confirmando que o alvo avança de 1 em 1),
soltar antes do ritmo visual alcançar, a visibilidade do `card_bg`, e o toggle de ordenar por
data — tudo isolado num banco de teste em `/tmp` (nunca `~/.iterador/iterador.db`) rodando dentro
de um `Xvfb`, esperando o tempo real necessário (`time.sleep`) pros ciclos de 100ms acontecerem de
verdade.

## Decisão: botão "Resetar posições" (desfazível)

Botão só ícone (`UI/assets/reset.png`, recolorido de branco em tempo de execução — pedido do
usuário, mesma técnica de `_tinted()` já usada no ícone da alça) no cabeçalho da lista, com o
estilo `theme.outline_button_style()` (fundo transparente, borda azul — "quadrado transparente com
borda azul" pedido pelo usuário). Confirma com `ConfirmDialog` antes (mesmo padrão de "Remover
mês", ADR-0019) e reordena as transações do mês atual por `occurred_at` decrescente (empate
quebrado pela ordem manual atual — sort estável, mesma lógica de `_apply_date_sort`), reatribuindo
`sort_order` só de quem realmente muda de lugar.

`ResetTransactionOrderCommand` (`transaction_commands.py`) empilha TODAS as reatribuições feitas
num único item de Desfazer/Refazer — mesmo princípio de `RemoveMonthCommand`: uma ação em lote não
deveria virar dezenas de "Desfazer" separados.

## Ajuste: ritmo de 100ms pra 20ms — e o que isso quebrou

`_DRAG_TARGET_STEP_INTERVAL_MS` (a "régua" que separa uma troca de linha da próxima, ver acima)
começou em 100ms — relato do usuário: o item ficava lento pra acompanhar o mouse. Baixado pra
20ms; `_DRAG_TARGET_OUTSIDE_BOUNDS_INTERVAL_MS` (o ritmo acelerado fora dos limites da lista)
ajustado de 20 pra 4ms, mantendo a mesma proporção (~5x mais rápido que o ritmo normal).

Isso expôs duas armadilhas reais que só apareciam com o ritmo mais rápido:

1. **Duração do deslize maior que o ritmo dos "hops"**: `_DRAG_ANIMATION_STEPS`/
   `_DRAG_ANIMATION_INTERVAL_MS` (a animação de cada troca de posição) ainda levava 6×12ms=72ms
   — bem mais que os 20ms novos entre um "hop" e o próximo. Um "hop" novo chegava sempre antes
   do anterior terminar, cancelando-o no meio (relato do usuário: "o item em si fica pra trás").
   Encurtado pra 2×8ms=16ms, cabendo dentro do ritmo de 20ms.
2. **`_show_card_bg` lendo `row_widgets["date"].winfo_y()` bem depois de um `.grid()` acabar de
   rodar** (`_grid_row_widgets`, ao assentar a linha arrastada de volta entre um "hop" e o
   outro) — a MESMA categoria de armadilha do `card.winfo_y()` já corrigida antes (ver seção
   acima), só que do lado do `.grid()`: o Tk não atualiza a geometria consultável até processar
   a fila de eventos, e ler na mesma chamada síncrona devolve a posição ANTIGA. O conteúdo real
   da linha (`_grid_row_widgets`, que assenta numa posição absoluta calculada, não lida) sempre
   ficava certo; só o cartão (que relia nessa leitura) ficava "preso" numa posição antiga, cada
   vez mais para trás conforme mais "hops" aconteciam sem nunca se corrigir sozinho — batendo
   exatamente com o relato ("o item em si fica pra trás enquanto o espaço vazio acompanha
   normalmente"). Corrigido eliminando a leitura por completo: `_show_card_bg` agora sempre
   RECEBE o `offset` de onde deveria estar e calcula a posição pela mesma fórmula confiável
   (`list_top + offset × row_step`), nunca relendo `winfo_y()` de outro widget.

O mecanismo de cancelamento por `anim_token`/`neighbor_card_owner` já foi desenhado pra suportar
qualquer ritmo de disparo sem corromper nada (ver seções acima) — só precisou dessas duas
correções extras pra realmente aguentar um ritmo bem mais rápido que o original.

## Auto-scroll perto da borda visível

Arrastar um lançamento pra além do que está visível na tela (não só fora da lista — o
`CTkScrollableFrame`/`page_scroll` cobre a tela inteira do Início, gráfico e cards incluídos)
deixava o item "preso" numa posição fora da parte visível, sem jeito de alcançar o resto da
lista (relato do usuário: rolar a página pra baixo antes de arrastar um item de baixo pra cima
prendia o arrasto). `_maybe_auto_scroll` (chamado a cada "tick" de `_advance_drag_target`, mesmo
ritmo — não precisa de agendamento próprio) checa a posição do mouse (`winfo_pointery()`) contra
os limites VISÍVEIS do canvas interno do `page_scroll` (`_parent_canvas`, não é API pública do
`CTkScrollableFrame` — mesmo acesso direto já usado pelos testes deste projeto) e rola sozinho
(`yview_scroll`) quando o mouse chega a `_AUTO_SCROLL_MARGIN_PX` (50px) da borda de cima/baixo.
Como `_list_frame.winfo_rooty()` é sempre lido fresco (nunca cacheado) em
`_compute_pending_target`, a rolagem automática não exige nenhuma mudança na matemática de
posição/alvo — o sistema já se adapta sozinho a onde a lista está na tela a cada consulta.

## Consequências

- A coluna Data deixa de ser garantia de ordem visual — é só informativa agora, a menos que o
  usuário clique no cabeçalho pra ordenar por ela (ou resete a ordem do mês pro botão de reset).
- Nenhuma automação de "renumerar tudo" existe se `sort_order` degenerar com o tempo (uso muito
  intenso de arrastar sempre no mesmo ponto) — aceito por ora, ver seção de decisão acima. O botão
  de reset serve como uma válvula de escape manual pra esse (improvável) cenário, mesmo não tendo
  sido desenhado especificamente pra isso.
