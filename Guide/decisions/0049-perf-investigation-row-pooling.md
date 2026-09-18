# 0049 — Investigação de performance: drawing method do CTk, pool de linhas no Investimentos

Status: Aceito

## Contexto

Usuário relatou 3 sintomas: app demora pra abrir, demora pra trocar de aba, demora pra trocar de
mês no Início. Pediu investigação + o que der pra melhorar; depois pediu pra pesquisar na
internet por otimizações aplicáveis sem mudança drástica, perguntando se seria um problema
estrutural.

## Método

`cProfile` (e, pro Achado 1, comparação A/B cronometrada) contra um banco sintético isolado
(`/tmp`, nunca `~/.iterador/iterador.db` — ver CLAUDE.md), na mesma escala do histórico real do
usuário (ver `Guide/spreadsheet-reference.md`): ~700 lançamentos em 33 meses (18-24/mês) + 8
investimentos, gerados via `backend_bridge` de verdade (sem atalho, mesmo caminho que a UI usa).
Rodado em Xvfb, medindo separadamente: (1) `IteradorApp.__init__` completo (abrir o app), (2)
primeira visita a cada aba (custo de construção), (3) revisitar uma aba já construída, (4) várias
trocas de mês seguidas no Início, em regime estável (pool de linhas já "aquecido").

