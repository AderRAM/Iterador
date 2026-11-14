package com.finance.iterador.data

import com.finance.iterador.data.dao.TransactionWithCategory
import com.finance.iterador.data.entity.BudgetEntity
import com.finance.iterador.data.entity.CategoryEntity
import com.finance.iterador.data.entity.InvestmentEntity
import com.finance.iterador.data.entity.TransactionEntity
import kotlinx.coroutines.flow.Flow

/**
 * Única classe que os ViewModels tocam para ler/gravar dados — espelha o papel de
 * `Application` (fachada C++) na UI desktop, mas aqui é só uma camada fina sobre o Room: o
 * Android ainda tem seu próprio banco local, sem sync com o Backend/desktop (ver Guide).
 */
class FinanceRepository(private val db: AppDatabase) {

    fun observeCategories(): Flow<List<CategoryEntity>> = db.categoryDao().observeAll()

    suspend fun listCategories(): List<CategoryEntity> = db.categoryDao().listAll()

    fun observeTransactions(): Flow<List<TransactionWithCategory>> =
        db.transactionDao().observeAllWithCategory()

    suspend fun saveTransaction(transaction: TransactionEntity) {
        db.transactionDao().upsert(transaction)
        adjustInvestmentIfNeeded(transaction, revert = false)
    }

    suspend fun updateTransaction(old: TransactionEntity, updated: TransactionEntity) {
        adjustInvestmentIfNeeded(old, revert = true)
        db.transactionDao().update(updated)
        adjustInvestmentIfNeeded(updated, revert = false)
    }

    suspend fun deleteTransaction(transaction: TransactionEntity) {
        db.transactionDao().delete(transaction)
        adjustInvestmentIfNeeded(transaction, revert = true)
    }

    // Categoria "Investimento" ajusta o valor do Investment vinculado (ver ADR-0012 no desktop) —
    // Receita/Transfer somam, Despesa subtrai; revert desfaz o efeito anterior antes de reaplicar.
    private suspend fun adjustInvestmentIfNeeded(transaction: TransactionEntity, revert: Boolean) {
        val investmentId = transaction.investmentId ?: return
        val investment = db.investmentDao().listAll().find { it.id == investmentId } ?: return
        val signedDelta = when (transaction.type) {
            TransactionType.EXPENSE -> -transaction.amountCents
            TransactionType.INCOME, TransactionType.TRANSFER -> transaction.amountCents
        }
        val delta = if (revert) -signedDelta else signedDelta
        db.investmentDao().update(investment.copy(currentValueCents = investment.currentValueCents + delta))
    }

    fun observeInvestments(): Flow<List<InvestmentEntity>> = db.investmentDao().observeAll()

    suspend fun saveInvestment(investment: InvestmentEntity) = db.investmentDao().upsert(investment)

    suspend fun updateInvestment(investment: InvestmentEntity) = db.investmentDao().update(investment)

    suspend fun deleteInvestment(investment: InvestmentEntity) {
        db.transactionDao().clearInvestmentLink(investment.id)
        db.budgetDao().clearInvestmentLink(investment.id)
        db.investmentDao().delete(investment)
    }

    fun observeBudgets(): Flow<List<BudgetEntity>> = db.budgetDao().observeAll()

    suspend fun saveBudget(budget: BudgetEntity) = db.budgetDao().upsert(budget)

    suspend fun updateBudget(budget: BudgetEntity) = db.budgetDao().update(budget)

    suspend fun deleteBudget(budget: BudgetEntity) = db.budgetDao().delete(budget)
}
