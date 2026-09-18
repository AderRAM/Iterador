# 0011 — Data editável em Transaction + lista em colunas de verdade

Status: Aceito

## Contexto

Duas lacunas apontadas pelo usuário:

1. `Transaction.occurredAt` existia no C++ mas nunca era exposto ao Python (`bind_core.cpp` não
   serializava `Timestamp`) nem editável na UI — toda transação ficava com a data/hora exata de
   quando foi criada, sem jeito de mudar.
2. A lista de lançamentos na aba Início (ver
   [ADR-0010](0010-dashboard-hosts-transactions.md)) usava `pack()` com cada linha numa
   `CTkFrame` independente — os botões "Editar"/"Remover" e o valor ficavam desalinhados entre
   linhas porque a largura do texto do valor variava (`R$ -15,00` vs `R$ 3.000,00`), empurrando
   os elementos vizinhos.

Também foi pedido um botão na própria linha pra alternar rapidamente entre pago/a pagar, sem
abrir o formulário de edição inteiro — `TransactionRepository::setStatus()` já existia no C++
mas nunca tinha ganhado binding pybind11 nem UI.

## Decisão

- `core::Timestamp` ganhou `fromDateString("YYYY-MM-DD")` (meio-dia UTC, pra não sofrer com
  virada de dia por fuso horário) em `Timestamp.hpp`.
- `Transaction` no pybind11 (`bind_core.cpp`) expõe `occurred_at` como string `"YYYY-MM-DD"`
  (via `def_property_readonly` com lambda — não expõe o tipo `Timestamp` inteiro).
- `TransactionRepository::create`/`update` (e `Application::createTransaction`/
  `updateTransaction`) passam a receber `occurredAtDate` explícito em vez de sempre usar
  `core::now()`. Quem decide o valor padrão (dia atual) é a **UI**
  (`TransactionFormDialog`), não o backend — o campo "Data" do formulário já vem preenchido com
  `datetime.date.today()`, formato `DD/MM/AAAA`, e o usuário pode editar livremente antes de
  salvar.
- Novo binding `Application::setTransactionStatus` / `set_transaction_status` — usado por um
  botão na própria linha da lista (`DashboardView`) que mostra "Pago" ou "A pagar" e alterna com
  um clique, sem abrir o formulário.
- `DashboardView` trocou `pack()` por `grid()` para a lista de lançamentos: `_list_frame` vira um
  container de grade com colunas fixas (Data, Descrição, Status, Valor, Editar, Remover); a
  coluna Valor tem `width=100` fixo com `anchor="e"`, garantindo que todas as linhas alinhem
  verticalmente independente de quantos dígitos o valor tiver. A coluna Descrição usa
  `grid_columnconfigure(1, weight=1)` pra ocupar o espaço sobrando.

## Consequências

- `occurred_at` só carrega data (sem hora) — suficiente pro caso de uso atual (não há
  agendamento por horário). Se precisar de hora no futuro, isso vai exigir expor mais que
  `.substr(0, 10)` no binding.
- O botão de status na lista e o switch "Já foi pago/recebido" no formulário de edição podem
  ficar temporariamente inconsistentes até o próximo `refresh()` — não é um problema real porque
  ambos chamam `refresh()` logo em seguida, mas vale registrar que não há um único "dono" da
  fonte de verdade do widget, só do banco.
- O layout em grade da lista não tem mais o cartão arredondado/bordado por linha que existia
  antes (via `CTkFrame` com `corner_radius`) — trocado por linhas simples de grade, porque não
  dá pra ter bordas por linha E alinhamento de coluna garantido entre `CTkFrame`s independentes
  ao mesmo tempo (cada `CTkFrame` teria seu próprio sistema de grid/pack isolado).
