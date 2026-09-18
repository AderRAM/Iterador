"""Diálogo modal para criar ou editar uma meta de economia (orçamento). Ver Guide/file-map.md.

Meta de economia: "valor total" dividido em "quantos meses" para calcular o aporte mensal
necessário (ver core::Budget/ADR-0017). O investimento vinculado é opcional — só indica onde o
dinheiro acumulado fica investido enquanto a meta é atingida, não move valores automaticamente.
"""

import customtkinter as ctk

from iterador_ui import backend_bridge, theme
from iterador_ui.widgets.dialog_utils import make_modal


class BudgetFormDialog(ctk.CTkToplevel):
    def __init__(self, master, on_created, budget=None):
        super().__init__(master)
        self._on_created = on_created
        self._budget = budget
        is_edit = budget is not None

        self.title("Editar meta" if is_edit else "Nova meta de economia")
        self.geometry("360x420")
        self.configure(fg_color=theme.BG_APP)
        make_modal(self, master)

        self._name_entry = self._add_field(
            self, "Nome", "ex. Notebook novo, Viagem...",
            default=budget.name if is_edit else "")
        self._value_entry = self._add_field(
            self, "Valor total (R$)", "0,00",
            default=f"{budget.target_value.cents / 100:.2f}".replace(".", ",")
            if is_edit else "")
        self._months_entry = self._add_field(
            self, "Dividir em quantos meses", "ex. 6",
            default=str(budget.months) if is_edit else "1")

        self._investments = backend_bridge.list_investments()
        investment_names = ["Nenhum"] + [inv.name for inv in self._investments]
        ctk.CTkLabel(self, text="Investimento vinculado (opcional)",
                     text_color=theme.TEXT_PRIMARY).pack(anchor="w", padx=20, pady=(12, 4))
        default_investment_name = "Nenhum"
        if is_edit and budget.investment_id:
            for inv in self._investments:
                if inv.id == budget.investment_id:
                    default_investment_name = inv.name
                    break
        self._investment_menu = ctk.CTkOptionMenu(self, values=investment_names)
        self._investment_menu.set(default_investment_name)
        self._investment_menu.pack(fill="x", padx=20)

        self._monthly_label = ctk.CTkLabel(
            self, text="", text_color=theme.ACCENT_HIGHLIGHT, font=ctk.CTkFont(size=12))
        self._monthly_label.pack(anchor="w", padx=20, pady=(12, 0))
        self._value_entry.bind("<KeyRelease>", lambda _e: self._update_monthly_preview())
        self._months_entry.bind("<KeyRelease>", lambda _e: self._update_monthly_preview())
        self._update_monthly_preview()

        self._error_label = ctk.CTkLabel(self, text="", text_color=theme.ACCENT_EXPENSE)
        self._error_label.pack(anchor="w", padx=20, pady=(10, 0))

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(fill="x", padx=20, pady=(16, 20))
        if is_edit:
            ctk.CTkButton(
                buttons, text="Excluir", fg_color="transparent", text_color=theme.ACCENT_EXPENSE,
                hover_color=theme.BG_SURFACE, command=self._delete,
            ).pack(side="left")
        ctk.CTkButton(
            buttons, text="Salvar alterações" if is_edit else "Criar meta",
            fg_color=theme.ACCENT_EXPENSE, command=self._submit,
        ).pack(side="right", fill="x", expand=True, padx=(8 if is_edit else 0, 0))

    def _add_field(self, parent, label: str, placeholder, default: str = "") -> ctk.CTkEntry:
        ctk.CTkLabel(parent, text=label, text_color=theme.TEXT_PRIMARY).pack(
            anchor="w", padx=20, pady=(12, 4))
        entry = ctk.CTkEntry(parent, placeholder_text=placeholder)
        if default:
            entry.insert(0, default)
        entry.pack(fill="x", padx=20)
        return entry

    def _update_monthly_preview(self) -> None:
        try:
            value = float(self._value_entry.get().strip().replace(",", ".") or "0")
            months = int(self._months_entry.get().strip() or "1")
            if months <= 0:
                raise ValueError
        except ValueError:
            self._monthly_label.configure(text="")
            return
        monthly = value / months
        self._monthly_label.configure(
            text=f"Guardar R$ {monthly:.2f} por mês durante {months} mês(es).")

    def _selected_investment_id(self) -> str:
        name = self._investment_menu.get()
        if name == "Nenhum":
            return ""
        for inv in self._investments:
            if inv.name == name:
                return inv.id
        return ""

    def _submit(self) -> None:
        name = self._name_entry.get().strip()
        if not name:
            self._error_label.configure(text="Informe um nome.")
            return

        try:
            value_cents = round(float(self._value_entry.get().strip().replace(",", ".") or "0") * 100)
            months = int(self._months_entry.get().strip() or "0")
            if value_cents <= 0 or months <= 0:
                raise ValueError
        except ValueError:
            self._error_label.configure(text="Valor e meses precisam ser maiores que zero.")
            return

        investment_id = self._selected_investment_id()

        if self._budget is not None:
            backend_bridge.update_budget(
                self._budget.id, name, value_cents, "BRL", months, investment_id)
        else:
            backend_bridge.create_budget(name, value_cents, "BRL", months, investment_id)
        self._on_created()
        self.destroy()

    def _delete(self) -> None:
        if self._budget is not None:
            backend_bridge.delete_budget(self._budget.id)
        self._on_created()
        self.destroy()
