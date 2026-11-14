package com.finance.iterador.data

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.TypeConverters
import androidx.sqlite.db.SupportSQLiteDatabase
import com.finance.iterador.data.dao.BudgetDao
import com.finance.iterador.data.dao.CategoryDao
import com.finance.iterador.data.dao.InvestmentDao
import com.finance.iterador.data.dao.TransactionDao
import com.finance.iterador.data.entity.BudgetEntity
import com.finance.iterador.data.entity.CategoryEntity
import com.finance.iterador.data.entity.InvestmentEntity
import com.finance.iterador.data.entity.TransactionEntity
import java.util.UUID
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

@Database(
    entities = [
        CategoryEntity::class,
        TransactionEntity::class,
        InvestmentEntity::class,
        BudgetEntity::class,
    ],
    version = 1,
    exportSchema = true,
)
@TypeConverters(Converters::class)
abstract class AppDatabase : RoomDatabase() {
    abstract fun categoryDao(): CategoryDao
    abstract fun transactionDao(): TransactionDao
    abstract fun investmentDao(): InvestmentDao
    abstract fun budgetDao(): BudgetDao

    companion object {
        @Volatile
        private var instance: AppDatabase? = null

        fun getInstance(context: Context): AppDatabase {
            return instance ?: synchronized(this) {
                instance ?: build(context).also { instance = it }
            }
        }

        private fun build(context: Context): AppDatabase {
            return Room.databaseBuilder(
                context.applicationContext,
                AppDatabase::class.java,
                "iterador.db",
            )
                .addCallback(object : RoomDatabase.Callback() {
                    override fun onCreate(db: SupportSQLiteDatabase) {
                        super.onCreate(db)
                        // As 5 categorias fixas do desktop (ver ADR-0012/0014) — categorias
                        // personalizadas ficam para uma fase futura do Android (ver Guide).
                        CoroutineScope(Dispatchers.IO).launch {
                            getInstance(context).categoryDao().insertAll(
                                listOf(
                                    CategoryEntity(UUID.randomUUID().toString(), FixedCategories.ESSENCIAL, CategoryKind.EXPENSE),
                                    CategoryEntity(UUID.randomUUID().toString(), FixedCategories.LAZER, CategoryKind.EXPENSE),
                                    CategoryEntity(UUID.randomUUID().toString(), FixedCategories.INVESTIMENTO, CategoryKind.EXPENSE),
                                    CategoryEntity(UUID.randomUUID().toString(), FixedCategories.ATIVA, CategoryKind.INCOME),
                                    CategoryEntity(UUID.randomUUID().toString(), FixedCategories.PASSIVA, CategoryKind.INCOME),
                                )
                            )
                        }
                    }
                })
                .build()
        }
    }
}
