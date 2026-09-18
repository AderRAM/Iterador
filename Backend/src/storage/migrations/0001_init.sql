-- Migration 0001: schema inicial do Iterador.
-- Nunca editar uma migration já aplicada em produção — crie 0002_*.sql para mudanças futuras
-- e registre o passo em Database::runMigrations() (Backend/src/storage/Database.cpp).

-- Não existe conceito de "conta" no Iterador — carteira única e implícita. Dinheiro (saldo
-- líquido, derivado das transações) e Investimentos são os dois lugares onde o valor do
-- usuário fica. Ver Guide/decisions/0007-remove-account-add-investment.md.
CREATE TABLE IF NOT EXISTS investments (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    current_value_cents INTEGER NOT NULL,
    currency TEXT NOT NULL,
    yield_rate REAL NOT NULL DEFAULT 0,
    fees_rate REAL NOT NULL DEFAULT 0,
    selic_percentage REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS categories (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    kind TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY,
    category_id TEXT NOT NULL REFERENCES categories(id),
    type TEXT NOT NULL,
    -- "PENDING" (a pagar/a receber) ou "PAID" (pago/recebido) — ver core::TransactionStatus.
    status TEXT NOT NULL DEFAULT 'PENDING',
    amount_cents INTEGER NOT NULL,
    currency TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    occurred_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS budgets (
    id TEXT PRIMARY KEY,
    category_id TEXT NOT NULL REFERENCES categories(id),
    limit_cents INTEGER NOT NULL,
    currency TEXT NOT NULL,
    period TEXT NOT NULL
);

-- Base do sync P2P (ver Guide/architecture.md): toda mutação nas tabelas acima também grava
-- uma entrada aqui. O módulo sync/ lê e escreve só nesta tabela, nunca nas de domínio direto.
CREATE TABLE IF NOT EXISTS operation_log (
    op_id TEXT PRIMARY KEY,
    device_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    op_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    hlc TEXT NOT NULL,
    applied_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_operation_log_hlc ON operation_log(hlc);
