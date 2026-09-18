"""Diálogo "Importar extrato" — revisão antes de confirmar. Ver
Guide/decisions/0024-nubank-statement-import.md.

Diferente do importador da planilha (ADR-0023, que já sabia a categoria pela coluna Prioridade e
importava direto), o CSV do Nubank não tem nada equivalente — cada linha aparece aqui com um
seletor de categoria começando em "(escolher)"; só as que o usuário categorizar de verdade viram
`Transaction` ao confirmar. As demais simplesmente não são criadas agora (reaparecem numa
importação futura do mesmo período, já que não geraram registro nenhum).
"""

import customtkinter as ctk

from iterador_ui import backend_bridge, theme
from iterador_ui.statement_import import parse_statement
from iterador_ui.widgets.dialog_utils import make_modal

_PLACEHOLDER = "(escolher)"


def _format_money(cents: int) -> str:
    return f"R$ {cents / 100:,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")


class StatementReviewDialog(ctk.CTkToplevel):
    def __init__(self, master, path: str, on_created):
        super().__init__(master)
        self._on_created = on_created
        self._row_widgets: list[dict] = []

        self.title("Importar extrato")
        self.geometry("560x600")
        self.configure(fg_color=theme.BG_APP)
        make_modal(self, master)

        self._status_label = ctk.CTkLabel(
            self, text="Lendo arquivo...", text_color=theme.TEXT_PRIMARY, wraplength=520,
            justify="left")
        self._status_label.pack(anchor="w", padx=20, pady=(20, 8))

        self._rows_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._rows_frame.pack(fill="both", expand=True, padx=20)

        self._summary_label = ctk.CTkLabel(
            self, text="", text_color=theme.TEXT_PRIMARY, wraplength=520, justify="left")
        self._summary_label.pack(anchor="w", padx=20, pady=(8, 0))

        self._import_button = ctk.CTkButton(
            self, text="Importar selecionados", fg_color=theme.ACCENT_EXPENSE,
            command=self._submit, state="disabled",
        )
        self._import_button.pack(fill="x", padx=20, pady=(8, 20))

        self._load(path)

    def _load(self, path: str) -> None:
        result = parse_statement(path)
        if result.errors:
            self._status_label.configure(
                text="\n".join(result.errors), text_color=theme.VALUE_EXPENSE)
            return

        existing_keys = {
            (t.occurred_at, t.description, t.amount.cents)
            for t in backend_bridge.list_transactions()}

        new_rows = [
            row for row in result.rows
            if (row.occurred_at, row.description, row.amount_cents) not in existing_keys]
        already_existed = len(result.rows) - len(new_rows)

        self._status_label.configure(
            text=f"{result.format_name} — {len(new_rows)} lançamento(s) novo(s) pra revisar"
                 + (f" ({already_existed} já existia(m), não aparecem aqui)."
                    if already_existed else "."))

        if not new_rows:
            return

        for row in new_rows:
            self._add_row(row)
        self._import_button.configure(state="normal")

    def _add_row(self, row) -> None:
        frame = ctk.CTkFrame(self._rows_frame, fg_color=theme.BG_SURFACE, corner_radius=8)
        frame.pack(fill="x", pady=3)

        info = ctk.CTkFrame(frame, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, padx=10, pady=8)
        ctk.CTkLabel(
            info, text=f"{row.occurred_at}  ·  {row.description}", text_color=theme.TEXT_PRIMARY,
            anchor="w", justify="left", wraplength=280,
        ).pack(anchor="w")
        value_color = theme.VALUE_INCOME_TEXT if row.amount_cents >= 0 else theme.VALUE_EXPENSE_TEXT
        ctk.CTkLabel(
            info, text=_format_money(row.amount_cents), text_color=value_color,
        ).pack(anchor="w")

        options = ([_PLACEHOLDER] + backend_bridge.income_category_names() if row.is_income
                   else [_PLACEHOLDER] + backend_bridge.expense_category_names())
        category_var = ctk.StringVar(value=_PLACEHOLDER)
        ctk.CTkOptionMenu(
            frame, values=options, variable=category_var, width=130,
            fg_color=theme.BG_APP, button_color=theme.INDIGO,
        ).pack(side="left", padx=(0, 8), pady=8)

        included_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            frame, text="", variable=included_var, width=20,
            checkmark_color=theme.CARBON_BLACK,
        ).pack(side="left", padx=(0, 10))

        self._row_widgets.append({
            "row": row, "category_var": category_var, "included_var": included_var,
        })

    def _submit(self) -> None:
        enums = backend_bridge.transaction_enums()
        created = 0
        skipped_no_category = 0

        for entry in self._row_widgets:
            if not entry["included_var"].get():
                continue
            category_name = entry["category_var"].get()
            if category_name == _PLACEHOLDER:
                skipped_no_category += 1
                continue

            row = entry["row"]
            type_ = enums["income"] if row.is_income else enums["expense"]
            created_transaction = backend_bridge.create_transaction(
                row.description, category_name, type_, row.amount_cents, "BRL", enums["paid"],
                row.occurred_at)
            self._on_created(created_transaction)
            created += 1

        self._summary_label.configure(
            text=f"{created} importado(s), {skipped_no_category} sem categoria escolhida "
                 "(não importado(s)).")
        for child in self._rows_frame.winfo_children():
            child.destroy()
        self._row_widgets.clear()
        self._import_button.configure(state="disabled")
