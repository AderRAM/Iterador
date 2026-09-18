"""Label com o texto sempre com contorno preto ao redor — usado onde a cor do texto vem de um
dado do usuário (cor de categoria, ver `theme.category_label_color`) e por isso não dá pra
garantir contraste bom contra o fundo sozinha, principalmente no modo claro (relato do usuário,
ver ADR-0042). Variante mais fina da técnica de `TriangleHeading._draw_outlined_text` (lá usa 8
direções incl. diagonais; aqui só as 4 cardeais — 8 deixava o contorno mais grosso do que devia,
ver ADR-0042) — texto desenhado em preto, 1px de offset, com a cor real por cima, generalizado
pra texto de tamanho variável (o nome da categoria muda), então não dá pra fixar um retângulo
como lá. Investimento/Passiva não levam contorno nenhum (ver `theme.CATEGORY_NO_OUTLINE`/
ADR-0047) — a cor dedicada dessas duas já garante contraste sozinha, e o contorno só deixava as
letras mais grossas sem ganhar legibilidade real (relato do usuário).

`CTkLabel` não dá pra usar (Tkinter não tem contorno de texto nativo) — por isso um
`tk.Canvas` puro, igual `ConsumptionChart`/`LineChart`/`TriangleHeading` já fazem. Diferente
desses três, porém, `tk.Canvas` sozinho é Tkinter puro, não CustomTkinter — nunca é avisado
quando o tema claro/escuro muda (`ctk.set_appearance_mode()`), então precisa se inscrever à mão
no `CTkAppearanceModeBaseClass` pra saber quando redesenhar (ver `_set_appearance_mode` abaixo);
sem isso, o fundo E a cor do texto ficavam "congelados" no modo em que a linha foi desenhada por
último — trocar de tema sem re-renderizar a lista deixava uma caixa clara (fundo do modo claro)
sobre fundo escuro, ou uma caixa escura sobre fundo claro, atrás do texto (relato do usuário,
ADR-0047)."""

import tkinter as tk
from tkinter import font as tkfont

import customtkinter as ctk
from customtkinter.windows.widgets.appearance_mode.appearance_mode_base_class import (
    CTkAppearanceModeBaseClass,
)

from iterador_ui import theme

# Só as 4 direções cardeais (sem diagonais) — com as 8 (ver TriangleHeading), as diagonais se
# somavam nos cantos de cada letra e o contorno ficava mais grosso do que devia (relato do
# usuário). 4 direções já resolve o contraste sem engrossar tanto.
_OUTLINE_OFFSETS = ((-1, 0), (1, 0), (0, -1), (0, 1))
_OUTLINE_COLOR = "#000000"


class OutlinedLabel(tk.Canvas, CTkAppearanceModeBaseClass):
    def __init__(self, master, font: "tkfont.Font | None" = None):
        self._font = font or ctk.CTkFont()
        # Altura fixa desde a construção — nunca lida de volta via `winfo_reqheight()` (valor
        # fica obsoleto se consultado antes do Tk processar a fila de eventos, mesma armadilha
        # já vista no arrasto da lista, ver ADR-0033).
        self._height = self._font.metrics("linespace") + 2
        tk.Canvas.__init__(self, master, height=self._height, highlightthickness=0)
        CTkAppearanceModeBaseClass.__init__(self)
        self._category_name = ""
        # Papel de cor ATUAL do fundo — normalmente `theme.BG_PANEL_BLUE` (o painel onde a lista
        # de lançamentos realmente fica, ver `DashboardView`; usar `BG_APP` aqui era o bug do
        # fundo errado, ver ADR-0047), mas vira `theme.BG_SURFACE` durante o "elevar" da linha no
        # arrasto (`set_background`/`reset_background`, ADR-0033).
        self._background_role = theme.BG_PANEL_BLUE
        self.configure(bg=self._resolve(self._background_role))

    def destroy(self) -> None:
        CTkAppearanceModeBaseClass.destroy(self)
        tk.Canvas.destroy(self)

    def tkraise(self, aboveThis=None) -> None:
        # `tk.Canvas` sobrescreve `tkraise`/`lift` pra "levantar item do canvas" (`tag_raise`,
        # exige um id de item) — não é o que o resto da lista espera ao chamar isso genérico em
        # todo widget de uma linha (levantar a JANELA na pilha de empilhamento, ver
        # `DashboardView._show_card_bg`/ADR-0033/0042). Restaura o comportamento normal.
        self.tk.call("raise", self._w, aboveThis)

    lift = tkraise

    @staticmethod
    def _resolve(color) -> str:
        """Aceita cor sólida OU par (claro, escuro) — igual o resto do app guarda papel
        estrutural (ver `theme.py`); Canvas puro só entende uma cor só, precisa resolver."""
        if isinstance(color, (tuple, list)):
            mode = ctk.get_appearance_mode()
            return color[0] if mode == "Light" else color[1]
        return color

    def _set_appearance_mode(self, mode_string: str) -> None:
        CTkAppearanceModeBaseClass._set_appearance_mode(self, mode_string)
        self.configure(bg=self._resolve(self._background_role))
        if self._category_name:
            self._draw()

    def set_text(self, category_name: str) -> None:
        if category_name == self._category_name:
            return  # evita redesenhar toda vez que a lista renderiza sem essa célula ter mudado
        self._category_name = category_name
        self._draw()

    def _draw(self) -> None:
        text = self._category_name
        color = theme.category_label_color(text)

        self.delete("all")
        width = self._font.measure(text) + 2
        self.configure(width=width)
        y = self._height // 2
        if text not in theme.CATEGORY_NO_OUTLINE:
            for dx, dy in _OUTLINE_OFFSETS:
                self.create_text(
                    1 + dx, y + dy, text=text, fill=_OUTLINE_COLOR, font=self._font, anchor="w")
        self.create_text(1, y, text=text, fill=color, font=self._font, anchor="w")

    def set_background(self, color) -> None:
        """Só troca o fundo, sem mexer no texto — usado pra "elevar" a linha durante o arrasto
        (ver `DashboardView._on_handle_press`/ADR-0033); `reset_background()` devolve depois."""
        self._background_role = color
        self.configure(bg=self._resolve(color))

    def reset_background(self) -> None:
        """Devolve o fundo pro papel normal (`theme.BG_PANEL_BLUE`) — chamado ao soltar o
        arrasto, par de `set_background()`."""
        self.set_background(theme.BG_PANEL_BLUE)
