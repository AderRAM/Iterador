package com.finance.iterador.data

// Espelha (conceitualmente, não byte-a-byte) os enums de Backend/src/core/ — ver
// Guide/decisions/0048-android-basic-functions.md. O Android ainda não fala o protocolo de sync,
// então este é um modelo local próprio até o dia em que sync/ estiver pronto dos dois lados.

enum class CategoryKind {
    INCOME,
    EXPENSE,
}

enum class TransactionType {
    INCOME,
    EXPENSE,
    TRANSFER,
}

enum class TransactionStatus {
    PENDING,
    PAID,
}

/** Nomes das categorias fixas — mesmos 5 nomes usados na UI desktop (ver ADR-0012/0014). */
object FixedCategories {
    const val ESSENCIAL = "Essencial"
    const val LAZER = "Lazer"
    const val INVESTIMENTO = "Investimento"
    const val ATIVA = "Ativa"
    const val PASSIVA = "Passiva"
}
