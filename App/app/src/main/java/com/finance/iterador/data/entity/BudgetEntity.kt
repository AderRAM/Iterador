package com.finance.iterador.data.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

/** Meta de economia (aba "Orçamentos" na UI desktop) — ver Backend/src/core/Budget.hpp/ADR-0017. */
@Entity(tableName = "budgets")
data class BudgetEntity(
    @PrimaryKey val id: String,
    val name: String,
    val targetValueCents: Long,
    val months: Int,
    val investmentId: String?,
    /** Data no formato ISO "yyyy-MM-dd". */
    val createdAt: String,
)
