package com.finance.iterador.ui.budgets

import androidx.lifecycle.LiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.asLiveData
import androidx.lifecycle.viewModelScope
import com.finance.iterador.data.FinanceRepository
import com.finance.iterador.data.entity.BudgetEntity
import com.finance.iterador.data.entity.InvestmentEntity
import kotlinx.coroutines.launch

class BudgetsViewModel(private val repository: FinanceRepository) : ViewModel() {

    val budgets: LiveData<List<BudgetEntity>> = repository.observeBudgets().asLiveData()
    val investments: LiveData<List<InvestmentEntity>> = repository.observeInvestments().asLiveData()

    fun save(budget: BudgetEntity) {
        viewModelScope.launch { repository.saveBudget(budget) }
    }

    fun update(budget: BudgetEntity) {
        viewModelScope.launch { repository.updateBudget(budget) }
    }

    fun delete(budget: BudgetEntity) {
        viewModelScope.launch { repository.deleteBudget(budget) }
    }
}
