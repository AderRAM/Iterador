# 0007 — Remover o modelo de múltiplas contas, adicionar Investimento

Status: Aceito

## Contexto

A fase inicial do Iterador foi implementada com um modelo de múltiplas contas (`Account`),
inspirado em apps de finanças genéricos: `AccountType` incluía Conta corrente, Poupança,
Dinheiro, Cartão de Crédito e Investimento, com CRUD completo e tela própria na UI.

O usuário corrigiu esse escopo: **não existe conceito de "conta" no Iterador**. Existe uma
carteira única e implícita do usuário. O valor do usuário fica em dois lugares:

1. **Dinheiro** — saldo líquido (ainda não modelado como entidade própria — ver Roadmap).
2. **Investimentos** — cada um nomeado pelo usuário, com tipo definido por ele (texto livre,
   ex. "Renda fixa", "Ações"), rentabilidade, taxas e um percentual relativo à Selic/CDI (comum
   em renda fixa brasileira).

Cartão de Crédito e Investimento **não são tipos de conta** — investimento é uma entidade
própria (rica, com os campos acima), e cartão de crédito não faz parte do escopo atual.

## Decisão

- Remover por completo `core::Account`, `core::AccountType`, `storage::AccountRepository`, os
  bindings pybind11 correspondentes, e a tela/diálogo de Contas na UI.
- Remover a coluna `account_id` de `transactions` — transações não pertencem a uma conta, só a
  uma categoria (ver Roadmap sobre como isso deveria afetar Dinheiro vs. um Investimento).
- Adicionar `core::Investment` (campos: `name`, `type` como texto livre, `currentValue`,
  `yieldRate`, `feesRate`, `selicPercentage`) e `storage::InvestmentRepository`, implementado de
  ponta a ponta como a nova "fatia de referência" (substituindo o papel que `AccountRepository`
  tinha).
- A tela "Contas" na UI vira "Investimentos" (`InvestmentsView` + `InvestmentFormDialog`).

## Consequências

- O formato exato de `yieldRate`/`feesRate`/`selicPercentage` (ao ano? ao mês? "% do CDI"?) é um
  primeiro rascunho — documentado como ponto em aberto no Roadmap, a confirmar com o usuário.
- `TransactionType::Transfer` deixa de fazer sentido como "transferência entre contas". Passa a
  representar movimento entre Dinheiro e um Investimento (ex. "Saque investimento" na planilha
  do usuário) — mas `Transaction` ainda não tem um campo para referenciar qual `Investment`;
  fica como TODO explícito no código e no Roadmap.
- "Dinheiro" (saldo líquido) ainda não tem representação própria no modelo — hoje é só um
  conceito mencionado, sem tabela/entidade. Fica para quando `TransactionRepository` for
  implementado de verdade (o saldo provavelmente será derivado das transações, não uma entidade
  separada como Investment).
