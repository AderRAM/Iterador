package com.finance.iterador.data.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "investments")
data class InvestmentEntity(
    @PrimaryKey val id: String,
    val name: String,
    val type: String,
    val currentValueCents: Long,
    val yieldRate: Double = 0.0,
    val feesRate: Double = 0.0,
    val selicPercentage: Double = 0.0,
)
