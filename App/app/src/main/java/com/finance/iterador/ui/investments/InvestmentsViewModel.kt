package com.finance.iterador.ui.investments

import androidx.lifecycle.LiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.asLiveData
import androidx.lifecycle.viewModelScope
import com.finance.iterador.data.FinanceRepository
import com.finance.iterador.data.entity.InvestmentEntity
import kotlinx.coroutines.launch

class InvestmentsViewModel(private val repository: FinanceRepository) : ViewModel() {

    val investments: LiveData<List<InvestmentEntity>> = repository.observeInvestments().asLiveData()

    fun save(investment: InvestmentEntity) {
        viewModelScope.launch { repository.saveInvestment(investment) }
    }

    fun update(investment: InvestmentEntity) {
        viewModelScope.launch { repository.updateInvestment(investment) }
    }

    fun delete(investment: InvestmentEntity) {
        viewModelScope.launch { repository.deleteInvestment(investment) }
    }
}
