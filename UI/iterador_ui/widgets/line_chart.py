"""Gráfico de linha simples (tkinter.Canvas puro, sem matplotlib). Duas formas de uso:

- `update_data()` — série única, com destaque pro valor mínimo e máximo. Primeiro uso: histórico
  mensal do CDI na Wiki (ver Guide/decisions/0021-cdi-history-from-bcb.md).
- `update_series()` — várias séries (uma linha por categoria + legenda com variação % vs mês
  anterior), usado pelo comparativo mensal do Início (ver ADR-0029/0032). As duas são
  independentes — cada instância de `LineChart` usa uma ou outra, nunca as duas. Clicar numa
  categoria na legenda entra em "modo foco" pra ela (ver `_toggle_focus`) — prioriza essa
  categoria no hover e esmaece as outras, útil quando várias linhas se sobrepõem no gráfico.

Mesmo estilo do `ConsumptionChart` (fundo Carbon Black fixo, independente do tema claro/escuro).
Pelo mesmo motivo, o canvas de desenho é `self._plot_canvas`, não `self._canvas` — ver o
comentário equivalente em `consumption_chart.py` (`self._canvas` já é usado internamente pelo
`CTkFrame`, e sobrescrever quebra o auto-recolorir do fundo do frame quando o tema muda).

A curva não usa o `smooth=True` do Canvas (que só arredonda os cantos da linha reta ligando os
pontos — com pontos muito próximos uns dos outros ainda parece "serrilhado"/quadriculado).
Em vez disso, cada trecho entre dois pontos é uma parábola de verdade (interpolação quadrática
de Lagrange usando o ponto e seus dois vizinhos), amostrada em vários pontos intermediários —
daí a curva ficar suave mesmo com poucos dados reais.
"""

import tkinter as tk

import customtkinter as ctk

from iterador_ui import theme

_WIDTH = 640
_HEIGHT = 190
_PADDING = 24
_SAMPLES_PER_SEGMENT = 12
_MAX_AXIS_LABELS = 6
_LEGEND_ROWS_PER_COLUMN = 4
_HOVER_RADIUS_PX = 14
_HOVER_SHADE_AMOUNT = 0.3
_FOCUS_DIM_AMOUNT = -0.55


