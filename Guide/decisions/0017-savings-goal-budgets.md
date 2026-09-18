# 0017 — Orçamentos viram metas de economia, não limite de gasto

Status: Aceito

## Contexto

`Budget` existia desde o scaffold inicial como "limite de gasto por categoria/período"
(`categoryId` + `limitCents` + `BudgetPeriod`), mas nunca foi implementado de verdade —
`BudgetRepository` sempre foi um stub que lançava `std::logic_error`, e a tabela `budgets` nunca
recebeu uma escrita real.

O usuário pediu algo diferente: "em orçamentos crie um sistema para incluir items, aplicar um
valor aos item e dividir o valor em determinados meses, isso é para calcular quantos meses eu
deveria acumular dinheiro para pagar algo, com a possibilidade do dinheiro estar investido
enquanto é acumulado." — ou seja, uma **meta de economia**: "quero X, tenho Y meses, quanto
preciso guardar por mês", opcionalmente vinculada a um `Investment` só como referência de onde o
dinheiro acumulado está.

Como a tabela antiga nunca teve dado real de usuário, foi seguro redesenhar o conceito do zero em
vez de conviver com os dois significados.

## Decisão

- `core::Budget` reescrito: `id`, `name`, `targetValue` (Money), `months` (int), `investmentId`
  (opcional, `""` = nenhum), `createdAt`. `BudgetPeriod` e o antigo `categoryId`/`limitCents`
  foram removidos por completo (não "descontinuados" — apagados, já que nunca chegaram a
  produção).
- **Migration 0003** (`0003_redesign_budgets_as_goals.sql`): `DROP TABLE budgets` +
  `CREATE TABLE budgets` com o schema novo. Uso de DROP+CREATE só é seguro aqui porque a tabela
  nunca recebeu escrita real (confirmado por inspeção de código antes de decidir) — **não repetir
  esse padrão** numa tabela que já tem dado de usuário; qualquer migration futura em cima de dado
  real precisa preservar linhas existentes (ALTER/migração de dado, como a 0002 fez). Testado
  simulando um banco real na versão 2 (rodando as migrations 0001+0002 de verdade) antes de abrir
  com o binário novo — confirma que o `user_version` sobe para 3 e o schema novo aparece sem erro.
- `BudgetRepository` reescrito seguindo o mesmo padrão de `InvestmentRepository`: `listAll`,
  `findById`, `create`, `update`, `remove` — cada mutação grava uma entrada em `OperationLog` com
  `entityType = "budget"`. Diferente de `InvestmentRepository` (que nunca teve `remove`),
  `Budget` ganhou `remove` desde o início, porque faz sentido cancelar/completar uma meta.
- `Application` ganhou `listBudgets`/`createBudget`/`updateBudget`/`deleteBudget`, expostos ao
  Python via `bind_app.cpp` e envolvidos em `backend_bridge.py`. `Budget` em si é bindado em
  `bind_core.cpp` com `created_at` exposto como string `"YYYY-MM-DD"` (mesmo padrão de
  `Transaction::occurred_at`, ver ADR-0011).
- UI: `BudgetsView` (lista, com "+ Nova meta") + `BudgetFormDialog` (Nome, Valor total, Meses,
  Investimento vinculado opcional via `CTkOptionMenu`). O aporte mensal necessário
  (`targetValue / months`) é calculado e mostrado ao vivo no formulário e na linha da lista — não
  fica guardado no banco, é sempre derivado dos dois campos.
- O vínculo com `Investment` é **só informativo**: criar/editar/remover uma meta não move
  nenhum valor do investimento vinculado. Quem efetivamente move o dinheiro é uma transação
  categoria "Investimento" ou "Passiva" (ADR-0012/0014) — a meta é apenas um cálculo de quanto/
  quando, e um lembrete visual de onde esse dinheiro está guardado.

## Consequências

- Nenhuma migração de dado do usuário foi necessária (tabela vazia), mas o padrão de teste
  (simular a versão anterior real antes de abrir com o código novo) foi seguido do mesmo jeito,
  por disciplina — já que da próxima vez a tabela não estará mais vazia.
- Não há nenhuma automação ligando "meta atingida" a algo — a UI não marca a meta como concluída
  nem verifica se o investimento vinculado já chegou ao valor alvo. Ficaria fácil de adicionar
  depois (comparar `investment.current_value` com `budget.target_value`), mas não foi pedido.
- Sem paginação em `listBudgets` — mesmo raciocínio do ADR-0016, volume baixo o suficiente por
  enquanto.
