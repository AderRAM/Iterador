"""Orçamentos — metas de economia (ver core::Budget e Guide/decisions/0017-savings-goal-budgets.md).

Não é limite de gasto por categoria: o usuário cria um item (ex. "Notebook novo"), define o
valor total e em quantos meses quer dividir, e a UI calcula quanto precisa guardar por mês.
Opcionalmente vincula um investimento existente, só como referência de onde o dinheiro acumulado
está investido enquanto a meta não é atingida.
"""

import customtkinter as ctk

from iterador_ui import backend_bridge, theme
from iterador_ui.widgets.budget_form_dialog import BudgetFormDialog
from iterador_ui.widgets.dialog_utils import open_singleton


class BudgetsView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=theme.BG_APP)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(24, 8))

        ctk.CTkLabel(
            header, text="Orçamentos",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=theme.TEXT_PRIMARY,
        ).pack(side="left")

        ctk.CTkButton(
            header, text="+ Nova meta", fg_color=theme.ACCENT_EXPENSE,
            command=self._open_new_budget_dialog,
        ).pack(side="right")

        self._list_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._list_frame.pack(fill="both", expand=True, padx=24, pady=8)

        self.refresh()

    def _open_new_budget_dialog(self) -> None:
        open_singleton(self, "_budget_dialog",
                        lambda: BudgetFormDialog(self, on_created=self.refresh))

    def _open_edit_budget_dialog(self, budget) -> None:
        open_singleton(self, "_budget_dialog", lambda: BudgetFormDialog(
            self, on_created=self.refresh, budget=budget))

    def refresh(self) -> None:
        for child in self._list_frame.winfo_children():
            child.destroy()

        budgets = backend_bridge.list_budgets()
        if not budgets:
            ctk.CTkLabel(
                self._list_frame, text="Nenhuma meta de economia ainda.",
                text_color=theme.TEXT_PRIMARY,
            ).pack(anchor="w")
            return

        investments_by_id = {inv.id: inv for inv in backend_bridge.list_investments()}

        for budget in budgets:
            row = ctk.CTkFrame(self._list_frame, fg_color=theme.BG_SURFACE,
                                border_width=1, border_color=theme.INDIGO, corner_radius=8)
            row.pack(fill="x", pady=4)

            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", padx=12, pady=8, fill="x", expand=True)
            ctk.CTkLabel(info, text=budget.name, text_color=theme.TEXT_PRIMARY,
                         font=ctk.CTkFont(weight="bold")).pack(anchor="w")

            monthly_cents = budget.target_value.cents / budget.months
            details = (f"R$ {budget.target_value.cents / 100:.2f} em {budget.months} "
                       f"mês(es) · guardar R$ {monthly_cents / 100:.2f}/mês")
            if budget.investment_id and budget.investment_id in investments_by_id:
                details += f" · investido em {investments_by_id[budget.investment_id].name}"
            ctk.CTkLabel(info, text=details, text_color=theme.TEXT_PRIMARY,
                         font=ctk.CTkFont(size=11)).pack(anchor="w")

            ctk.CTkButton(
                row, text="Editar", width=64, fg_color="transparent",
                text_color=theme.TEXT_PRIMARY, hover_color=theme.BG_APP,
                command=lambda b=budget: self._open_edit_budget_dialog(b),
            ).pack(side="right", padx=(0, 4), pady=8)
