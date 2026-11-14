package com.finance.iterador.ui.investments

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
import com.finance.iterador.data.entity.InvestmentEntity
import com.finance.iterador.databinding.FragmentInvestmentsBinding

class InvestmentsFragment : Fragment() {

    private var _binding: FragmentInvestmentsBinding? = null
    private val binding get() = _binding!!

    private val viewModel: InvestmentsViewModel by viewModels {
        val repository = (requireActivity().application as IteradorApplication).repository
        viewModelFactory { initializer { InvestmentsViewModel(repository) } }
    }

    private lateinit var adapter: InvestmentAdapter

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?,
    ): View {
        _binding = FragmentInvestmentsBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        adapter = InvestmentAdapter(
            onClick = { investment ->
                showInvestmentFormDialog(requireContext(), investment) { updated ->
                    viewModel.update(updated)
                }
            },
            onLongClick = { investment -> confirmDelete(investment) },
        )
        binding.recyclerInvestments.layoutManager = LinearLayoutManager(requireContext())
        binding.recyclerInvestments.adapter = adapter

        binding.fabAddInvestment.setOnClickListener {
            showInvestmentFormDialog(requireContext(), null) { investment -> viewModel.save(investment) }
        }

        viewModel.investments.observe(viewLifecycleOwner) { investments ->
            adapter.submitList(investments)
            binding.textEmpty.visibility = if (investments.isEmpty()) View.VISIBLE else View.GONE
        }
    }

    private fun confirmDelete(investment: InvestmentEntity) {
        AlertDialog.Builder(requireContext())
            .setTitle(R.string.confirm_delete_title)
            .setMessage(R.string.confirm_delete_investment)
            .setPositiveButton(R.string.action_delete) { _, _ -> viewModel.delete(investment) }
            .setNegativeButton(R.string.action_cancel, null)
            .show()
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
