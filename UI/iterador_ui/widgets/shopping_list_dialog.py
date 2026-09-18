"""Diálogo modal "Lista de compras" — entrada rápida de várias despesas pequenas de uma vez
(compras do dia a dia), reaproveitando o modelo de `Transaction` já existente em vez de criar
uma entidade nova. Ver Guide/decisions/0022-generic-unlabeled-investment-link.md.

Cada item vira uma transação Despesa/Essencial/Pendente na data de hoje — `DashboardView` já
soma despesas Pendentes+Pagas em "Despesas do mês" (não filtra por status), então os itens já
entram no total do mês assim que adicionados, sem nenhuma lógica de agregação nova. O usuário
marca "Pago" depois pelo toggle que já existe na lista de lançamentos, quando efetivamente
comprar.
"""

import datetime

import customtkinter as ctk

from iterador_ui import backend_bridge, theme
from iterador_ui.widgets.dialog_utils import make_modal

_ITEM_CATEGORY = "Essencial"


class ShoppingListDialog(ctk.CTkToplevel):
    def __init__(self, master, on_created):
        super().__init__(master)
        self._on_created = on_created
        self._rows: list[tuple[ctk.CTkEntry, ctk.CTkEntry, ctk.CTkFrame]] = []

        self.title("Lista de compras")
        self.geometry("360x480")
        self.configure(fg_color=theme.BG_APP)
        make_modal(self, master)

        ctk.CTkLabel(
            self, text="Item e valor de cada compra — todos viram lançamentos "
            '"A pagar" em Essencial, na data de hoje.',
            text_color=theme.TEXT_PRIMARY, wraplength=320, justify="left",
        ).pack(anchor="w", padx=20, pady=(20, 8))

        self._rows_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._rows_frame.pack(fill="both", expand=True, padx=20)

        ctk.CTkButton(
            self, text="+ Item", command=self._add_row, **theme.outline_button_style(),
        ).pack(fill="x", padx=20, pady=(8, 0))

        self._error_label = ctk.CTkLabel(self, text="", text_color=theme.ACCENT_EXPENSE)
        self._error_label.pack(anchor="w", padx=20, pady=(8, 0))

        ctk.CTkButton(
            self, text="Adicionar todos", fg_color=theme.ACCENT_EXPENSE,
            command=self._submit,
        ).pack(fill="x", padx=20, pady=(8, 20))

        self._add_row()
        self._add_row()

    def _add_row(self) -> None:
        row = ctk.CTkFrame(self._rows_frame, fg_color="transparent")
        row.pack(fill="x", pady=2)

        item_entry = ctk.CTkEntry(row, placeholder_text="Item (ex. Leite)")
        item_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))

        value_entry = ctk.CTkEntry(row, placeholder_text="0,00", width=80)
        value_entry.pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            row, text="✕", width=28, fg_color="transparent", text_color=theme.TEXT_PRIMARY,
            hover_color=theme.BG_SURFACE, command=lambda: self._remove_row(row),
        ).pack(side="left")

        self._rows.append((item_entry, value_entry, row))

    def _remove_row(self, row: ctk.CTkFrame) -> None:
        self._rows = [entry for entry in self._rows if entry[2] is not row]
        row.destroy()

    def _submit(self) -> None:
        items: list[tuple[str, int]] = []
        for item_entry, value_entry, _row in self._rows:
            name = item_entry.get().strip()
            raw_value = value_entry.get().strip()
            if not name and not raw_value:
                continue  # linha em branco — ignora, não é erro
            if not name:
                self._error_label.configure(text="Falta o nome de um item com valor preenchido.")
                return
            try:
                value_cents = round(float(raw_value.replace(",", ".") or "0") * 100)
            except ValueError:
                self._error_label.configure(text=f'Valor inválido em "{name}".')
                return
            if value_cents <= 0:
                self._error_label.configure(text=f'Informe um valor maior que zero em "{name}".')
                return
            items.append((name, value_cents))

        if not items:
            self._error_label.configure(text="Adicione pelo menos um item.")
            return

        enums = backend_bridge.transaction_enums()
        today = datetime.date.today().isoformat()
        for name, value_cents in items:
            created = backend_bridge.create_transaction(
                name, _ITEM_CATEGORY, enums["expense"], -value_cents, "BRL", enums["pending"],
                today)
            self._on_created(created)

        self.destroy()
