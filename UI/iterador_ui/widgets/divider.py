"""Linha divisória fina e reutilizável (ver Guide/decisions/0020-color-profile-system.md).

Só um CTkFrame fino sem conteúdo — a cor vem sempre de `theme.py` (nunca hardcoded no widget
que usa o Divider), então trocar de perfil de cor já atualiza todos os separadores do app sem
precisar editar view por view.
"""

import customtkinter as ctk


class Divider(ctk.CTkFrame):
    def __init__(self, master, color, thickness: int = 2, orientation: str = "horizontal",
                 **kwargs):
        if orientation == "horizontal":
            kwargs.setdefault("height", thickness)
        else:
            kwargs.setdefault("width", thickness)
        super().__init__(master, fg_color=color, corner_radius=0, **kwargs)
