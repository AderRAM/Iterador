-- Migration 0005: marca uma transação como "fixada"/recorrente (ícone de pin na lista, ver
-- Guide/decisions/0034-recurring-transactions-pin.md) — ao criar um mês novo ("+ Mês"), toda
-- transação com essa marca é clonada automaticamente pro mês novo (o clone em si NÃO nasce
-- fixado, só o original continua sendo o "molde" — evita duplicar a cada mês novo).
-- Nunca editar 0001-0004 — usuários já migraram. Próximas mudanças de schema entram como
-- 0006_*.sql e um bloco novo em Database::runMigrations().

ALTER TABLE transactions ADD COLUMN is_recurring INTEGER NOT NULL DEFAULT 0;
