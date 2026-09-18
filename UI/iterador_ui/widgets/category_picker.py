"""Grade de "chips" (`CTkButton`) pra escolher uma categoria — substitui `CTkSegmentedButton` só
nesse uso, porque `CTkSegmentedButton` não quebra em várias linhas (confirmado lendo o código do
pacote instalado: divide a largura disponível igualmente entre TODOS os valores numa linha só,
sem opção de quebra). Com mais de ~4 categorias (possível desde as categorias personalizadas, ver
ADR-0028) os nomes ficavam espremidos e ilegíveis numa linha só (relato do usuário, com
screenshot). Ver ADR-0029.

Até `_COLUMNS` categorias por linha; acima de `_MAX_VISIBLE_ROWS` linhas, a grade de chips fica
dentro de um `CTkScrollableFrame` de altura fixa (cabe exatamente `_MAX_VISIBLE_ROWS` linhas) em
vez de esticar o diálogo — o resto rola. Até `_MAX_VISIBLE_ROWS` linhas, é só um `CTkFrame` comum
(altura natural, sem scroll nenhum).

A própria picker observa a `StringVar` passada (`trace_add`) pra re-destacar o chip certo sempre
que o valor mudar — por clique num chip OU por `.set()` externo (ex.
`TransactionFormDialog._update_category_options()` corrigindo uma seleção que ficou inválida ao
trocar Despesa/Receita) — sem precisar de um parâmetro `command` feito à mão só pra isso.
"""

import customtkinter as ctk

from iterador_ui import theme

_COLUMNS = 4
_MAX_VISIBLE_ROWS = 2
_CHIP_HEIGHT = 32
_CHIP_PADY = 3


class CategoryPicker(ctk.CTkFrame):
    def __init__(self, master, values: list[str], variable: ctk.StringVar):
        super().__init__(master, fg_color="transparent")
        self._variable = variable
        self._chips: dict[str, ctk.CTkButton] = {}
        self._container = None
        self.set_values(values)
        self._variable.trace_add("write", lambda *_args: self._refresh_highlight())

    def set_values(self, values: list[str]) -> None:
        if self._container is not None:
            self._container.destroy()
        self._chips = {}

        rows_needed = -(-len(values) // _COLUMNS)  # divisão com arredondamento pra cima
        row_height = _CHIP_HEIGHT + _CHIP_PADY * 2
        if rows_needed > _MAX_VISIBLE_ROWS:
            self._container = ctk.CTkScrollableFrame(
                self, fg_color="transparent", height=row_height * _MAX_VISIBLE_ROWS)
        else:
            self._container = ctk.CTkFrame(self, fg_color="transparent")
        self._container.pack(fill="x")

        for index, value in enumerate(values):
            chip = ctk.CTkButton(
                self._container, text=value, height=_CHIP_HEIGHT,
                fg_color="transparent", border_width=1, border_color=theme.BORDER_ACCENT,
                text_color=theme.TEXT_PRIMARY,
                command=lambda v=value: self._select(v))
            chip.grid(row=index // _COLUMNS, column=index % _COLUMNS,
                      sticky="ew", padx=3, pady=_CHIP_PADY)
            self._chips[value] = chip

        self._refresh_highlight()

    def _select(self, value: str) -> None:
        self._variable.set(value)

    def _refresh_highlight(self) -> None:
        selected = self._variable.get()
        for value, chip in self._chips.items():
            if value == selected:
                chip.configure(fg_color=theme.INDIGO, text_color=theme.TEXT_ON_BLACK)
            else:
                chip.configure(fg_color="transparent", text_color=theme.TEXT_PRIMARY)
