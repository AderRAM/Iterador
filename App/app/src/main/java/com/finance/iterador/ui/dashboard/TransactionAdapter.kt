package com.finance.iterador.ui.dashboard

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.core.content.ContextCompat
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.finance.iterador.R
import com.finance.iterador.data.PT_BR
import com.finance.iterador.data.TransactionStatus
import com.finance.iterador.data.TransactionType
import com.finance.iterador.data.dao.TransactionWithCategory
import com.finance.iterador.data.formatCents
import com.finance.iterador.databinding.ItemTransactionBinding
import java.text.SimpleDateFormat
import java.util.Locale

class TransactionAdapter(
    private val onClick: (TransactionWithCategory) -> Unit,
    private val onLongClick: (TransactionWithCategory) -> Unit,
    private val onToggleStatus: (TransactionWithCategory) -> Unit,
) : ListAdapter<TransactionWithCategory, TransactionAdapter.ViewHolder>(DIFF) {

    private val displayFormat = SimpleDateFormat("dd/MM/yyyy", PT_BR)
    private val storageFormat = SimpleDateFormat("yyyy-MM-dd", Locale.ROOT)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemTransactionBinding.inflate(LayoutInflater.from(parent.context), parent, false)
        return ViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        holder.bind(getItem(position))
    }

    inner class ViewHolder(private val binding: ItemTransactionBinding) :
        RecyclerView.ViewHolder(binding.root) {

        fun bind(entry: TransactionWithCategory) {
            val context = binding.root.context
            val transaction = entry.transaction
            binding.textDescription.text = transaction.description

            val date = try {
                displayFormat.format(storageFormat.parse(transaction.occurredAt)!!)
            } catch (_: Exception) {
                transaction.occurredAt
            }
            binding.textMeta.text = "$date · ${entry.categoryName}"

            val isExpense = transaction.type == TransactionType.EXPENSE
            val sign = if (isExpense) "- " else "+ "
            binding.textAmount.text = sign + formatCents(transaction.amountCents)
            binding.textAmount.setTextColor(
                ContextCompat.getColor(
                    context,
                    if (isExpense) R.color.value_expense else R.color.value_income,
                )
            )

            val isPaid = transaction.status == TransactionStatus.PAID
            binding.textStatus.text = context.getString(
                if (isPaid) R.string.label_paid else R.string.label_pending
            )
            binding.textStatus.setTextColor(
                ContextCompat.getColor(
                    context,
                    if (isPaid) R.color.value_income else R.color.deep_saffron,
                )
            )

            binding.root.setOnClickListener { onClick(entry) }
            binding.root.setOnLongClickListener {
                onLongClick(entry)
                true
            }
            binding.textStatus.setOnClickListener { onToggleStatus(entry) }
        }
    }

    companion object {
        private val DIFF = object : DiffUtil.ItemCallback<TransactionWithCategory>() {
            override fun areItemsTheSame(old: TransactionWithCategory, new: TransactionWithCategory) =
                old.transaction.id == new.transaction.id

            override fun areContentsTheSame(old: TransactionWithCategory, new: TransactionWithCategory) =
                old == new
        }
    }
}
