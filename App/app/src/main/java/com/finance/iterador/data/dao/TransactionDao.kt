package com.finance.iterador.data.dao

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Embedded
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import com.finance.iterador.data.entity.TransactionEntity
import kotlinx.coroutines.flow.Flow

/** Lançamento + nome da categoria (via JOIN), pronto para exibir na lista — sem consulta extra. */
data class TransactionWithCategory(
    @Embedded val transaction: TransactionEntity,
    val categoryName: String,
)

@Dao
interface TransactionDao {
    @Query(
        """
        SELECT t.*, c.name AS categoryName
        FROM transactions t
        JOIN categories c ON c.id = t.categoryId
        ORDER BY t.occurredAt DESC, t.id DESC
        """
    )
    fun observeAllWithCategory(): Flow<List<TransactionWithCategory>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(transaction: TransactionEntity)

    @Update
    suspend fun update(transaction: TransactionEntity)

    @Delete
    suspend fun delete(transaction: TransactionEntity)

    @Query("SELECT * FROM transactions WHERE investmentId = :investmentId")
    suspend fun listByInvestment(investmentId: String): List<TransactionEntity>

    @Query("UPDATE transactions SET investmentId = NULL WHERE investmentId = :investmentId")
    suspend fun clearInvestmentLink(investmentId: String)
}
