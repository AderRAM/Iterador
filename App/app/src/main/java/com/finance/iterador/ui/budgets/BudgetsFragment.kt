package com.finance.iterador.ui.budgets

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.appcompat.app.AlertDialog
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import androidx.recyclerview.widget.LinearLayoutManager
import com.finance.iterador.IteradorApplication
import com.finance.iterador.R
import com.finance.iterador.data.entity.BudgetEntity
import com.finance.iterador.data.entity.InvestmentEntity
import com.finance.iterador.databinding.FragmentBudgetsBinding

class BudgetsFragment : Fragment() {

    private var _binding: FragmentBudgetsBinding? = null
    private val binding get() = _binding!!

    private val viewModel: BudgetsViewModel by viewModels {
        val repository = (requireActivity().application as IteradorApplication).repository
        viewModelFactory { initializer { BudgetsViewModel(repository) } }
    }

    private lateinit var adapter: BudgetAdapter
    private var investments: List<InvestmentEntity> = emptyList()

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?,
    ): View {
        _binding = FragmentBudgetsBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        adapter = BudgetAdapter(
            onClick = { budget ->
                showBudgetFormDialog(requireContext(), investments, budget) { updated ->
                    viewModel.update(updated)
                }
            },
            onLongClick = { budget -> confirmDelete(budget) },
        )
        binding.recyclerBudgets.layoutManager = LinearLayoutManager(requireContext())
        binding.recyclerBudgets.adapter = adapter

        binding.fabAddBudget.setOnClickListener {
            showBudgetFormDialog(requireContext(), investments, null) { budget -> viewModel.save(budget) }
        }

        viewModel.investments.observe(viewLifecycleOwner) { investments = it }

        viewModel.budgets.observe(viewLifecycleOwner) { budgets ->
            adapter.submitList(budgets)
            binding.textEmpty.visibility = if (budgets.isEmpty()) View.VISIBLE else View.GONE
        }
    }

    private fun confirmDelete(budget: BudgetEntity) {
        AlertDialog.Builder(requireContext())
            .setTitle(R.string.confirm_delete_title)
            .setMessage(R.string.confirm_delete_budget)
            .setPositiveButton(R.string.action_delete) { _, _ -> viewModel.delete(budget) }
            .setNegativeButton(R.string.action_cancel, null)
            .show()
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
