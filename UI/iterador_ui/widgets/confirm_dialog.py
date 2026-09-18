"""Diálogo de confirmação genérico pra ações potencialmente destrutivas. Primeiro uso: remover
um mês inteiro (ver Guide/decisions/0019-remove-month-with-undo.md).
"""

import customtkinter as ctk

from iterador_ui import theme
from iterador_ui.widgets.dialog_utils import make_modal


class ConfirmDialog(ctk.CTkToplevel):
    def __init__(self, master, title: str, message: str, on_confirm,
                 confirm_text: str = "Confirmar"):
        super().__init__(master)
        self._on_confirm = on_confirm

        self.title(title)
        self.geometry("340x170")
        self.configure(fg_color=theme.BG_APP)
        make_modal(self, master)

        ctk.CTkLabel(
            self, text=message, text_color=theme.TEXT_PRIMARY, wraplength=300, justify="left",
        ).pack(fill="x", padx=20, pady=(20, 16))

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(fill="x", padx=20, pady=(0, 20))
        ctk.CTkButton(
            buttons, text="Cancelar", fg_color="transparent", text_color=theme.TEXT_PRIMARY,
            hover_color=theme.BG_SURFACE, command=self.destroy,
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(
            buttons, text=confirm_text, fg_color=theme.ACCENT_EXPENSE, command=self._confirm,
        ).pack(side="right", fill="x", expand=True)

    def _confirm(self) -> None:
        self._on_confirm()
        self.destroy()
