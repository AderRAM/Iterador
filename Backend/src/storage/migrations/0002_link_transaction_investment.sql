-- Migration 0002: liga uma transação a um investimento (opcional). Quando presente, a
-- transação influencia o valor atual do investimento (ver core::Transaction::investmentId e
-- Application::createTransaction/updateTransaction/deleteTransaction).
-- Nunca editar 0001_init.sql — usuários já migraram pra versão 1. Próximas mudanças de schema
-- entram como 0003, 0004... e um bloco novo em Database::runMigrations().

ALTER TABLE transactions ADD COLUMN investment_id TEXT REFERENCES investments(id);
