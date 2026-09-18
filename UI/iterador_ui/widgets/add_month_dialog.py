"""Diálogo modal pra adicionar um mês manualmente ao `MonthSelector` (ver ADR-0018).

Existe pra quando o usuário quer começar a lançar num mês que ainda não tem nenhuma transação
(ex. planejar o mês que vem) — sem isso, não haveria como o mês aparecer na tira, já que ela só
lista meses com pelo menos um lançamento (mais o mês selecionado atual).
"""

import datetime

import customtkinter as ctk

from iterador_ui import theme
from iterador_ui.widgets.dialog_utils import make_modal

_INPUT_FORMATS = ("%m/%Y", "%Y-%m")


def parse_month_input(text: str) -> str | None:
    """Aceita "MM/AAAA" (formato natural em PT-BR) ou "AAAA-MM". Retorna "YYYY-MM" ou None se
    o texto não bater com nenhum dos dois formatos."""
    text = text.strip()
    for fmt in _INPUT_FORMATS:
        try:
            parsed = datetime.datetime.strptime(text, fmt)
            return f"{parsed.year:04d}-{parsed.month:02d}"
        except ValueError:
            continue
    return None


class AddMonthDialog(ctk.CTkToplevel):
    def __init__(self, master, on_add):
        super().__init__(master)
        self._on_add = on_add

        self.title("Adicionar mês")
        self.geometry("280x180")
        self.configure(fg_color=theme.BG_APP)
        make_modal(self, master)

        ctk.CTkLabel(self, text="Mês (MM/AAAA)", text_color=theme.TEXT_PRIMARY).pack(
            anchor="w", padx=20, pady=(20, 4))
        self._entry = ctk.CTkEntry(self, placeholder_text="ex. 10/2026")
        self._entry.pack(fill="x", padx=20)
        self._entry.bind("<Return>", lambda _event: self._submit())
        self._entry.focus()

        self._error_label = ctk.CTkLabel(self, text="", text_color=theme.ACCENT_EXPENSE)
        self._error_label.pack(anchor="w", padx=20, pady=(8, 0))

        ctk.CTkButton(
            self, text="Adicionar", fg_color=theme.ACCENT_EXPENSE, command=self._submit,
        ).pack(fill="x", padx=20, pady=(16, 20))

    def _submit(self) -> None:
        month_str = parse_month_input(self._entry.get())
        if month_str is None:
            self._error_label.configure(text="Formato inválido. Use MM/AAAA (ex. 10/2026).")
            return
        self._on_add(month_str)
        self.destroy()
