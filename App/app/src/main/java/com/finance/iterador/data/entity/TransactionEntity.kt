package com.finance.iterador.data.entity

import androidx.room.Entity
import androidx.room.PrimaryKey
import com.finance.iterador.data.TransactionStatus
import com.finance.iterador.data.TransactionType

// Espelha Backend/src/core/Transaction.hpp, sem sortOrder/isRecurring nesta primeira versão
// (reordenação manual e transações fixadas ficam para uma fase futura do Android — ver Guide).
@Entity(tableName = "transactions")
data class TransactionEntity(
    @PrimaryKey val id: String,
    val categoryId: String,
    val type: TransactionType,
    val status: TransactionStatus,
    val amountCents: Long,
    val description: String,
    /** Data no formato ISO "yyyy-MM-dd". */
    val occurredAt: String,
    val investmentId: String?,
)
