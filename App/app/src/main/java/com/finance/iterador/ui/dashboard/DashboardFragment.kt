package com.finance.iterador.ui.dashboard

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
import com.finance.iterador.data.formatCents
import com.finance.iterador.databinding.FragmentDashboardBinding

class DashboardFragment : Fragment() {

    private var _binding: FragmentDashboardBinding? = null
    private val binding get() = _binding!!

    private val viewModel: DashboardViewModel by viewModels {
        val repository = (requireActivity().application as IteradorApplication).repository
        viewModelFactory { initializer { DashboardViewModel(repository) } }
    }

    private lateinit var adapter: TransactionAdapter
    private var categories: List<com.finance.iterador.data.entity.CategoryEntity> = emptyList()

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?,
    ): View {
        _binding = FragmentDashboardBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        adapter = TransactionAdapter(
            onClick = { entry ->
                showTransactionFormDialog(requireContext(), categories, entry.transaction) { updated ->
                    viewModel.update(entry.transaction, updated)
                }
            },
            onLongClick = { entry -> confirmDelete(entry) },
            onToggleStatus = { entry -> viewModel.toggleStatus(entry) },
        )
        binding.recyclerTransactions.layoutManager = LinearLayoutManager(requireContext())
        binding.recyclerTransactions.adapter = adapter

        binding.fabAddTransaction.setOnClickListener {
            showTransactionFormDialog(requireContext(), categories, null) { transaction ->
                viewModel.save(transaction)
            }
        }

        viewModel.categories.observe(viewLifecycleOwner) { categories = it }

        viewModel.transactions.observe(viewLifecycleOwner) { entries ->
            adapter.submitList(entries)
            binding.textEmpty.visibility = if (entries.isEmpty()) View.VISIBLE else View.GONE

            val (income, expense, balance) = DashboardViewModel.totals(entries)
            binding.textSummaryIncome.text = getString(R.string.summary_income, formatCents(income))
            binding.textSummaryExpense.text = getString(R.string.summary_expense, formatCents(expense))
            binding.textSummaryBalance.text = getString(R.string.summary_balance, formatCents(balance))
        }
    }

    private fun confirmDelete(entry: com.finance.iterador.data.dao.TransactionWithCategory) {
        AlertDialog.Builder(requireContext())
            .setTitle(R.string.confirm_delete_title)
            .setMessage(R.string.confirm_delete_transaction)
            .setPositiveButton(R.string.action_delete) { _, _ -> viewModel.delete(entry.transaction) }
            .setNegativeButton(R.string.action_cancel, null)
            .show()
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
