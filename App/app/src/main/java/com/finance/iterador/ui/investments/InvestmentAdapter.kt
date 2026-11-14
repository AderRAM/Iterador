package com.finance.iterador.ui.investments

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.finance.iterador.data.entity.InvestmentEntity
import com.finance.iterador.data.formatCents
import com.finance.iterador.databinding.ItemInvestmentBinding

class InvestmentAdapter(
    private val onClick: (InvestmentEntity) -> Unit,
    private val onLongClick: (InvestmentEntity) -> Unit,
) : ListAdapter<InvestmentEntity, InvestmentAdapter.ViewHolder>(DIFF) {

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemInvestmentBinding.inflate(LayoutInflater.from(parent.context), parent, false)
        return ViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        holder.bind(getItem(position))
    }

    inner class ViewHolder(private val binding: ItemInvestmentBinding) :
        RecyclerView.ViewHolder(binding.root) {

        fun bind(investment: InvestmentEntity) {
            binding.textName.text = investment.name
            binding.textType.text = investment.type
            binding.textValue.text = formatCents(investment.currentValueCents)
            binding.root.setOnClickListener { onClick(investment) }
            binding.root.setOnLongClickListener {
                onLongClick(investment)
                true
            }
        }
    }

    companion object {
        private val DIFF = object : DiffUtil.ItemCallback<InvestmentEntity>() {
            override fun areItemsTheSame(old: InvestmentEntity, new: InvestmentEntity) = old.id == new.id
            override fun areContentsTheSame(old: InvestmentEntity, new: InvestmentEntity) = old == new
        }
    }
}
