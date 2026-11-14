package com.finance.iterador.ui.budgets

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.finance.iterador.R
import com.finance.iterador.data.entity.BudgetEntity
import com.finance.iterador.data.formatCents
import com.finance.iterador.databinding.ItemBudgetBinding

class BudgetAdapter(
    private val onClick: (BudgetEntity) -> Unit,
    private val onLongClick: (BudgetEntity) -> Unit,
) : ListAdapter<BudgetEntity, BudgetAdapter.ViewHolder>(DIFF) {

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemBudgetBinding.inflate(LayoutInflater.from(parent.context), parent, false)
        return ViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        holder.bind(getItem(position))
    }

    inner class ViewHolder(private val binding: ItemBudgetBinding) :
        RecyclerView.ViewHolder(binding.root) {

        fun bind(budget: BudgetEntity) {
            val context = binding.root.context
            binding.textName.text = budget.name
            binding.textTarget.text = context.getString(
                R.string.label_budget_target,
                formatCents(budget.targetValueCents),
                budget.months,
            )
            val monthlyCents = if (budget.months > 0) budget.targetValueCents / budget.months else 0
            binding.textContribution.text = context.getString(
                R.string.label_monthly_contribution,
                formatCents(monthlyCents),
            )
            binding.root.setOnClickListener { onClick(budget) }
            binding.root.setOnLongClickListener {
                onLongClick(budget)
                true
            }
        }
    }

    companion object {
        private val DIFF = object : DiffUtil.ItemCallback<BudgetEntity>() {
            override fun areItemsTheSame(old: BudgetEntity, new: BudgetEntity) = old.id == new.id
            override fun areContentsTheSame(old: BudgetEntity, new: BudgetEntity) = old == new
        }
    }
}
