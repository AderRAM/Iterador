"""Gráfico de pizza do consumo do mês, por categoria. Ver Guide/file-map.md.

Desenhado num tkinter.Canvas puro (sem dependência nova tipo matplotlib) — fundo sempre Carbon
Black, igual ao gráfico "Alocações Financeiras" da planilha original do usuário (ver
Guide/spreadsheet-reference.md), independente do tema claro/escuro do resto do app. Cada fatia
usa a cor da categoria (`theme.category_color`, ver ADR-0014) — mesma cor que aparece na lista de
lançamentos, pra servir de legenda visual consistente. As 5 categorias fixas têm cor própria;
categorias personalizadas (ver ADR-0028) caem numa paleta auxiliar por hash do nome — o gráfico
em si não sabe nem precisa saber quantas categorias existem, já itera genericamente sobre o que
vier em `totals_by_label`. Legenda em grade (`_LEGEND_ROWS_PER_COLUMN`), não coluna única — com
muitas categorias no mês, cresce em largura em vez de virar uma lista infinitamente alta.

O canvas de desenho é `self._pie_canvas`, não `self._canvas` — `CTkFrame` (a superclasse) já
usa `self._canvas` internamente pro seu próprio fundo arredondado, e é esse canvas interno que
`_set_appearance_mode()` recolore quando o tema muda. Sobrescrever `self._canvas` aqui quebrava
silenciosamente esse mecanismo: o fundo do frame ficava congelado na cor de quando foi criado,
não acompanhava mais o claro/escuro (relato do usuário).
"""

import tkinter as tk

import customtkinter as ctk

from iterador_ui import theme

_SIZE = 140
_LEGEND_ROWS_PER_COLUMN = 4


class ConsumptionChart(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=theme.BG_SURFACE, corner_radius=10)

        ctk.CTkLabel(
            self, text="Consumo do mês", text_color=theme.TEXT_PRIMARY,
            font=ctk.CTkFont(weight="bold"),
        ).pack(anchor="w", padx=14, pady=(12, 4))

        self._pie_canvas = tk.Canvas(
            self, width=_SIZE, height=_SIZE, bg=theme.CARBON_BLACK, highlightthickness=0)
        self._pie_canvas.pack(padx=14, pady=(0, 8))

        self._legend_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._legend_frame.pack(fill="x", padx=14, pady=(0, 12))

        # Últimos totais desenhados — ver `update_data()`.
        self._last_totals: dict | None = None

    def update_data(self, totals_by_label: dict) -> None:
        """totals_by_label: {descrição: valor_em_reais (positivo)}."""
        if totals_by_label == self._last_totals:
            # Nada mudou desde o último desenho (ex. Desfazer/Refazer de uma ação que não afeta
            # nenhuma categoria, como reordenar ou alternar Pago/A pagar) — sem isso, o gráfico
            # inteiro (canvas + legenda) era destruído e reconstruído do zero em toda chamada de
            # `DashboardView.refresh()`, mesmo quando o resultado final seria pixel-a-pixel igual
            # (relato do usuário: "alguns valores piscam mesmo que eles não precisam mudar"). Ver
            # o mesmo princípio já aplicado em `MonthSelector.update_months()` (ADR-0026).
            return
        self._last_totals = dict(totals_by_label)

        self._pie_canvas.delete("all")
        for child in self._legend_frame.winfo_children():
            child.destroy()

        total = sum(totals_by_label.values())
        if total <= 0:
            self._pie_canvas.create_text(
                _SIZE / 2, _SIZE / 2, text="Sem despesas\nainda", fill=theme.TEXT_ON_BLACK,
                justify="center")
            return

        margin = 10
        start_angle = 90.0  # começa no topo, sentido horário
        for index, (label, value) in enumerate(
                sorted(totals_by_label.items(), key=lambda kv: -kv[1])):
            fraction = value / total
            extent = -360.0 * fraction  # negativo = sentido horário no Canvas
            # -360 exato (uma única categoria = 100%) faz o Canvas do Tk desenhar um arco
            # degenerado (bbox de poucos pixels em vez do círculo inteiro) — bug conhecido do
            # create_arc com volta completa. -359.99 é visualmente idêntico e não tem esse
            # problema (relato do usuário: "gráfico pizza não aparece").
            if extent <= -360.0:
                extent = -359.99
            color = theme.category_color(label)
            self._pie_canvas.create_arc(
                margin, margin, _SIZE - margin, _SIZE - margin,
                start=start_angle, extent=extent, fill=color, outline=theme.CARBON_BLACK)
            start_angle += extent

        # Borda preta fina rente às fatias, depois a borda branca um pouco mais afastada do
        # centro — o espaço entre as duas (fundo do canvas, sempre preto) é a "borda preta fina
        # entre a borda branca e o gráfico" pedida pelo usuário.
        self._pie_canvas.create_oval(
            margin, margin, _SIZE - margin, _SIZE - margin, outline="#000000", width=1)
        white_margin = margin - 4
        self._pie_canvas.create_oval(
            white_margin, white_margin, _SIZE - white_margin, _SIZE - white_margin,
            outline="#FFFFFF", width=2)

        # Grade em vez de uma coluna só — com poucas categorias (caso mais comum) o resultado é
        # idêntico a uma coluna; a partir da 5ª categoria, uma coluna nova a cada
        # `_LEGEND_ROWS_PER_COLUMN` entradas em vez de uma lista cada vez mais alta (ver
        # ADR-0028 — "organizar o espaço" pedido pelo usuário quando categorias novas aparecem).
        for index, (label, value) in enumerate(
                sorted(totals_by_label.items(), key=lambda kv: -kv[1])):
            fraction = value / total
            color = theme.category_color(label)
            row = ctk.CTkFrame(self._legend_frame, fg_color="transparent")
            row.grid(row=index % _LEGEND_ROWS_PER_COLUMN, column=index // _LEGEND_ROWS_PER_COLUMN,
                      sticky="w", padx=(0, 10), pady=1)
            dot = tk.Canvas(row, width=10, height=10, highlightthickness=0,
                             bg=self._apply_appearance_mode(theme.BG_SURFACE))
            dot.pack(side="left", padx=(0, 6))
            dot.create_oval(1, 1, 9, 9, fill=color, outline="")
            ctk.CTkLabel(
                row, text=f"{label} ({fraction * 100:.0f}%)", text_color=theme.TEXT_PRIMARY,
                font=ctk.CTkFont(size=11),
            ).pack(side="left")
