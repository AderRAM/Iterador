package com.finance.iterador.data.entity

import androidx.room.Entity
import androidx.room.PrimaryKey
import com.finance.iterador.data.CategoryKind

@Entity(tableName = "categories")
data class CategoryEntity(
    @PrimaryKey val id: String,
    val name: String,
    val kind: CategoryKind,
)
