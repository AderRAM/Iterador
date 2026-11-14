package com.finance.iterador.ui.dashboard

import androidx.lifecycle.LiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.asLiveData
import androidx.lifecycle.viewModelScope
import com.finance.iterador.data.FinanceRepository
import com.finance.iterador.data.TransactionStatus
import com.finance.iterador.data.TransactionType
import com.finance.iterador.data.dao.TransactionWithCategory
import com.finance.iterador.data.entity.CategoryEntity
import com.finance.iterador.data.entity.TransactionEntity
import kotlinx.coroutines.launch

class DashboardViewModel(private val repository: FinanceRepository) : ViewModel() {

    val transactions: LiveData<List<TransactionWithCategory>> =
        repository.observeTransactions().asLiveData()

    val categories: LiveData<List<CategoryEntity>> =
        repository.observeCategories().asLiveData()

    fun save(transaction: TransactionEntity) {
        viewModelScope.launch { repository.saveTransaction(transaction) }
    }

    fun update(old: TransactionEntity, updated: TransactionEntity) {
        viewModelScope.launch { repository.updateTransaction(old, updated) }
    }

    fun delete(transaction: TransactionEntity) {
        viewModelScope.launch { repository.deleteTransaction(transaction) }
    }

    fun toggleStatus(entry: TransactionWithCategory) {
        val current = entry.transaction
        val toggled = current.copy(
            status = if (current.status == TransactionStatus.PAID) {
                TransactionStatus.PENDING
            } else {
                TransactionStatus.PAID
            }
        )
        update(current, toggled)
    }

    companion object {
        fun totals(entries: List<TransactionWithCategory>): Triple<Long, Long, Long> {
            var income = 0L
            var expense = 0L
            for (entry in entries) {
                when (entry.transaction.type) {
                    TransactionType.INCOME -> income += entry.transaction.amountCents
                    TransactionType.EXPENSE -> expense += entry.transaction.amountCents
                    TransactionType.TRANSFER -> Unit
                }
            }
            return Triple(income, expense, income - expense)
        }
    }
}
