package com.finance.iterador

import android.app.Application
import com.finance.iterador.data.AppDatabase
import com.finance.iterador.data.FinanceRepository

class IteradorApplication : Application() {
    val repository: FinanceRepository by lazy {
        FinanceRepository(AppDatabase.getInstance(this))
    }
}
