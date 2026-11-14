package com.finance.iterador.ui.budgets

import android.content.Context
import android.text.Editable
import android.text.TextWatcher
import android.view.LayoutInflater
import android.widget.ArrayAdapter
import androidx.appcompat.app.AlertDialog
import com.finance.iterador.R
import com.finance.iterador.data.PT_BR
import com.finance.iterador.data.entity.BudgetEntity
import com.finance.iterador.data.entity.InvestmentEntity
import com.finance.iterador.data.formatCents
import com.finance.iterador.data.parseCentsOrNull
import com.finance.iterador.databinding.DialogBudgetFormBinding
import java.text.SimpleDateFormat
import java.util.Locale
import java.util.UUID

private val STORAGE_FORMAT = SimpleDateFormat("yyyy-MM-dd", Locale.ROOT)

fun showBudgetFormDialog(
    context: Context,
    investments: List<InvestmentEntity>,
    existing: BudgetEntity?,
    onSave: (BudgetEntity) -> Unit,
) {
    val binding = DialogBudgetFormBinding.inflate(LayoutInflater.from(context))

    val investmentNames = listOf(context.getString(R.string.option_none)) + investments.map { it.name }
    binding.spinnerInvestment.adapter =
        ArrayAdapter(context, android.R.layout.simple_spinner_dropdown_item, investmentNames)

    fun updatePreview() {
        val cents = parseCentsOrNull(binding.editValue.text?.toString().orEmpty()) ?: 0L
        val months = binding.editMonths.text?.toString()?.toIntOrNull() ?: 0
        val monthly = if (months > 0) cents / months else 0
        binding.textContributionPreview.text =
            context.getString(R.string.label_monthly_contribution, formatCents(monthly))
    }

    val watcher = object : TextWatcher {
        override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) = Unit
        override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) = updatePreview()
        override fun afterTextChanged(s: Editable?) = Unit
    }
    binding.editValue.addTextChangedListener(watcher)
    binding.editMonths.addTextChangedListener(watcher)

    if (existing != null) {
        binding.editName.setText(existing.name)
        binding.editValue.setText(String.format(PT_BR, "%.2f", existing.targetValueCents / 100.0))
        binding.editMonths.setText(existing.months.toString())
        val index = investments.indexOfFirst { it.id == existing.investmentId }
        binding.spinnerInvestment.setSelection(if (index >= 0) index + 1 else 0)
    } else {
        binding.editMonths.setText("1")
    }
    updatePreview()

    val titleRes = if (existing == null) R.string.dialog_new_budget else R.string.dialog_edit_budget
    AlertDialog.Builder(context)
        .setTitle(titleRes)
        .setView(binding.root)
        .setPositiveButton(R.string.action_save) { _, _ ->
            val name = binding.editName.text?.toString()?.trim().orEmpty()
            val cents = parseCentsOrNull(binding.editValue.text?.toString().orEmpty())
            val months = binding.editMonths.text?.toString()?.toIntOrNull()
            if (name.isEmpty() || cents == null || months == null || months <= 0) {
                return@setPositiveButton
            }
            val selectedPosition = binding.spinnerInvestment.selectedItemPosition
            val investmentId = if (selectedPosition == 0) null else investments[selectedPosition - 1].id
            onSave(
                BudgetEntity(
                    id = existing?.id ?: UUID.randomUUID().toString(),
                    name = name,
                    targetValueCents = cents,
                    months = months,
                    investmentId = investmentId,
                    createdAt = existing?.createdAt ?: STORAGE_FORMAT.format(java.util.Date()),
                )
            )
        }
        .setNegativeButton(R.string.action_cancel, null)
        .show()
}