def _format_reais(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _quadratic_lagrange(t: float, nodes: tuple[float, float, float],
                         values: tuple[float, float, float]) -> float:
    """Valor em `t` da parábola que passa exatamente pelos 3 pontos (nodes[i], values[i])."""
    i0, i1, i2 = nodes
    v0, v1, v2 = values
    l0 = (t - i1) * (t - i2) / ((i0 - i1) * (i0 - i2))
    l1 = (t - i0) * (t - i2) / ((i1 - i0) * (i1 - i2))
    l2 = (t - i0) * (t - i1) / ((i2 - i0) * (i2 - i1))
    return v0 * l0 + v1 * l1 + v2 * l2


def _smooth_curve(values: list[float]) -> list[tuple[float, float]]:
    """Amostra a curva suave (parábola por trecho) entre `values`. Retorna pares
    (índice_fracionário, valor_interpolado); em cada índice inteiro o valor bate exatamente com
    o dado real (a parábola passa pelos pontos, não só perto deles)."""
    n = len(values)
    if n < 3:
        return list(enumerate(values))

    sampled: list[tuple[float, float]] = []
    last_segment = n - 2
    for i in range(n - 1):
        nodes = (i - 1, i, i + 1) if i > 0 else (i, i + 1, i + 2)
        segment_values = tuple(values[j] for j in nodes)
        steps = _SAMPLES_PER_SEGMENT if i < last_segment else _SAMPLES_PER_SEGMENT + 1
        for step in range(steps):
            t = i + step / _SAMPLES_PER_SEGMENT
            sampled.append((t, _quadratic_lagrange(t, nodes, segment_values)))
    return sampled


def _format_delta(current: float, previous: float) -> tuple[str, str]:
    """Variação percentual entre o mês anterior e o atual, pro resumo numérico de
    `update_series()`. Casos sem percentual bem definido (categoria nova ou zerada) ganham um
    rótulo textual em vez de uma divisão por zero."""
    if previous <= 0 and current <= 0:
        return "–", theme.TEXT_PRIMARY
    if previous <= 0:
        return "novo", theme.TEXT_PRIMARY
    if current <= 0:
        return "-100%", theme.VALUE_EXPENSE
    pct = (current - previous) / previous * 100
    sign = "+" if pct >= 0 else ""
    color = theme.VALUE_INCOME if pct >= 0 else theme.VALUE_EXPENSE
    return f"{sign}{pct:.0f}%", color


class LineChart(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=theme.BG_SURFACE, corner_radius=10)
        self._plot_canvas = tk.Canvas(
            self, width=_WIDTH, height=_HEIGHT, bg=theme.CARBON_BLACK, highlightthickness=0)
        self._plot_canvas.pack(padx=14, pady=(14, 4))
        # Só usada por `update_series()` (multi-série, ver ADR-0029) — `update_data()` (série
        # única, usada pelo histórico do CDI na Wiki) nunca escreve aqui, sempre fica vazia
        # nesse caso.
        self._legend_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._legend_frame.pack(fill="x", padx=14, pady=(0, 12))

        # Hover só existe em modo `update_series()` (ver ADR-0030) — `None` desliga (modo
        # `update_data()`, série única, sem interação). Guarda por categoria: id da linha no
        # canvas (pra recolorir via itemconfig sem redesenhar tudo), cor normal (pra restaurar) e
        # os pontos reais em coords de canvas + valor (pra achar a categoria mais próxima do
        # mouse e mostrar o valor certo no tooltip).
        self._hover_state: dict | None = None
        self._plot_canvas.bind("<Motion>", self._on_motion)
        self._plot_canvas.bind("<Leave>", self._on_leave)
        # Clicar na própria linha da categoria no gráfico foca ela, mesmo efeito de clicar no
        # nome dela na legenda (ver `_toggle_focus`) — pedido do usuário depois do modo foco já
        # existir só via legenda.
        self._plot_canvas.bind("<Button-1>", self._on_canvas_click)

        # Tooltip como uma janela `Toplevel` sem decoração, não como itens desenhados dentro do
        # `_plot_canvas` — um Canvas nunca desenha fora da própria área (é cortado), então perto
        # da borda do gráfico o texto ficava cortado em vez de aparecer por cima do resto da tela
        # (relato do usuário, com screenshot). Uma janela flutuante de verdade não tem esse
        # limite: pode se sobrepor a qualquer outro widget/frame do app, só é cortada pelas
        # bordas da TELA (comportamento normal de qualquer tooltip). Criada uma vez, reaproveitada
        # via `deiconify()`/`withdraw()`/`geometry()` em vez de criar/destruir a cada hover.
        self._tooltip_window = tk.Toplevel(self)
        self._tooltip_window.overrideredirect(True)
        self._tooltip_window.attributes("-topmost", True)
        self._tooltip_window.withdraw()
        self._tooltip_label = tk.Label(
            self._tooltip_window, justify="left", font=("DejaVu Sans", 8),
            bg=theme.CARBON_BLACK, fg=theme.TEXT_ON_BLACK, padx=6, pady=4)
        self._tooltip_label.pack()

        # Últimos dados desenhados — ver `update_data()`/`update_series()`. Só um dos dois é
        # usado por instância (as duas formas são independentes, ver docstring do módulo).
        self._last_points: tuple | None = None
        self._last_series: dict | None = None

    def update_data(self, points: list[tuple[str, float]], granularity: str = "mensal") -> None:
        """points: [(rótulo_data, valor), ...] em ordem cronológica. `granularity` só aparece
        na legenda embaixo do gráfico (ex. "mensal", "anual", "diário"), pra deixar claro o que
        cada ponto representa sem precisar adivinhar pelos rótulos do eixo."""
        cache_key = (tuple(points), granularity)
        if cache_key == self._last_points:
            # Nada mudou desde o último desenho — evita destruir/recriar o canvas à toa (mesmo
            # motivo de `ConsumptionChart.update_data()`).
            return
        self._last_points = cache_key

        self._plot_canvas.delete("all")
        for child in self._legend_frame.winfo_children():
            child.destroy()
        self._hover_state = None  # sem hover em modo série única (ver __init__)
        self._tooltip_window.withdraw()

        if len(points) < 2:
            self._plot_canvas.create_text(
                _WIDTH / 2, _HEIGHT / 2, text="Sem dados suficientes ainda",
                fill=theme.TEXT_ON_BLACK, justify="center")
            return

        labels = [label for label, _ in points]
        values = [value for _, value in points]
        min_value, max_value = min(values), max(values)
        value_range = (max_value - min_value) or 1.0

        plot_left, plot_right = _PADDING, _WIDTH - _PADDING
        plot_top, plot_bottom = _PADDING, _HEIGHT - _PADDING - 16  # -16: linha de legenda embaixo
        plot_width = plot_right - plot_left
        plot_height = plot_bottom - plot_top
        last_index = len(points) - 1

        def to_xy(index: float, value: float) -> tuple[float, float]:
            x = plot_left + (index / last_index) * plot_width
            y = plot_bottom - ((value - min_value) / value_range) * plot_height
            # A parábola de `_smooth_curve` passa exatamente pelos dados reais, mas entre dois
            # pontos pode ultrapassar o maior/menor valor deles (artefato normal de interpolação
            # quadrática, mais visível quando um pico é bem mais alto que os vizinhos) — sem o
            # grampo, a curva desenhada passava do topo/fundo da área do gráfico e invadia o
            # espaço dos rótulos de mês embaixo.
            return x, min(max(y, plot_top), plot_bottom)

        coords = []
        for index, value in _smooth_curve(values):
            coords.extend(to_xy(index, value))
        self._plot_canvas.create_line(
            *coords, fill=theme.ACCENT_HIGHLIGHT, width=2,
            capstyle=tk.ROUND, joinstyle=tk.ROUND)

        min_index = values.index(min_value)
        max_index = values.index(max_value)
        for index, value, color in (
            (min_index, min_value, theme.VALUE_EXPENSE),
            (max_index, max_value, theme.VALUE_INCOME),
        ):
            x, y = to_xy(index, value)
            self._plot_canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill=color, outline="")
            # Rótulo do lado com mais espaço — evita cortar em cima/embaixo do canvas.
            label_y = y - 14 if y > plot_top + 24 else y + 14
            self._plot_canvas.create_text(
                x, label_y, text=f"{value:.2f}%", fill=color,
                font=("DejaVu Sans", 9, "bold"))

        # Rótulos de data espalhados no eixo (não só primeiro/último) — sem isso não dava pra
        # saber que ponto do meio corresponde a que mês (relato do usuário).
        label_count = min(_MAX_AXIS_LABELS, len(points))
        if label_count > 1:
            label_positions = [
                round(i * last_index / (label_count - 1)) for i in range(label_count)]
        else:
            label_positions = [0]
        for index in sorted(set(label_positions)):
            x, _ = to_xy(index, values[index])
            if index == 0:
                anchor = "w"
            elif index == last_index:
                anchor = "e"
            else:
                anchor = "center"
            self._plot_canvas.create_text(
                x, plot_bottom + 8, text=labels[index], fill=theme.TEXT_ON_BLACK,
                font=("DejaVu Sans", 8), anchor=anchor)

        # Legenda de granularidade — deixa explícito que cada ponto é uma média mensal (ou o
        # que for passado em `granularity`), não um valor diário (relato do usuário).
        self._plot_canvas.create_text(
            plot_left, _HEIGHT - 6,
            text=f"Cada ponto: média {granularity} · {labels[0]} a {labels[-1]}",
            fill=theme.TEXT_ON_BLACK, font=("DejaVu Sans", 8), anchor="w")

    def update_series(self, series: dict[str, list[tuple[str, float]]]) -> None:
        """series: {categoria: [(rótulo_mês, valor), ...]} — todas as categorias com a MESMA
        sequência de rótulos de mês (mesmo eixo X, ver `DashboardView._monthly_category_series`,
        ADR-0029). Uma linha suave por categoria, cor de `theme.category_color` (mesma cor da
        fatia no gráfico de pizza) — reforça visualmente "isso é o mesmo recorte, ao longo do
        tempo". Legenda embutida abaixo do canvas: bolinha + nome + variação % vs mês anterior
        (verde/vermelho, ver `_format_delta`) — é o "resumo em números do que mudou" pedido, sem
        precisar de um painel separado. Sem marcadores de mínimo/máximo (ambíguos com várias
        linhas na tela ao mesmo tempo, diferente de `update_data()`)."""
        if series == self._last_series:
            # Nada mudou desde o último desenho (ex. Desfazer/Refazer de uma ação que não afeta
            # nenhuma categoria, como reordenar ou alternar Pago/A pagar) — sem isso, a linha
            # inteira + legenda eram destruídas e reconstruídas do zero em toda chamada de
            # `DashboardView.refresh()`, mesmo quando o resultado seria idêntico (relato do
            # usuário: "alguns valores piscam mesmo que eles não precisam mudar"). Pulando aqui
            # também preserva o modo foco/hover tal como estava, sem precisar "restaurar" nada.
            return
        self._last_series = {category: list(points) for category, points in series.items()}

        # Lido ANTES de zerar `self._hover_state` logo abaixo — senão a categoria focada
        # (`_toggle_focus`) nunca sobreviveria a um refresh (ver uso mais abaixo).
        previous_focused = self._hover_state["focused"] if self._hover_state else None

        self._plot_canvas.delete("all")
        for child in self._legend_frame.winfo_children():
            child.destroy()
        self._hover_state = None
        self._tooltip_window.withdraw()

        if not series or len(next(iter(series.values()))) < 2:
            self._plot_canvas.create_text(
                _WIDTH / 2, _HEIGHT / 2, text="Sem dados suficientes ainda",
                fill=theme.TEXT_ON_BLACK, justify="center")
            return

        labels = [label for label, _ in next(iter(series.values()))]
        all_values = [value for points in series.values() for _, value in points]
        min_value, max_value = min(all_values), max(all_values)
        value_range = (max_value - min_value) or 1.0

        plot_left, plot_right = _PADDING, _WIDTH - _PADDING
        plot_top, plot_bottom = _PADDING, _HEIGHT - _PADDING - 16
        plot_width = plot_right - plot_left
        plot_height = plot_bottom - plot_top
        last_index = len(labels) - 1

        def to_xy(index: float, value: float) -> tuple[float, float]:
            x = plot_left + (index / last_index) * plot_width
            y = plot_bottom - ((value - min_value) / value_range) * plot_height
            # Grampo pro mesmo motivo de `update_data()` acima — a interpolação quadrática entre
            # pontos pode ultrapassar o maior/menor valor real, invadindo o espaço dos rótulos.
            return x, min(max(y, plot_top), plot_bottom)

        # Categoria com maior valor no mês mais recente primeiro — mesma ordenação do gráfico de
        # pizza (`ConsumptionChart`, maior fatia primeiro), pra bater visualmente com ele.
        ordered = sorted(series.items(), key=lambda kv: -kv[1][-1][1])

        line_ids: dict[str, int] = {}
        colors: dict[str, str] = {}
        real_points: dict[str, list[tuple[float, float, float]]] = {}
        # Pontos da curva já suavizada, em coordenadas de canvas — os MESMOS pontos usados pra
        # desenhar a linha (não os dados brutos por mês). O hover usa isso pra achar a linha mais
        # perto do mouse: comparar só contra os pontos de dado (1 a cada ~5-6 meses, bem espaçados
        # no eixo X) fazia o "contato" da linha com o mouse parecer impreciso longe de um ponto de
        # dado exato — a curva real ali podia estar bem longe do dado mais próximo (relato do
        # usuário, com screenshot).
        dense_points: dict[str, list[tuple[float, float]]] = {}
        for category, points in ordered:
            values = [value for _, value in points]
            color = theme.category_color(category)
            colors[category] = color
            real_points[category] = [
                (*to_xy(index, value), value) for index, value in enumerate(values)]
            curve = [to_xy(index, value) for index, value in _smooth_curve(values)]
            dense_points[category] = curve
            coords = [coordinate for point in curve for coordinate in point]
            line_ids[category] = self._plot_canvas.create_line(
                *coords, fill=color, width=2, capstyle=tk.ROUND, joinstyle=tk.ROUND)

        label_count = min(_MAX_AXIS_LABELS, len(labels))
        if label_count > 1:
            label_positions = [
                round(i * last_index / (label_count - 1)) for i in range(label_count)]
        else:
            label_positions = [0]
        for index in sorted(set(label_positions)):
            x = plot_left + (index / last_index) * plot_width if last_index else plot_left
            if index == 0:
                anchor = "w"
            elif index == last_index:
                anchor = "e"
            else:
                anchor = "center"
            self._plot_canvas.create_text(
                x, plot_bottom + 8, text=labels[index], fill=theme.TEXT_ON_BLACK,
                font=("DejaVu Sans", 8), anchor=anchor)

        # Categoria focada (clicada na legenda, ver `_toggle_focus`) sobrevive a este refresh se
        # ainda existir no mês selecionado — sem isso, qualquer `refresh()` do Início (troca de
        # mês, marcar Pago/A pagar, etc.) desfaria o foco escolhido pelo usuário sem aviso.
        focused = previous_focused if previous_focused in colors else None

        legend_rows: dict[str, ctk.CTkFrame] = {}
        for index, (category, points) in enumerate(ordered):
            values = [value for _, value in points]
            delta_text, delta_color = _format_delta(values[-1], values[-2])
            color = theme.category_color(category)
            row = ctk.CTkFrame(self._legend_frame, fg_color="transparent", corner_radius=6)
            row.grid(row=index % _LEGEND_ROWS_PER_COLUMN, column=index // _LEGEND_ROWS_PER_COLUMN,
                      sticky="w", padx=(0, 14), pady=1)
            dot = tk.Canvas(row, width=10, height=10, highlightthickness=0,
                             bg=self._apply_appearance_mode(theme.BG_SURFACE))
            dot.pack(side="left", padx=(6, 6))
            dot.create_oval(1, 1, 9, 9, fill=color, outline="")
            name_label = ctk.CTkLabel(
                row, text=category, text_color=theme.TEXT_PRIMARY, font=ctk.CTkFont(size=11))
            name_label.pack(side="left")
            delta_label = ctk.CTkLabel(
                row, text=f" {delta_text}", text_color=delta_color,
                font=ctk.CTkFont(size=11, weight="bold"))
            delta_label.pack(side="left", padx=(0, 6))
            legend_rows[category] = row

            # "Apertar na categoria vai focar ela" — clicar em qualquer parte da linha da
            # legenda alterna o modo foco pra essa categoria (ver `_toggle_focus`). Precisa
            # bindar cada widget filho, não só `row`: um clique em cima de um filho nunca chega
            # no pai em Tk.
            for widget in (row, dot, name_label, delta_label):
                widget.bind("<Button-1>", lambda _event, c=category: self._toggle_focus(c))

        self._hover_state = {
            "line_ids": line_ids,
            "colors": colors,
            "points": real_points,
            "dense_points": dense_points,
            "plot_left": plot_left,
            "plot_width": plot_width,
            "last_index": last_index,
            "labels": labels,
            "hovered": [],
            "focused": focused,
            "legend_rows": legend_rows,
        }
        self._apply_focus_visuals()

    def _toggle_focus(self, category: str) -> None:
        """Clicar numa categoria na legenda alterna o modo foco pra ela — clicar de novo (ou na
        mesma categoria já focada) desliga. Em foco, essa categoria fica na cor cheia e por cima
        das outras (`tag_raise`); as demais ficam esmaecidas (`_FOCUS_DIM_AMOUNT`) — útil quando
        várias linhas se sobrepõem no gráfico e fica difícil saber qual é qual. O hover
        (`_on_motion`) também passa a priorizar a categoria focada dentro do raio de tolerância,
        mesmo que outra esteja pixel a pixel mais perto do mouse naquele ponto."""
        state = self._hover_state
        if state is None:
            return
        state["focused"] = None if state["focused"] == category else category
        self._apply_focus_visuals()

    def _apply_focus_visuals(self) -> None:
        state = self._hover_state
        if state is None:
            return
        focused = state["focused"]
        for category, line_id in state["line_ids"].items():
            self._plot_canvas.itemconfig(line_id, fill=self._display_color(state, category))
            row = state["legend_rows"].get(category)
            if row is not None:
                row.configure(fg_color=theme.BG_APP if category == focused else "transparent")
        if focused is not None:
            self._plot_canvas.tag_raise(state["line_ids"][focused])

    def _display_color(self, state: dict, category: str) -> str:
        """Cor "de repouso" da linha (sem hover) — cheia se não tem foco ativo ou essa é a
        categoria focada, esmaecida (`_FOCUS_DIM_AMOUNT`) senão. `_on_motion`/`_on_leave` restauram
        pra isso em vez da cor fixa, senão sair do hover apagaria o esmaecimento do modo foco."""
        color = state["colors"][category]
        focused = state["focused"]
        if focused is not None and category != focused:
            return theme.shade_color(color, _FOCUS_DIM_AMOUNT)
        return color

    @staticmethod
    def _sample_index_for_x(state: dict, x: float) -> int:
        # Testa contra os pontos da curva JÁ SUAVIZADA (mesmos pixels desenhados), não contra o
        # dado bruto de cada mês — comparar só com o dado bruto (bem espaçado no eixo X) fazia o
        # "contato" da linha com o mouse parecer impreciso longe de um ponto de dado exato
        # (relato do usuário, com screenshot): a curva real ali podia estar bem longe do dado
        # mais próximo. Todas as categorias amostram a curva nos MESMOS instantes (só o valor
        # muda, não a posição X de cada amostra), então um único índice de amostra serve pra
        # todas — não precisa buscar por categoria.
        any_curve = next(iter(state["dense_points"].values()))
        sample_index = round((x - state["plot_left"]) / state["plot_width"] * (len(any_curve) - 1))
        return max(0, min(len(any_curve) - 1, sample_index))

    def _category_at(self, event) -> str | None:
        """Categoria cuja linha está mais perto de `event` (dentro de `_HOVER_RADIUS_PX`), ou
        `None` — usado por `_on_canvas_click` pra saber em qual linha o clique caiu. Ignora o
        foco de propósito (diferente de `_on_motion`): clicar deve sempre mirar a linha mais
        perto do ponto exato do clique, não a que já está focada."""
        state = self._hover_state
        if state is None or state["last_index"] <= 0:
            return None
        sample_index = self._sample_index_for_x(state, event.x)
        best_category = None
        best_distance = _HOVER_RADIUS_PX
        for category, curve in state["dense_points"].items():
            _, y = curve[sample_index]
            distance = abs(event.y - y)
            if distance < best_distance:
                best_distance = distance
                best_category = category
        return best_category

    def _on_canvas_click(self, event) -> None:
        """Clicar em cima da própria linha de uma categoria no gráfico foca ela — mesmo efeito
        de clicar no nome dela na legenda (ver `_toggle_focus`)."""
        category = self._category_at(event)
        if category is not None:
            self._toggle_focus(category)

    def _on_motion(self, event) -> None:
        state = self._hover_state
        if state is None or state["last_index"] <= 0:
            return

        sample_index = self._sample_index_for_x(state, event.x)
        focused = state["focused"]
        # Toda categoria com a curva dentro do raio de tolerância naquele ponto — não só a mais
        # próxima. Ordenado por altura na tela (mais alta = maior valor primeiro), mesma
        # convenção de "maior primeiro" do resto do widget.
        overlapping = sorted(
            (category for category, curve in state["dense_points"].items()
             if abs(event.y - curve[sample_index][1]) < _HOVER_RADIUS_PX),
            key=lambda category: state["dense_points"][category][sample_index][1])

        if focused is not None:
            # Modo foco: a categoria focada vence sozinha se estiver dentro do raio, mesmo que
            # não seja a pixel-a-pixel mais próxima — é exatamente pra desambiguar sobreposição
            # que o foco existe (relato do usuário). Fora do raio dela, cai pra "mais próxima
            # entre todas" de sempre (uma só, sem listar sobreposição — foco ativo simplifica
            # pra uma categoria de cada vez).
            if focused in overlapping:
                new_hovered = [focused]
            elif overlapping:
                new_hovered = [min(
                    overlapping,
                    key=lambda c: abs(event.y - state["dense_points"][c][sample_index][1]))]
            else:
                new_hovered = []
        else:
            # Sem foco: se mais de uma categoria se sobrepõe naquele ponto, lista todas — em vez
            # de escolher uma "vencedora" arbitrária quando não dá pra saber qual o usuário quer
            # (relato do usuário: sem foco ativo, mostrar todas as que se sobrepõem ali).
            new_hovered = overlapping

        # Índice do mês mais próximo (pro texto do tooltip — mês/valor de verdade, não um valor
        # interpolado entre dois meses).
        raw_index = (event.x - state["plot_left"]) / state["plot_width"] * state["last_index"]
        month_index = max(0, min(state["last_index"], round(raw_index)))

        previous = state["hovered"]
        if new_hovered == previous:
            if new_hovered:
                self._show_tooltip(state, new_hovered, month_index, sample_index)
            return

        for category in previous:
            self._plot_canvas.itemconfig(
                state["line_ids"][category], fill=self._display_color(state, category), width=2)
        state["hovered"] = new_hovered
        if not new_hovered:
            self._clear_tooltip()
            return

        # "A linha deve mudar a tonalidade um pouco com a presença do mouse" — mesmo
        # theme.shade_color() já usado pro hover do botão Pago/A pagar (ver correção de
        # performance desta sessão), aplicado em toda categoria em hover (uma ou várias, se
        # sobrepondo). Parte da cor CHEIA (`state["colors"]`), não da esmaecida — hoverar uma
        # linha esmaecida pelo modo foco deve trazer ela de volta ao normal + destaque.
        for category in new_hovered:
            highlighted = theme.shade_color(state["colors"][category], _HOVER_SHADE_AMOUNT)
            self._plot_canvas.itemconfig(state["line_ids"][category], fill=highlighted, width=3)
        self._show_tooltip(state, new_hovered, month_index, sample_index)

    def _on_leave(self, _event) -> None:
        state = self._hover_state
        if state is None:
            return
        for category in state["hovered"]:
            self._plot_canvas.itemconfig(
                state["line_ids"][category], fill=self._display_color(state, category), width=2)
        state["hovered"] = []
        self._clear_tooltip()

    def _clear_tooltip(self) -> None:
        self._tooltip_window.withdraw()

    def _show_tooltip(self, state: dict, categories: list[str], month_index: int,
                       sample_index: int) -> None:
        # Ancorado no ponto da CURVA sob o cursor (`sample_index`, mesma resolução usada no
        # hit-test), não no dado bruto do mês mais próximo — o texto sempre acompanha de perto o
        # cursor, mesmo hoverando entre dois meses; só o conteúdo (mês/valor) usa o mês mais
        # próximo, que é a informação real que existe (relato do usuário: tooltip parecia
        # "grudado" longe do mouse antes desta correção).
        points = [state["dense_points"][category][sample_index] for category in categories]
        anchor_x = points[0][0]
        anchor_y = min(y for _, y in points)

        if len(categories) == 1:
            category = categories[0]
            value = state["points"][category][month_index][2]
            text = f"{category}\n{state['labels'][month_index]}: {_format_reais(value)}"
            outline_color = state["colors"][category]
        else:
            # Várias categorias se sobrepõem nesse ponto e nenhuma está focada — lista todas em
            # vez de escolher uma vencedora arbitrária (relato do usuário).
            lines = [state["labels"][month_index]]
            for category in categories:
                value = state["points"][category][month_index][2]
                lines.append(f"{category}: {_format_reais(value)}")
            text = "\n".join(lines)
            outline_color = theme.TEXT_ON_BLACK  # várias cores ali — nenhuma cor única faz sentido

        # Janela flutuante (ver __init__) em vez de itens de canvas — pode se sobrepor a
        # qualquer frame vizinho em vez de ser cortada na borda do gráfico (relato do usuário,
        # com screenshot). Posição em coordenadas de TELA: converte o ponto local do canvas
        # somando `winfo_rootx()/rooty()` do próprio canvas.
        self._tooltip_label.configure(
            text=text, highlightthickness=1, highlightbackground=outline_color,
            highlightcolor=outline_color)
        self._tooltip_window.update_idletasks()
        width = self._tooltip_window.winfo_reqwidth()
        height = self._tooltip_window.winfo_reqheight()

        canvas_x = self._plot_canvas.winfo_rootx()
        canvas_y = self._plot_canvas.winfo_rooty()
        screen_width = self._tooltip_window.winfo_screenwidth()
        screen_height = self._tooltip_window.winfo_screenheight()

        # Por padrão, acima e à direita do ponto — só os limites da TELA importam agora (não mais
        # os limites do canvas/frame, já que a janela pode se sobrepor a eles de propósito).
        x = canvas_x + anchor_x
        y = canvas_y + anchor_y - 8 - height
        if x + width > screen_width:
            x = canvas_x + anchor_x - width  # joga pra esquerda do ponto em vez de sair da tela
        if y < 0:
            y = canvas_y + anchor_y + 8  # joga pra baixo do ponto em vez de sair por cima da tela
        x = max(0, x)
        y = min(y, screen_height - height)

        self._tooltip_window.geometry(f"{width}x{height}+{int(x)}+{int(y)}")
        self._tooltip_window.deiconify()
        self._tooltip_window.lift()
