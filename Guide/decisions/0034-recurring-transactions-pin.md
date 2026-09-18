# 0034 — Transações fixadas/recorrentes (ícone de pin)

Status: Aceito

## Contexto

Item já no roadmap (`Guide/checklist.md`): "tornar transações recorrentes para aparecer
automaticamente no próximo mês criado". O usuário pediu especificamente um ícone de pin (assets
`Pin-on.png`/`Pin-off.png`, fornecidos por ele) em cada lançamento, entre Data e Descrição: clicar
fixa a transação (ícone azul) — a partir daí, toda vez que um mês novo é criado ("+ Mês"), a
transação fixada é clonada automaticamente pra dentro dele. Clicar de novo desfixa (ícone cinza).

## Decisão: `sort_order`-like — um `UPDATE` fino, sem lógica de negócio no C++

Nova coluna `transactions.is_recurring INTEGER` (migration `0005_add_transaction_recurring_flag.sql`,
nunca editar 0001-0004 — ver CLAUDE.md). `TransactionRepository::updateRecurring`/
`Application::updateTransactionRecurring`/`backend_bridge.update_transaction_recurring` seguem
exatamente o formato de `updateSortOrder()`/`setStatus()` — só grava a marca, sem decidir nada.
Toda a lógica de "o que fazer quando um mês é criado" mora na UI (Python), que já sabe quais
transações estão fixadas via `list_transactions()` — mesmo princípio de ADR-0033 (a UI decide, o
C++ só persiste).

## Decisão: o clone NÃO nasce fixado — só o original é o "molde"

Se o clone também nascesse fixado, cada mês novo acumularia mais uma cópia fixada da mesma
transação (mês 1 tem 1 fixada → mês 2 clona 1 → mas agora há 2 fixadas → mês 3 clonaria as 2,
duplicando). Mantendo o clone SEMPRE não-fixado, só a transação ORIGINAL que o usuário
efetivamente marcou continua sendo clonada, indefinidamente, sem nunca duplicar. Efeito prático:
se o usuário quer mudar o valor do "molde" pra frente (ex. aluguel reajustou), precisa editar (ou
refixar) a transação que está de fato fixada — editar só um clone de um mês específico não afeta
os meses futuros. Aceito como escopo simples de v1 (não é um sistema de "grupos recorrentes"
completo).

## Decisão: dia do mês, status e vínculo do clone

- **Dia**: mesmo dia do mês do original, ajustado (`calendar.monthrange`) se o mês novo tiver
  menos dias (ex. original no dia 30, mês novo é fevereiro de 28 dias → cai no dia 28).
- **Status**: sempre "A pagar" (`PENDING`) — é uma cobrança nova daquele mês, nunca herda "Pago"
  do original.
- **Categoria/tipo/valor/investimento vinculado**: copiados exatamente do original.

## Decisão: onde o gancho entra — `MonthSelector.on_add_month`

`MonthSelector` ganhou um callback opcional `on_add_month(month_str)`, chamado em `_add_month`
**antes** de `add_extra_month()`/`_select()` — assim, `DashboardView._on_month_added` (quem
realmente clona as transações) ainda consegue ler `month_selector.selected_month()` como "o mês
anterior" (pro desfazer), sem precisar que `MonthSelector` saiba nada de transações/backend (ele
continua só bookkeeping de UI, mesmo princípio já usado por `on_remove_month`, ver ADR-0019).

Sem transação fixada nenhuma, `_on_month_added` não faz nada e não empilha desfazer — "+ Mês"
continua exatamente como antes pra quem nunca usa pin. Com pelo menos uma clonagem,
`AddMonthCommand` (`transaction_commands.py`) empilha TODAS as criações + o bookkeeping do mês
(extra month/seleção) num único item — inversa exata de `RemoveMonthCommand` (ADR-0019): desfazer
"+ Mês" remove o mês E todos os clones dele de uma vez, não lançamento por lançamento.

## UI: nova coluna entre Data e Descrição

`_COLUMN_HEADERS`/`_ROW_GRID_SPEC` ganharam uma entrada `"pin"` na coluna 2 (sem cabeçalho, igual
`handle`/`edit`/`remove`) — todo `column=N` de `description` em diante desloca +1 (mesma mecânica
já usada em ADR-0033 pra inserir a alça de arrastar). Ícones `Pin-on.png`/`Pin-off.png`
(fornecidos pelo usuário, pretos na origem) recoloridos em tempo de execução com `_tinted()` (já
existente, ver ADR-0033): azul fixo (`theme.INDIGO`, cor de destaque já usada no resto do app,
sem inventar tom novo) quando ligado, mesmo cinza claro/escuro adaptativo da alça de arrastar
quando desligado.

## Consequências

- Editar um lançamento fixado pelo formulário normal não desfixa nem refixa — `is_recurring`
  fica de fora de `update_transaction` (igual `sort_order`), só o botão de pin muda essa marca.
- Não há indicação visual de "este lançamento é um clone de um fixado" — o clone parece um
  lançamento normal (não fixado) depois de criado; aceito por ora.
- Testado (Xvfb, sem interação humana): fixar/desfixar com desfazer/refazer, clonagem com ajuste
  de dia em mês mais curto, desfazer "+ Mês" removendo todos os clones de uma vez, e a coluna
  nova não quebra nenhum mecanismo do arrasto (ADR-0033).