Pesquisa: GitHub issues/discussions do próprio `CustomTkinter`
([#1461](https://github.com/TomSchimansky/CustomTkinter/issues/1461),
[#2778](https://github.com/TomSchimansky/CustomTkinter/issues/2778),
[#2690](https://github.com/TomSchimansky/CustomTkinter/issues/2690)) — o mantenedor confirma
várias vezes que "performance problems are inherent to tkinter and therefore cannot get fixed",
recomendando reduzir nº de widgets ou usar outra biblioteca (PyQt) pro caso extremo. Não achei
nenhum fork/patch de terceiros que resolva isso — mas o próprio pacote expõe uma opção pública
pouco documentada (ver Achado 1) que ataca boa parte do problema sem mudar nada da nossa
arquitetura.

## Achado 1 (o maior ganho): `DrawEngine.preferred_drawing_method` — "font_shapes" vs "polygon_shapes"

Todo widget arredondado do CTk (qualquer `CTkButton`/`CTkFrame` com `corner_radius`) é desenhado
por um de 3 métodos (`customtkinter.windows.widgets.core_rendering.draw_engine.DrawEngine`,
`DRAWING_METHODS = ["polygon_shapes", "font_shapes", "circle_shapes"]`) — escolha pública, o
próprio app de exemplo que vem junto do pacote (`customtkinter/__init__.py`) tem um seletor pra
isso na UI. **No Linux/Windows o padrão é `"font_shapes"`** (desenha cada canto arredondado como
o glifo de uma fonte especial, via `create_text` — visualmente mais suave, mas cada
`create_text`/`coords` é uma chamada Tcl inteira); **no macOS o padrão é `"polygon_shapes"`**
(2 polígonos redesenhados via `coords()`, sem nenhum `create_text`/`create_aa_circle` por
widget) — bem mais barato. `"circle_shapes"` é o 3º método, só usado como fallback quando a fonte
especial não carrega, e o próprio pacote documenta como "má qualidade".

Ou seja: **quem roda Iterador no Linux (esta máquina) ou Windows já paga, por padrão, o modo de
desenho mais caro dos 3** — não é bug nosso, é a escolha de qualidade/performance padrão do CTk
pra essas plataformas.

Comparação A/B medida (banco sintético, mesmos 697 lançamentos/33 meses/8 investimentos):

| | `font_shapes` (padrão Linux, antes) | `polygon_shapes` (depois) |
|---|---|---|
| Abrir o app | 0,90s | **0,37s** (~2,4x) |
| 1ª visita a Investimentos | 0,35s | **0,04s** (~9x) |
| 1ª visita a Configurações | 0,49s | **0,04s** (~11x) |
| Trocar de mês (regime estável) | 0,22s | **0,17s** (~25%) |

`"circle_shapes"` rendeu números quase idênticos a `"polygon_shapes"` no teste, mas é
explicitamente documentado como pior qualidade visual — sem motivo pra usar em vez de
`"polygon_shapes"`.

**Decisão**: `UI/iterador_ui/app.py`, logo depois do `import customtkinter`, antes de qualquer
widget ser construído: `DrawEngine.preferred_drawing_method = "polygon_shapes"`. Sem condicional
de plataforma — no macOS já é o padrão, reafirmar não muda nada. Troca de 1 linha, reversível,
sem tocar em nenhuma view/widget — exatamente o tipo de mudança "não drástica" pedida. Efeito
colateral visual esperado: cantos arredondados ligeiramente menos suaves que antes (mesmo método
que todo usuário de macOS do CTk já vê por padrão, então é uma qualidade testada em produção por
outras pessoas, não um modo experimental) — vale conferir a olho depois de instalar, mas não é
uma mudança de "baixa qualidade" (essa é `circle_shapes`).

## Achado 2: `InvestmentsView.refresh()` destruía e reconstruía tudo — corrigido

Causa raiz: `refresh()` fazia `for child in self._list_frame.winfo_children(): child.destroy()`
e reconstruía TODAS as linhas do zero a cada chamada — e `IteradorApp.show_view()` chama
`refresh()` toda vez que se volta pra uma view já visitada (não só a primeira vez). Medido (antes
do Achado 1, ainda em `font_shapes`): revisitar a aba com só 8 investimentos custava ~274ms,
escalando linear com a quantidade.

**Decisão**: mesmo padrão de `DashboardView` (pool de linhas reaproveitado, ver ADR-0026) —
`_get_or_create_row()` cria cada linha uma vez só, `refresh()` daí em diante só faz
`.configure()` nos textos/comandos e reposiciona. Diferença deliberada: `grid(row=index, ...)`
em vez de `pack()` — o pool de investimentos pode ter a ORDEM mudada entre uma renderização e
outra (investimento removido do meio da lista, por exemplo), e `pack()` num widget já gerenciado
não reordena sozinho (só `grid()` com `row=` explícito garante posição determinística por índice
sempre, mesmo padrão que `DashboardView` já usa por esse motivo). Medido: revisitar a mesma aba
caiu de ~274ms pra ~5ms (~55x) mesmo antes do Achado 1; combinado com `polygon_shapes`, ~3ms.

## Achado 3: `MonthSelector.update_months()` reconfigurava a tira inteira a cada troca de mês

Mesmo com o pool de botões já existente (ADR-0026, comentário original da própria função), o
loop que reaplica o destaque roxo do mês selecionado rodava sobre TODOS os botões da tira (~33
num histórico de 3 anos) a cada troca de mês — mesmo que só 2 precisassem mudar (o que perde o
destaque, o que ganha). `CTkButton.configure(fg_color=...)` sempre redesenha o retângulo inteiro,
mudando ou não o valor de verdade — reconfigurar 31 botões que não mudaram nada era desperdício
puro. Medido: ~34ms por troca de mês só nisso (~0.276s em 8 trocas).

**Decisão**: `_highlighted_month` guarda qual botão está com o destaque aplicado de verdade;
`update_months()` só toca os 2 botões (antigo/novo) quando o conjunto de meses não mudou.

## Achado 4: o piso restante é overhead inerente ao CustomTkinter, não um bug

Mesmo com os 3 fixes acima e o pool de linhas do Início já "aquecido" (sem criar nenhuma linha
nova, só reconfigurando conteúdo), trocar de mês ainda custa **~175ms em regime estável** (era
~220ms antes do Achado 1, ~300ms antes de qualquer fix). Raiz confirmada pelo profile: mesmo com
`polygon_shapes`, a maior parte do tempo continua sendo chamadas Tcl (`_tkinter.tkapp.call`) por
trás de CADA operação de desenho — e o conteúdo da lista **muda de verdade** a cada mês
(transações diferentes), então a otimização "não redesenha se não mudou" (já usada em
`OutlinedLabel.set_text()`/`StatCard`) não ajuda aqui: quase toda célula muda mesmo.

**Não implementado nesta rodada** — reduzir esse piso de verdade exigiria trocar o modelo atual
(uma linha = vários widgets CTk reais, com drag-and-drop/pin/editar/remover clicáveis de
verdade) por uma lista desenhada num Canvas só (texto/retângulos desenhados à mão, sem widget
por célula) — mesma técnica já usada em `ConsumptionChart`/`LineChart`/`TriangleHeading`. Ganho
real, mas é uma reescrita grande da lista de lançamentos inteira (perde os widgets nativos de
clique/hover/arrasto que já existem, tudo reimplementado à mão em cima de eventos de mouse no
Canvas) — risco de regressão alto o bastante pra não fazer sem decisão explícita do usuário, e
foge do escopo "sem mudança drástica" pedido nesta rodada. Fica registrado aqui como próximo
passo possível, não como pendência assumida. Confirma a resposta de "é estrutural?": sim, é
estrutural ao Tkinter/CTk em si (mantenedor do CTk confirma isso publicamente, ver Método) — o
Achado 1 é o que dava pra espremer dessa estrutura sem reescrever nada; o resto exigiria sair
dela.

## Consequências

- `app.py`/`InvestmentsView`/`MonthSelector` testados isoladamente (Xvfb, banco sintético em
  `/tmp`, nunca o banco real) antes/depois de cada fix, números acima medidos de verdade, não
  estimados.
- Abrir o app e trocar de aba (incluindo Investimentos, agora com pool) ficaram bem mais rápidos
  na prática (0,90s→0,37s abrir; a maioria das trocas de aba na casa de poucos ms). Início ainda
  é a view mais cara de trocar de mês — arquitetural (Achado 4), mas ~25% mais rápido que antes
  de qualquer fix desta rodada.
