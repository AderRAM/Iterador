# 0026 — Pool de widgets na lista de lançamentos (correção de performance)

Status: Aceito

## Contexto

O usuário relatou lentidão perceptível em 3 ações do Início: alternar "A pagar"/"Pago", digitar
na busca, e trocar de mês. Cronometrei contra uma **cópia** do banco real dele (608 transações,
até 31 meses, até 48 lançamentos no mês mais cheio) pra achar a causa raiz de verdade:

| Operação | Antes |
|---|---|
| `backend_bridge.list_transactions()` (C++/pybind11, 608 linhas) | 2,9 ms — nunca foi o problema |
| `MonthSelector.update_months()` (31 meses) | 288 ms |
| `DashboardView._render_transaction_list()` (48 lançamentos) | 2537 ms |
| `refresh()` completo (toggle/troca de mês chamam isso) | ~2850 ms |
| 1 tecla na busca (só re-renderiza, sem tocar no banco) | ~894 ms |

O backend C++ não era o gargalo. `_render_transaction_list()` e `MonthSelector.update_months()`
**destruíam e recriavam todos os widgets do zero a cada chamada** — inclusive o cabeçalho de
colunas e separadores, que nunca mudam entre uma chamada e outra. `CTkButton`/`CTkLabel` são
caros de construir (cada um desenha num Canvas próprio, registra callbacks de tema) — ~8 widgets
por linha × até 48 linhas era o que levava os ~2,5s.

## Decisão

- **Cabeçalho de colunas + 2 `Divider`** (`DashboardView`) — criados uma única vez no `__init__`
  de `self._list_frame`, nunca mais tocados em `_render_transaction_list()`.
- **Pool de linhas** (`DashboardView._row_pool`) — `_render_transaction_list()` reaproveita as
  linhas já criadas (só `.configure(text=..., command=...)`, sem destruir/recriar) e só cria
  linha nova quando a lista atual precisa de mais linhas do que o pool já tem
  (`_get_or_create_row()`). Linhas sobrando de uma renderização anterior maior ficam escondidas
  (`.grid_remove()`), não destruídas — prontas pra reaparecer sem custo se a lista crescer nova.
- **`MonthSelector.update_months()`** — só reconstrói a tira de meses se o conjunto de meses
  mudou de verdade (`self._months_sorted` comparado com o novo `months`); do contrário só
  reaplica o destaque (cor) do mês selecionado nos botões já existentes
  (`self._month_buttons: dict[str, CTkButton]`), que é barato.
- **Debounce na busca** (`DashboardView._on_search_changed`) — `self.after(150, ...)`, cancelando
  o agendamento anterior a cada tecla nova (`after_cancel`); só renderiza ~150ms depois da
  última tecla, não a cada tecla.

## Verificação (mesma cópia do banco real, 48 lançamentos no mês mais cheio)

| Operação | Depois (pool "quente" — uso real após o primeiro carregamento) |
|---|---|
| `refresh()` completo (toggle/troca de mês) | **113 ms** (era ~2850 ms) |
| `MonthSelector.update_months()`, conjunto igual | **9,6 ms** (era 288 ms) |
| `refresh()` disparado por toggle de status | **64,6 ms** (era ~2815 ms) |
| Busca (debounce ativo) | dispara instantâneo, renderiza só 1x depois de parar de digitar |

## Consequências

- A primeira renderização de cada mês ainda paga o custo total de construir os widgets daquele
  tanto de linhas (pool "frio") — só a partir da segunda vez que esse número de linhas (ou menos)
  é necessário que o ganho aparece. Aceitável: os 3 casos reportados pelo usuário (toggle, busca,
  troca de mês) são exatamente os casos que **reaproveitam** o pool depois do primeiro
  carregamento da tela.
- Ao medir de novo, percebi que até um `CTkScrollableFrame` **vazio**, sem nenhum código meu,
  estava levando ~2s pra construir nesta sessão de testes (provavelmente acúmulo de horas de
  janelas Tk criadas/destruídas no mesmo display X ao longo de uma sessão de desenvolvimento
  excepcionalmente longa) — isso infla o tempo do **primeiro** carregamento do Início de um jeito
  que não tem nada a ver com esta correção, e não deve reproduzir numa sessão normal do usuário
  (processo/display novos). Não investigado a fundo por estar fora do que foi reportado.
