package com.finance.iterador.ui.investments

import android.content.Context
import android.view.LayoutInflater
import androidx.appcompat.app.AlertDialog
import com.finance.iterador.R
import com.finance.iterador.data.PT_BR
import com.finance.iterador.data.entity.InvestmentEntity
import com.finance.iterador.data.parseCentsOrNull
import com.finance.iterador.databinding.DialogInvestmentFormBinding
import java.util.Locale
import java.util.UUID

fun showInvestmentFormDialog(
    context: Context,
    existing: InvestmentEntity?,
    onSave: (InvestmentEntity) -> Unit,
) {
    val binding = DialogInvestmentFormBinding.inflate(LayoutInflater.from(context))
    if (existing != null) {
        binding.editName.setText(existing.name)
        binding.editType.setText(existing.type)
        binding.editValue.setText(String.format(PT_BR, "%.2f", existing.currentValueCents / 100.0))
    }

    val titleRes = if (existing == null) R.string.dialog_new_investment else R.string.dialog_edit_investment
    AlertDialog.Builder(context)
        .setTitle(titleRes)
        .setView(binding.root)
        .setPositiveButton(R.string.action_save) { _, _ ->
            val name = binding.editName.text?.toString()?.trim().orEmpty()
            val type = binding.editType.text?.toString()?.trim().orEmpty()
            val cents = parseCentsOrNull(binding.editValue.text?.toString().orEmpty()) ?: 0L
            if (name.isEmpty()) {
                return@setPositiveButton
            }
            onSave(
                InvestmentEntity(
                    id = existing?.id ?: UUID.randomUUID().toString(),
                    name = name,
                    type = type,
                    currentValueCents = cents,
                    yieldRate = existing?.yieldRate ?: 0.0,
                    feesRate = existing?.feesRate ?: 0.0,
                    selicPercentage = existing?.selicPercentage ?: 0.0,
                )
            )
        }
        .setNegativeButton(R.string.action_cancel, null)
        .show()
}
