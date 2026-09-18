# 0019 — Remover mês, com confirmação e desfazer em um passo só

Status: Aceito

## Contexto

Depois do ADR-0018 (navegação limitada + "+ Mês"), o usuário pediu o complemento óbvio: um jeito
de **remover** um mês também — e destacou explicitamente que precisa dar pra voltar atrás caso o
mês seja removido por acidente. Remover um mês com lançamento de verdade é destrutivo (apaga
transações reais do usuário), então merece tanto confirmação quanto desfazer — coerente com a
regra permanente de cuidado com dado de usuário no `CLAUDE.md` (ver incidente registrado em
`Guide/checklist.md`).

## Decisão

- Botão "Remover mês" na tira do `MonthSelector`, ao lado de "+ Mês" — opera sobre o mês
  atualmente selecionado (mesmo padrão do "+ Mês": ação sobre "o mês que estou vendo agora").
- Antes de remover, `ConfirmDialog` (novo, `UI/iterador_ui/widgets/confirm_dialog.py` — diálogo
  de confirmação genérico, reutilizável para outras ações destrutivas futuras) mostra quantas
  transações serão apagadas (ou avisa que é só um mês vazio, se não tiver nenhuma).
- Remover de fato apaga **todas** as transações daquele mês (`backend_bridge.delete_transaction`
  por lançamento) — não existe "mês" como entidade no backend, só transações com uma data; um
  mês "existe" na UI só como agrupamento derivado de `occurred_at[:7]`.
- Um único `RemoveMonthCommand` (novo, `transaction_commands.py`) empacota a remoção inteira —
  um só clique em "Desfazer" recria todas as transações do mês de uma vez (em vez de precisar
  desfazer lançamento por lançamento). Guarda os campos de cada transação removida (mesmo padrão
  de `DeleteTransactionCommand`) mais três coisas extras que só esse comando precisa: se o mês
  era "adicionado manualmente" (`MonthSelector.is_extra_month`), o mês vizinho pra onde a seleção
  vai depois de remover (`MonthSelector.neighbor_of`), e uma referência ao próprio
  `MonthSelector` — porque desfazer/refazer aqui não é só backend, também precisa repor/tirar o
  mês do bookkeeping local (`_extra_months`) e da seleção. É a única exceção à regra "comando não
  mexe na UI direto" do `transaction_commands.py` — documentada no docstring do módulo.
- `MonthSelector` ganhou métodos de bookkeeping pro comando usar: `is_extra_month`,
  `add_extra_month` (já existia como parte de `_add_month`, virou público), `remove_month`
  (só tira de `_extra_months`, não mexe em transação/seleção), `neighbor_of` (calcula pra onde
  ir depois de remover o mês selecionado — prefere o mês anterior, senão o próximo, senão o mês
  atual), `force_select` (troca o mês selecionado sem disparar `on_select`, já que quem chama
  sempre segue com `refresh()` de qualquer forma).

## Consequências

- Remover um mês que tem lançamento é uma ação em lote (N deletes) — cada delete já grava sua
  própria entrada em `operation_log` no backend (nada novo aqui, é o mesmo `deleteTransaction`
  de sempre), só o desfazer do lado da UI que trata como uma unidade.
- Não existe hoje limite de quantas transações um "Remover mês" pode apagar de uma vez — pra um
  mês com centenas de lançamentos isso significa centenas de chamadas síncronas ao backend antes
  de devolver o controle pra UI. Sem problema no volume atual (uso pessoal), mas não é assíncrono.
- Igual ao ADR-0018: o bookkeeping de "mês adicionado manualmente" não persiste — some se o
  usuário trocar de aba e voltar (a `DashboardView` inteira é recriada). O `RemoveMonthCommand`
  guarda uma referência ao `MonthSelector` da instância viva no momento da remoção; se a view for
  recriada antes de desfazer, essa referência fica presa à instância antiga (não é mais a que
  está na tela) — na prática improvável de acontecer (undo/redo ficam na mesma `DashboardView`
  que tem o próprio `_undo_stack`), mas vale registrar como limitação conhecida.
