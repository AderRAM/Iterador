-- Migration 0004: ordem manual de exibição dos lançamentos (arrastar pra cima/baixo na lista,
-- ver Guide/decisions/0033-transaction-manual-reorder.md). Maior sort_order = aparece mais acima
-- (substitui occurred_at DESC como critério principal de TransactionRepository::listAll).
-- Nunca editar 0001/0002/0003 — usuários já migraram. Próximas mudanças de schema entram como
-- 0005_*.sql e um bloco novo em Database::runMigrations().

ALTER TABLE transactions ADD COLUMN sort_order REAL NOT NULL DEFAULT 0;

-- Backfill: reproduz a ordem visual de antes (mais recente primeiro, empate por ordem de
-- inserção) pra ninguém ver a lista "embaralhar" no primeiro uso depois do update.
WITH ranked AS (
    SELECT id, ROW_NUMBER() OVER (ORDER BY occurred_at ASC, rowid ASC) AS rn
    FROM transactions
)
UPDATE transactions
SET sort_order = (SELECT rn FROM ranked WHERE ranked.id = transactions.id);
