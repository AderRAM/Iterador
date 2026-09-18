"""Card reutilizável rótulo+valor, para o dashboard e outras telas. Ver Guide/file-map.md."""

import customtkinter as ctk

from iterador_ui import theme


class StatCard(ctk.CTkFrame):
    def __init__(self, master, label: str, value: str, accent: str = theme.ACCENT_HIGHLIGHT):
        super().__init__(master, fg_color=theme.BG_SURFACE, corner_radius=10,
                          border_width=2, border_color=accent)

        ctk.CTkLabel(
            self, text=label, text_color=theme.TEXT_PRIMARY,
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=14, pady=(12, 0))

        ctk.CTkLabel(
            self, text=value, text_color=accent,
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(anchor="w", padx=14, pady=(0, 12))

    def set_value(self, value: str, color: str | None = None) -> None:
        # Segundo filho é o label de valor (ver __init__): mantém a API simples sem guardar
        # referência extra por enquanto. color opcional recolore o valor (ex. verde/vermelho
        # dinâmico conforme o sinal — ver DashboardView "Saldo já pago").
        value_label = self.winfo_children()[1]
        # `.configure()` redesenha o label (CTk desenha tudo em canvas por baixo) mesmo quando o
        # texto/cor não mudam — pulando aqui evita um redesenho (e "piscar") à toa toda vez que
        # `DashboardView.refresh()` roda por uma ação que não altera este valor (ex. Desfazer de
        # um arrasto ou de um toggle de status).
        if value_label.cget("text") == value and (color is None or value_label.cget("text_color") == color):
            return
        value_label.configure(text=value)
        if color is not None:
            value_label.configure(text_color=color)
