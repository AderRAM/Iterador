package com.finance.iterador.ui.dashboard

import android.app.DatePickerDialog
import android.content.Context
import android.widget.ArrayAdapter
import androidx.appcompat.app.AlertDialog
import com.finance.iterador.R
import com.finance.iterador.data.PT_BR
import com.finance.iterador.data.CategoryKind
import com.finance.iterador.data.TransactionStatus
import com.finance.iterador.data.TransactionType
import com.finance.iterador.data.entity.CategoryEntity
import com.finance.iterador.data.entity.TransactionEntity
import com.finance.iterador.data.parseCentsOrNull
import com.finance.iterador.databinding.DialogTransactionFormBinding
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Locale
import java.util.UUID

private val DATE_FORMAT = SimpleDateFormat("dd/MM/yyyy", PT_BR)
private val STORAGE_FORMAT = SimpleDateFormat("yyyy-MM-dd", Locale.ROOT)

/** Cria/edita um lançamento num AlertDialog — sem tela própria, igual ao diálogo modal do desktop. */
fun showTransactionFormDialog(
    context: Context,
    categories: List<CategoryEntity>,
    existing: TransactionEntity?,
    onSave: (TransactionEntity) -> Unit,
) {
    val binding = DialogTransactionFormBinding.inflate(android.view.LayoutInflater.from(context))
    val calendar = Calendar.getInstance()

    fun categoriesForKind(kind: CategoryKind) = categories.filter { it.kind == kind }

    fun bindCategorySpinner(kind: CategoryKind, selectedId: String?) {
        val options = categoriesForKind(kind)
        binding.spinnerCategory.adapter = ArrayAdapter(
            context,
            android.R.layout.simple_spinner_dropdown_item,
            options.map { it.name },
        )
        val index = options.indexOfFirst { it.id == selectedId }
        binding.spinnerCategory.setSelection(if (index >= 0) index else 0)
    }

    fun updateStatusLabel() {
        binding.switchStatus.text = context.getString(
            if (binding.switchStatus.isChecked) R.string.label_paid else R.string.label_pending
        )
    }

    binding.radioGroupType.setOnCheckedChangeListener { _, checkedId ->
        val kind = if (checkedId == binding.radioIncome.id) CategoryKind.INCOME else CategoryKind.EXPENSE
        bindCategorySpinner(kind, null)
    }
    binding.switchStatus.setOnCheckedChangeListener { _, _ -> updateStatusLabel() }

    binding.editDate.setText(DATE_FORMAT.format(calendar.time))
    binding.editDate.setOnClickListener {
        DatePickerDialog(
            context,
            { _, year, month, dayOfMonth ->
                calendar.set(year, month, dayOfMonth)
                binding.editDate.setText(DATE_FORMAT.format(calendar.time))
            },
            calendar.get(Calendar.YEAR),
            calendar.get(Calendar.MONTH),
            calendar.get(Calendar.DAY_OF_MONTH),
        ).show()
    }

    if (existing != null) {
        binding.editDescription.setText(existing.description)
        binding.editValue.setText(String.format(PT_BR, "%.2f", existing.amountCents / 100.0))
        try {
            calendar.time = STORAGE_FORMAT.parse(existing.occurredAt) ?: calendar.time
        } catch (_: Exception) {
        }
        binding.editDate.setText(DATE_FORMAT.format(calendar.time))
        val isIncome = existing.type == TransactionType.INCOME
        binding.radioGroupType.check(if (isIncome) binding.radioIncome.id else binding.radioExpense.id)
        bindCategorySpinner(if (isIncome) CategoryKind.INCOME else CategoryKind.EXPENSE, existing.categoryId)
        binding.switchStatus.isChecked = existing.status == TransactionStatus.PAID
    } else {
        bindCategorySpinner(CategoryKind.EXPENSE, null)
    }
    updateStatusLabel()

    val titleRes = if (existing == null) R.string.dialog_new_transaction else R.string.dialog_edit_transaction
    AlertDialog.Builder(context)
        .setTitle(titleRes)
        .setView(binding.root)
        .setPositiveButton(R.string.action_save) { _, _ ->
            val description = binding.editDescription.text?.toString()?.trim().orEmpty()
            val cents = parseCentsOrNull(binding.editValue.text?.toString().orEmpty())
            if (description.isEmpty() || cents == null) {
                return@setPositiveButton
            }
            val kind = if (binding.radioGroupType.checkedRadioButtonId == binding.radioIncome.id) {
                CategoryKind.INCOME
            } else {
                CategoryKind.EXPENSE
            }
            val category = categoriesForKind(kind).getOrNull(binding.spinnerCategory.selectedItemPosition)
                ?: return@setPositiveButton
            val transaction = TransactionEntity(
                id = existing?.id ?: UUID.randomUUID().toString(),
                categoryId = category.id,
                type = if (kind == CategoryKind.INCOME) TransactionType.INCOME else TransactionType.EXPENSE,
                status = if (binding.switchStatus.isChecked) TransactionStatus.PAID else TransactionStatus.PENDING,
                amountCents = cents,
                description = description,
                occurredAt = STORAGE_FORMAT.format(calendar.time),
                investmentId = existing?.investmentId,
            )
            onSave(transaction)
        }
        .setNegativeButton(R.string.action_cancel, null)
        .show()
}
