-- Migration 0003: redesenha "budgets" de limite de gasto por categoria (nunca chegou a ser
-- implementado — BudgetRepository sempre foi stub, tabela nunca recebeu escrita) para meta de
-- economia (ver Guide/decisions/0017-savings-goal-budgets.md). Seguro fazer DROP+CREATE aqui
-- porque não existe dado real na tabela antiga — não repita esse padrão numa tabela que já tem
-- dado de usuário.

DROP TABLE IF EXISTS budgets;

CREATE TABLE budgets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    target_value_cents INTEGER NOT NULL,
    currency TEXT NOT NULL,
    months INTEGER NOT NULL,
    investment_id TEXT REFERENCES investments(id),
    created_at TEXT NOT NULL
);
