"""Tela inicial: navegação por mês, gráfico de consumo, total do mês e a lista de lançamentos
(com adicionar/editar/remover/desfazer). A lista de transações vivia numa aba própria antes — o
usuário pediu pra juntar tudo aqui, mais prático. Ver
Guide/decisions/0010-dashboard-hosts-transactions.md,
Guide/decisions/0011-transaction-date-and-column-list.md,
Guide/decisions/0012-fixed-categories-and-investment-link.md,
Guide/decisions/0016-monthly-transaction-navigation.md,
Guide/decisions/0019-remove-month-with-undo.md e
Guide/decisions/0020-color-profile-system.md.

Tudo (gráfico, cards, lista) é filtrado pelo mês selecionado no `MonthSelector` — antes "Total
do mês" somava tudo desde sempre, apesar do nome.

A lista usa grid (não pack) pra Data/Status/Valor/Editar/Remover ficarem alinhados em colunas
de verdade entre todas as linhas, independente do tamanho de cada descrição/valor. Cada
lançamento ocupa uma linha de grid de dados + uma linha de `Divider` fino logo abaixo (ver
ADR-0020) — por isso as linhas de dado ficam em índices pares (`_row_of(offset)`).
"""

import calendar
import os
import time
import traceback
from pathlib import Path

import customtkinter as ctk
from PIL import Image

from iterador_ui import backend_bridge, theme
from iterador_ui.transaction_commands import (
    AddMonthCommand, CreateTransactionCommand, DeleteTransactionCommand, RemoveMonthCommand,
    ReorderTransactionCommand, ResetTransactionOrderCommand, ToggleStatusCommand,
    TogglePinCommand, UpdateTransactionCommand,
)
from iterador_ui.undo_stack import UndoStack
from iterador_ui.widgets.confirm_dialog import ConfirmDialog
from iterador_ui.widgets.consumption_chart import ConsumptionChart
from iterador_ui.widgets.dialog_utils import open_singleton
from iterador_ui.widgets.divider import Divider
from iterador_ui.widgets.line_chart import LineChart
from iterador_ui.widgets.month_selector import MonthSelector, month_label
from iterador_ui.widgets.outlined_label import OutlinedLabel
from iterador_ui.widgets.shopping_list_dialog import ShoppingListDialog
from iterador_ui.widgets.stat_card import StatCard
from iterador_ui.widgets.transaction_form_dialog import TransactionFormDialog

_COLUMN_HEADERS = ["", "Data", "", "Descrição", "Categoria", "Status", "Valor", "", ""]

_SEARCH_ICON_PATH = Path(__file__).resolve().parent.parent.parent / "assets" / "search.png"
_HANDLE_ICON_PATH = (
    Path(__file__).resolve().parent.parent.parent / "assets" /
    "sort-arrows-couple-pointing-up-and-down.png")
_RESET_ICON_PATH = Path(__file__).resolve().parent.parent.parent / "assets" / "reset.png"
_RESET_ICON_COLOR = "#FFFFFF"  # branco, pedido do usuário — botão em si já é "quadrado
# transparente com borda azul" (theme.outline_button_style())
_PIN_ON_ICON_PATH = Path(__file__).resolve().parent.parent.parent / "assets" / "Pin-on.png"
_PIN_OFF_ICON_PATH = Path(__file__).resolve().parent.parent.parent / "assets" / "Pin-off.png"
# Azul quando fixado, cinza quando não (pedido do usuário, ver ADR-0034) — mesmo cinza da alça
# de arrastar (`_HANDLE_ICON_LIGHT_COLOR`/`_DARK_COLOR` abaixo) pro "desligado", e a mesma cor
# de destaque azul fixa já usada no resto do app (`theme.INDIGO`) pro "ligado" — sem inventar
# tom novo nenhum.
_PIN_ON_COLOR = theme.INDIGO
# O ícone original é preto sólido — perfeito no modo claro, mas quase invisível no escuro
# (relato do usuário). Recolorido pro mesmo cinza usado pelo placeholder da busca
# ("Pesquisar...", cor padrão do CTkEntry) — mais claro no modo escuro que no claro, mesmo
# princípio de qualquer papel "neutro" do tema (ver `theme.py`).
_HANDLE_ICON_LIGHT_COLOR = "#858585"  # CTk "gray52" — placeholder do CTkEntry no modo claro
_HANDLE_ICON_DARK_COLOR = "#9E9E9E"  # CTk "gray62" — placeholder do CTkEntry no modo escuro


def _tinted(image: Image.Image, hex_color: str) -> Image.Image:
    """Substitui a cor do ícone mantendo o canal alfa original (a arte só varia por
    transparência, não por tons de cinza próprios — ver ícone fonte) — permite reusar o mesmo
    recorte pra qualquer cor sem precisar de um arquivo por tom."""
    alpha = image.convert("RGBA").split()[3]
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    solid = Image.new("RGBA", image.size, (r, g, b, 255))
    solid.putalpha(alpha)
    return solid

# Posição de cada coluna de dado na grid (a coluna 0, a alça de arrastar, e a 2, o pin, não têm
# cabeçalho — ver ADR-0033/0034). "sticky" vazio = comportamento padrão do grid (centralizado),
# igual antes.
_ROW_GRID_SPEC = (
    ("handle", 0, "", (8, 4)),
    ("date", 1, "w", 8),
    ("pin", 2, "", (4, 4)),
    ("description", 3, "w", 8),
    ("category", 4, "w", 8),
    ("status", 5, "", 8),
    ("value", 6, "e", 8),
    ("edit", 7, "", (8, 2)),
    ("remove", 8, "", (2, 8)),
)

# Passos/velocidade do deslize de "abrir espaço" (ver `_animate_row_to_offset`). Precisa caber
# DENTRO de `_DRAG_TARGET_STEP_INTERVAL_MS` (abaixo) — se um "hop" novo chegar antes do deslize
# anterior terminar, ele cancela e reinicia do meio do caminho, e a posição visual nunca alcança
# de verdade o alvo, acumulando atraso (relato do usuário: "o item em si fica pra trás" depois de
# baixar o ritmo pra 20ms sem encurtar isto também — 6×12ms=72ms era bem mais que os 20ms novos).
_DRAG_ANIMATION_STEPS = 2
_DRAG_ANIMATION_INTERVAL_MS = 8

# Ritmo (não a velocidade real do mouse) em que o alvo do arrasto avança uma posição por vez —
# ver `_advance_drag_target`. Um mouse físico normalmente pula mais de uma altura de linha entre
# dois eventos `<B1-Motion>` consecutivos; sem esse limite, um arrasto rápido fazia várias linhas
# (às vezes quase a lista inteira) deslocarem de uma vez só, em vez de uma de cada vez como no
# YouTube Music (relato do usuário). O item arrastado em si também só troca de slot nesse ritmo —
# nunca fica numa posição de pixel solta entre dois slots. Baixado de 100 pra 20ms (relato do
# usuário: 100ms deixava o item lento pra acompanhar o mouse).
_DRAG_TARGET_STEP_INTERVAL_MS = 20
# Ritmo usado só enquanto o mouse está de verdade fora dos limites da lista (não apenas
# encostando na borda) — continua trocando uma linha de cada vez (nunca pula várias juntas), só
# mais rápido, pra alcançar a borda em bem menos tempo. Sem isso, arrastar o mouse pra fora do
# frame parecia "sem resposta"/"perder o track do mouse" por vários segundos (relato do usuário).
# Mantido mais rápido que o ritmo normal acima, mesma proporção de antes (~5x).
_DRAG_TARGET_OUTSIDE_BOUNDS_INTERVAL_MS = 4

# Distância (em pixels da borda VISÍVEL da área rolável) que dispara o auto-scroll durante um
# arrasto — ver `DashboardView._maybe_auto_scroll` (ADR-0033: arrastar pra cima/baixo do que
# está visível na tela, não só fora da lista, deixava o item "preso" sem jeito de alcançar o
# resto da lista mais longa que a tela).
_AUTO_SCROLL_MARGIN_PX = 50

# Log de diagnóstico do arrasto (ver ADR-0033) — desligado por padrão, liga com
# `ITERADOR_DEBUG_DRAG=1 ./scripts/run_ui.sh`. Grava posição do mouse e posição real dos widgets
# da linha arrastada, com timestamp relativo ao início do arrasto (ms), num arquivo em `/tmp`
# (nunca no banco/`~/.iterador`) — pra investigar instabilidade relatada pelo usuário que não deu
# pra reproduzir só com eventos sintéticos (o timing real do mouse importa aqui).
_DRAG_DEBUG = os.environ.get("ITERADOR_DEBUG_DRAG") == "1"
_DRAG_DEBUG_LOG_PATH = "/tmp/iterador_drag_debug.log"


class DashboardView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=theme.BG_APP)
        self._undo_stack = UndoStack()
        self._current_transactions: list = []  # mês selecionado, antes do filtro de busca
        self._rendered_transactions: list = []  # última lista efetivamente exibida (com sort de
        # data aplicado, se ativo) — é o que o arrasto usa pra saber quem está em cada posição.
        # `None` = ordem manual (sort_order do backend); "asc"/"desc" = view local (não persiste,
        # ver ADR-0033), ativada clicando no cabeçalho "Data".
        self._date_sort_mode: str | None = None
        self._drag: dict | None = None  # estado do arrasto em andamento, ver _on_handle_press
        self._drag_tick_id: str | None = None  # agendamento de _advance_drag_target
        self._drag_locked_rows: list[int] = []  # linhas do grid com minsize travado, ver _on_handle_press
        self._global_motion_bind_id: str | None = None  # ver _on_global_motion_check_release
        self._drag_log: list[str] = []  # ver _log_drag/_flush_drag_log (ITERADOR_DEBUG_DRAG=1)
        self._drag_log_start = 0.0

        # Rola a página inteira (cabeçalho, gráfico, cards, painel de mês/lançamentos) — antes só
        # a lista de lançamentos rolava por dentro, então o resto (gráfico, botões) ficava
        # espremido ou cortado quando a janela era menor que o conteúdo (relato do usuário). Fica
        # de fora só a Sidebar (fora desta view, ver IteradorApp) — o scroll aqui é só do
        # conteúdo do Início.
        page_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        page_scroll.pack(fill="both", expand=True)
        # Guardado (não só variável local) — precisa dele durante o arrasto pra saber os limites
        # visíveis da área rolável e rolar sozinho perto da borda (ver `_maybe_auto_scroll`).
        self._page_scroll = page_scroll

        header = ctk.CTkFrame(page_scroll, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(16, 6))
        ctk.CTkLabel(
            header, text="Início", font=ctk.CTkFont(size=20, weight="bold"),
            text_color=theme.TEXT_PRIMARY,
        ).pack(side="left", anchor="s")
        # anchor="s" nos três — alinha as bordas de baixo do texto e dos botões na mesma linha,
        # pra distância até o separador azul embaixo ficar igual dos dois lados (relato do
        # usuário, indicado com setas numeradas 1/2 na tela).
        ctk.CTkButton(
            header, text="↷ Refazer", width=90, command=self._redo,
            **theme.outline_button_style(),
        ).pack(side="right", anchor="s")
        ctk.CTkButton(
            header, text="↶ Desfazer", width=90, command=self._undo,
            **theme.outline_button_style(),
        ).pack(side="right", padx=(0, 8), anchor="s")

        # Separador estrutural (ver ADR-0020) — isola o cabeçalho da tela do resto do conteúdo.
        Divider(page_scroll, color=theme.BORDER_ACCENT).pack(fill="x", padx=24, pady=(0, 6))

        top_row = ctk.CTkFrame(page_scroll, fg_color="transparent")
        top_row.pack(fill="x", padx=24, pady=4)
        self._chart = ConsumptionChart(top_row)
        self._chart.pack(side="left", anchor="nw")
        # Comparativo mensal por categoria (ver ADR-0029) — mesmo espaço que antes ficava vazio
        # ao lado do gráfico de pizza. Uma linha por categoria (mesma cor da fatia da pizza) +
        # legenda com variação % vs mês anterior, calculado em `_monthly_category_series()`.
        self._trend_chart = LineChart(top_row)
        self._trend_chart.pack(side="left", padx=(16, 0), anchor="nw")

        # Três dos números do painel "Alocações Financeiras" da planilha original valiam a
        # pena trazer sem herdar o bug dela (ver ADR-0015): Input (receitas), Output (despesas)
        # e uma versão bug-free de "Capital atual" vs "Capital final" — usando o status
        # Pago/Pendente que a planilha não tinha. "Essencial imediato"/"Investindo"/"Não
        # Alocado" ficaram de fora, por serem ambíguos demais pra reconstruir com confiança.
        stats_row = ctk.CTkFrame(page_scroll, fg_color="transparent")
        stats_row.pack(fill="x", padx=24, pady=(4, 0))
        self._income_card = StatCard(stats_row, "Receitas do mês", "R$ 0,00",
                                      accent=theme.VALUE_INCOME_TEXT)
        self._income_card.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self._expense_card = StatCard(stats_row, "Despesas do mês", "R$ 0,00",
                                       accent=theme.VALUE_EXPENSE_TEXT)
        self._expense_card.pack(side="left", fill="x", expand=True, padx=6)
        self._paid_balance_card = StatCard(stats_row, "Saldo atual", "R$ 0,00",
                                            accent=theme.TEXT_PRIMARY)
        self._paid_balance_card.pack(side="left", fill="x", expand=True, padx=(6, 0))

        # Painel que agrupa mês/remover mês, total do mês e lançamentos — fundo BG_PANEL_BLUE,
        # o mesmo tom azulado do frame lateral (Sidebar), marca esse bloco como uma unidade só.
        # É onde entram as próximas variáveis do resumo do período. Borda preta fixa
        # (CARBON_BLACK) — no modo claro, BG_PANEL_BLUE ficava perto demais do fundo do app pra
        # dar pra notar o limite do painel sem ela (mesmo motivo da borda da Sidebar).
        content_panel = ctk.CTkFrame(
            page_scroll, fg_color=theme.BG_PANEL_BLUE, corner_radius=12,
            border_width=1, border_color=theme.CARBON_BLACK)
        content_panel.pack(fill="both", expand=True, padx=24, pady=(5, 8))

        # Borda dourada (ACCENT_HIGHLIGHT) isolando o grupo de navegação por mês + Fim do mês do
        # resto do painel — trocada com a do card abaixo (pedido do usuário).
        panel_top = ctk.CTkFrame(
            content_panel, fg_color="transparent", corner_radius=10,
            border_width=2, border_color=theme.ACCENT_HIGHLIGHT)
        panel_top.pack(fill="x", padx=16, pady=(16, 6))

        # Navegação por mês — cada mês mostra só as transações daquele mês, limitada aos meses
        # que já existem (ver ADR-0016/0018). Remover mês é destrutivo (apaga as transações do
        # mês inteiro) então passa por confirmação e vira um único item no desfazer (ADR-0019).
        self._month_selector = MonthSelector(
            panel_top, on_select=self._on_month_selected,
            on_remove_month=self._on_remove_month_requested,
            on_add_month=self._on_month_added)
        self._month_selector.pack(side="left", fill="x", expand=True, padx=(12, 8), pady=10)

        # Borda azul (BORDER_ACCENT) — trocada com a do panel_top acima (pedido do usuário).
        self._total_card = ctk.CTkFrame(panel_top, fg_color=theme.BG_SURFACE, corner_radius=10,
                                         border_width=2, border_color=theme.BORDER_ACCENT)
        self._total_card.pack(side="right", padx=(0, 12), pady=10)
        ctk.CTkLabel(
            self._total_card, text="Fim do mês", text_color=theme.TEXT_PRIMARY,
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=16, pady=(10, 0))
        self._total_label = ctk.CTkLabel(
            self._total_card, text="R$ 0,00", text_color=theme.TEXT_PRIMARY,
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        self._total_label.pack(anchor="w", padx=16, pady=(0, 10))

        transactions_frame = ctk.CTkFrame(content_panel, fg_color="transparent")
        transactions_frame.pack(fill="both", expand=True, padx=16, pady=(10, 16))

        # Botão de adicionar fica logo acima da lista (perto do que ele afeta), não lá em cima
        # no cabeçalho da tela — ver relato do usuário.
        list_header = ctk.CTkFrame(transactions_frame, fg_color="transparent")
        list_header.pack(fill="x", padx=12, pady=(10, 4))
        ctk.CTkLabel(
            list_header, text="Lançamentos", text_color=theme.TEXT_PRIMARY,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(side="left")
        # Contador discreto — quantos lançamentos aparecem na lista agora (depois do filtro de
        # busca, se houver).
        self._count_label = ctk.CTkLabel(
            list_header, text="", text_color=theme.TEXT_PRIMARY, font=ctk.CTkFont(size=11))
        self._count_label.pack(side="left", padx=(8, 0))
        # Busca por descrição/categoria — filtra só a lista abaixo, sem afetar gráfico/totais do
        # mês (esses continuam refletindo o mês inteiro).
        search_frame = ctk.CTkFrame(list_header, fg_color="transparent")
        search_frame.pack(side="left", padx=(8, 0))
        # Ícone de lupa (UI/assets/search.png, fornecido pelo usuário) só pra deixar claro que o
        # campo é de busca — não emoji (pedido do usuário).
        self._search_icon = ctk.CTkImage(Image.open(_SEARCH_ICON_PATH), size=(14, 14))
        ctk.CTkLabel(search_frame, image=self._search_icon, text="").pack(
            side="left", padx=(0, 4))
        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_args: self._on_search_changed())
        ctk.CTkEntry(
            search_frame, textvariable=self._search_var, placeholder_text="Pesquisar...",
            width=150,
        ).pack(side="left")
        ctk.CTkButton(
            list_header, text="+ Adicionar", command=self._open_new_transaction_dialog,
            **theme.outline_button_style(),
        ).pack(side="right")
        ctk.CTkButton(
            list_header, text="+ Lista de compras", command=self._open_shopping_list_dialog,
            **theme.outline_button_style(),
        ).pack(side="right", padx=(0, 8))
        # Reseta a ordem manual (arrastar, ver ADR-0033) do mês pra ordem padrão (por data) — só
        # ícone, cor branca fixa (pedido do usuário; `outline_button_style()` já dá o "quadrado
        # transparente com borda azul"). Desfazível como qualquer outra ação da tela.
        self._reset_order_icon = ctk.CTkImage(
            _tinted(Image.open(_RESET_ICON_PATH), _RESET_ICON_COLOR), size=(16, 16))
        ctk.CTkButton(
            list_header, image=self._reset_order_icon, text="", width=32,
            command=self._open_reset_order_dialog, **theme.outline_button_style(),
        ).pack(side="right", padx=(0, 8))

        # Ícone de pin (fixar/desfixar transação recorrente, ver ADR-0034) — azul quando
        # fixada, cinza (mesmo tom da alça de arrastar) quando não. Só uma versão de cada por
        # ícone/tema, reconfigurada por linha em `_render_transaction_list` conforme
        # `t.is_recurring`.
        pin_on_source = Image.open(_PIN_ON_ICON_PATH)
        pin_off_source = Image.open(_PIN_OFF_ICON_PATH)
        self._pin_on_icon = ctk.CTkImage(_tinted(pin_on_source, _PIN_ON_COLOR), size=(16, 16))
        self._pin_off_icon = ctk.CTkImage(
            light_image=_tinted(pin_off_source, _HANDLE_ICON_LIGHT_COLOR),
            dark_image=_tinted(pin_off_source, _HANDLE_ICON_DARK_COLOR),
            size=(16, 16))

        # Frame comum (não mais CTkScrollableFrame própria) — quem rola agora é a página inteira
        # (`page_scroll`, ver __init__); dois scrolls aninhados brigavam pelo scroll do mouse.
        self._list_frame = ctk.CTkFrame(transactions_frame, fg_color="transparent")
        self._list_frame.pack(fill="both", expand=True, padx=12, pady=(4, 12))
        self._list_frame.grid_columnconfigure(3, weight=1)  # coluna Descrição expande

        # Cabeçalho de colunas + os 2 separadores ao redor — criados uma única vez aqui, nunca
        # mais destruídos/recriados a cada `_render_transaction_list()` (eram recriados a cada
        # chamada antes, sem necessidade — nunca mudam). Ver ADR-0026 (correção de performance).
        column_count = len(_COLUMN_HEADERS)
        Divider(self._list_frame, color=theme.BORDER_ACCENT).grid(
            row=0, column=0, columnspan=column_count, sticky="ew", pady=(0, 4))
        for col, header_text in enumerate(_COLUMN_HEADERS):
            if not header_text:
                continue
            if header_text == "Data":
                # Clicável — inverte a ordem por data (ADR-0033), sem mexer na ordem manual
                # persistida. `cursor="hand2"` só pra dar a dica de que é clicável.
                self._date_header_label = ctk.CTkLabel(
                    self._list_frame, text=self._date_header_text(),
                    text_color=theme.TEXT_PRIMARY, font=ctk.CTkFont(size=11, weight="bold"),
                    cursor="hand2")
                self._date_header_label.bind("<Button-1>", self._toggle_date_sort)
                self._date_header_label.grid(row=1, column=col, sticky="w", padx=8, pady=(0, 6))
                continue
            ctk.CTkLabel(
                self._list_frame, text=header_text, text_color=theme.TEXT_PRIMARY,
                font=ctk.CTkFont(size=11, weight="bold"),
            ).grid(row=1, column=col, sticky="w", padx=8, pady=(0, 6))
        Divider(self._list_frame, color=theme.BORDER_ACCENT).grid(
            row=2, column=0, columnspan=column_count, sticky="ew", pady=(0, 6))

        self._empty_label = ctk.CTkLabel(self._list_frame, text="", text_color=theme.TEXT_PRIMARY)

        # Pool de linhas — reaproveitado entre renderizações em vez de destruir/recriar tudo a
        # cada chamada (era o gargalo real de performance: ~8 widgets CTk por linha, cada um
        # caro de construir — trocar de mês/marcar Pago/digitar na busca chamava isso toda vez,
        # ver ADR-0026). Cresce sob demanda; linhas sobrando de uma renderização anterior maior
        # só ficam escondidas (`grid_remove`), prontas pra reaparecer sem reconstruir nada.
        # Ícone da alça de arrastar (setas cima/baixo, ver ADR-0033) — mesmo padrão do
        # `_search_icon` (CTkImage, não emoji), mas com uma versão clara/escura (ver `_tinted`)
        # pra ficar visível nos dois temas — CTk troca sozinho ao mudar de modo, igual qualquer
        # papel de cor "neutro" do tema.
        handle_icon_source = Image.open(_HANDLE_ICON_PATH)
        self._drag_icon = ctk.CTkImage(
            light_image=_tinted(handle_icon_source, _HANDLE_ICON_LIGHT_COLOR),
            dark_image=_tinted(handle_icon_source, _HANDLE_ICON_DARK_COLOR),
            size=(14, 14))

        self._row_pool: list[dict] = []

        # Fundos sólidos do arrasto (ver `_show_card_bg`, ADR-0033) — só 2 no total, nunca um por
        # linha do pool: um pra linha arrastada (fica visível o arrasto inteiro) e um reusado pela
        # linha vizinha que estiver deslizando a cada momento. Só 2 widgets fixos elimina qualquer
        # ambiguidade de "quem fica na frente de quem" entre linhas diferentes.
        self._drag_card = ctk.CTkFrame(self._list_frame, fg_color="transparent", corner_radius=6)
        self._neighbor_card = ctk.CTkFrame(
            self._list_frame, fg_color="transparent", corner_radius=6)

        self._search_after_id: str | None = None

        self.refresh()

    def _open_new_transaction_dialog(self) -> None:
        open_singleton(self, "_transaction_dialog",
                        lambda: TransactionFormDialog(self, on_created=self._handle_created))

    def _open_shopping_list_dialog(self) -> None:
        open_singleton(self, "_shopping_list_dialog",
                        lambda: ShoppingListDialog(self, on_created=self._handle_created))

    def _open_edit_transaction_dialog(self, transaction) -> None:
        open_singleton(self, "_transaction_dialog", lambda: TransactionFormDialog(
            self, on_created=lambda after: self._handle_updated(transaction, after),
            transaction=transaction))

    def _handle_created(self, created_transaction) -> None:
        self._undo_stack.push(CreateTransactionCommand(created_transaction))
        self.refresh()

    def _handle_updated(self, before_transaction, after_transaction) -> None:
        self._undo_stack.push(UpdateTransactionCommand(before_transaction, after_transaction))
        self.refresh()

    def _undo(self) -> None:
        self._undo_stack.undo()
        self.refresh()

    def _redo(self) -> None:
        self._undo_stack.redo()
        self.refresh()

    def _on_month_selected(self, _month_str: str) -> None:
        self.refresh()

    def _on_remove_month_requested(self, month_str: str) -> None:
        month_transactions = [
            t for t in backend_bridge.list_transactions() if t.occurred_at[:7] == month_str]
        label = month_label(month_str)
        if month_transactions:
            message = (
                f'Remover {label} vai apagar {len(month_transactions)} lançamento(s) desse '
                f'mês. Dá pra desfazer depois com "Desfazer".')
        else:
            message = f'Remover {label} da lista de meses? Dá pra desfazer depois com "Desfazer".'
        open_singleton(self, "_confirm_dialog", lambda: ConfirmDialog(
            self, title="Remover mês", message=message, confirm_text="Remover",
            on_confirm=lambda: self._remove_month(month_str, month_transactions)))

    def _remove_month(self, month_str: str, month_transactions) -> None:
        was_extra = self._month_selector.is_extra_month(month_str)
        fallback = self._month_selector.neighbor_of(month_str)
        for t in month_transactions:
            backend_bridge.delete_transaction(t.id)
        self._month_selector.remove_month(month_str)
        self._month_selector.force_select(fallback)
        self._undo_stack.push(RemoveMonthCommand(
            month_transactions, month_str, was_extra, fallback, self._month_selector))
        self.refresh()

    def _on_month_added(self, month_str: str) -> None:
        """Chamado por `MonthSelector` ANTES de selecionar o mês novo (ver ADR-0034) — clona
        toda transação atualmente fixada (ícone de pin) pra dentro do mês novo: mesmo dia do mês
        do original (ajustado se o mês novo tiver menos dias), sempre "A pagar" (é uma cobrança
        nova) e o clone em si NÃO nasce fixado (só o original continua sendo o "molde" — evita
        duplicar a cada mês novo criado depois). Sem transação fixada nenhuma, não faz nada — só
        entra na pilha de desfazer quando realmente clona alguma coisa, pra "+ Mês" continuar
        sem histórico extra no caso comum (sem pin nenhum usado)."""
        previous_month = self._month_selector.selected_month()
        recurring = [t for t in backend_bridge.list_transactions() if t.is_recurring]
        if not recurring:
            return

        year, month = (int(part) for part in month_str.split("-"))
        days_in_month = calendar.monthrange(year, month)[1]
        pending_status = backend_bridge.transaction_enums()["pending"]

        entries = []
        for t in recurring:
            day = min(int(t.occurred_at[8:10]), days_in_month)
            fields = {
                "description": t.description,
                "category_name": t.category_name,
                "type_": t.type,
                "amount_cents": t.amount.cents,
                "currency": t.amount.currency,
                "status": pending_status,
                "occurred_at_date": f"{month_str}-{day:02d}",
                "investment_id": t.investment_id,
            }
            created = backend_bridge.create_transaction(**fields)
            entries.append({"fields": fields, "id": created.id})

        self._undo_stack.push(
            AddMonthCommand(month_str, entries, previous_month, self._month_selector))

    def _open_reset_order_dialog(self) -> None:
        if len(self._current_transactions) < 2:
            return  # nada pra reordenar
        open_singleton(self, "_confirm_dialog", lambda: ConfirmDialog(
            self, title="Resetar posições",
            message=(
                'Resetar a ordem deste mês pra ordem padrão (por data, mais recente primeiro)? '
                'Dá pra desfazer depois com "Desfazer".'),
            confirm_text="Resetar",
            on_confirm=self._reset_transaction_order))

    def _reset_transaction_order(self) -> None:
        """Reseta a ordem manual (ver ADR-0033) do mês atual pra ordem padrão — por data,
        empate quebrado pela ordem manual atual (sort estável, mesma lógica de
        `_apply_date_sort`). Só reatribui `sort_order` de quem realmente muda de lugar, e vira um
        único item no desfazer (ver ADR-0019/`RemoveMonthCommand`, mesmo princípio)."""
        ordered = sorted(self._current_transactions, key=lambda t: t.occurred_at, reverse=True)
        total = len(ordered)
        entries = []
        for index, t in enumerate(ordered):
            new_sort_order = float(total - index)
            if new_sort_order != t.sort_order:
                entries.append((t.id, t.sort_order, new_sort_order))
                backend_bridge.update_transaction_sort_order(t.id, new_sort_order)
        if entries:
            self._undo_stack.push(ResetTransactionOrderCommand(entries))
        self._date_sort_mode = None
        self._date_header_label.configure(text=self._date_header_text())
        self.refresh()

    def _on_search_changed(self) -> None:
        # Debounce: cancela o agendamento anterior a cada tecla nova, só renderiza de fato ~150ms
        # depois da última tecla — evita trabalho à toa enquanto o usuário ainda está digitando
        # (ver ADR-0026). Só re-renderiza a lista, sem reconsultar o banco nem mexer em
        # gráfico/totais do mês.
        if self._search_after_id is not None:
            self.after_cancel(self._search_after_id)
        self._search_after_id = self.after(150, self._apply_search_filter)

    def _apply_search_filter(self) -> None:
        self._search_after_id = None
        self._render_transaction_list(self._filtered_transactions())

    def _filtered_transactions(self) -> list:
        query = self._search_var.get().strip().lower()
        if not query:
            return self._current_transactions
        return [
            t for t in self._current_transactions
            if query in t.description.lower() or query in t.category_name.lower()]

    def _date_header_text(self) -> str:
        if self._date_sort_mode == "asc":
            return "Data ▲"
        if self._date_sort_mode == "desc":
            return "Data ▼"
        return "Data"

    def _toggle_date_sort(self, _event=None) -> None:
        """Clicar no cabeçalho "Data" alterna entre ordenar a visualização por data crescente/
        decrescente — não persiste nada, é só um jeito alternativo de olhar a lista sem abrir
        mão da ordem manual (ver ADR-0033: arrastar qualquer linha volta pro modo manual)."""
        self._date_sort_mode = "asc" if self._date_sort_mode != "asc" else "desc"
        self._date_header_label.configure(text=self._date_header_text())
        self._render_transaction_list(self._filtered_transactions())

    def _apply_date_sort(self, transactions: list) -> list:
        if self._date_sort_mode is None:
            return transactions
        return sorted(
            transactions, key=lambda t: t.occurred_at, reverse=self._date_sort_mode == "desc")

    def refresh(self) -> None:
        all_transactions = backend_bridge.list_transactions()
        available_months = {t.occurred_at[:7] for t in all_transactions}
        self._month_selector.update_months(available_months)
        selected_month = self._month_selector.selected_month()
        transactions = [t for t in all_transactions if t.occurred_at[:7] == selected_month]
        self._current_transactions = transactions

        total_cents = sum(t.amount.cents for t in transactions)
        total_color = theme.VALUE_INCOME_TEXT if total_cents >= 0 else theme.VALUE_EXPENSE_TEXT
        total_text = _format_money(total_cents)
        # Evita redesenhar o card à toa quando o valor não mudou (mesmo motivo do StatCard —
        # ver ADR-0033: Desfazer de uma ação que não afeta o total, ex. reordenar, não deveria
        # fazer este card piscar).
        if (self._total_label.cget("text") != total_text
                or self._total_label.cget("text_color") != total_color):
            self._total_label.configure(text=total_text, text_color=total_color)

        # Input/Output/Capital atual do painel "Alocações Financeiras" — ver ADR-0015. Receitas
        # do mês só conta dinheiro que entrou de verdade na conta — exclui categoria Passiva
        # (resgate/rendimento de investimento), que não é renda nova, só dinheiro voltando de um
        # investimento (relato do usuário). Só esse card mudou — Fim do mês, Despesas do mês,
        # Saldo atual e o gráfico de consumo continuam somando exatamente como antes.
        income_cents = sum(
            t.amount.cents for t in transactions
            if t.amount.cents > 0 and t.category_name != "Passiva")
        expense_cents = sum(t.amount.cents for t in transactions if t.amount.cents < 0)
        paid_balance_cents = sum(
            t.amount.cents for t in transactions if str(t.status) == "TransactionStatus.PAID")
        self._income_card.set_value(_format_money(income_cents))
        self._expense_card.set_value(_format_money(expense_cents))
        self._paid_balance_card.set_value(
            _format_money(paid_balance_cents),
            color=theme.VALUE_INCOME_TEXT if paid_balance_cents >= 0 else theme.VALUE_EXPENSE_TEXT)

        # Consumo por categoria (Essencial/Lazer/Investimento), não por descrição — ver
        # ADR-0012/0014. Só despesas contam (dinheiro saindo), igual ao painel "Alocações
        # Financeiras" da planilha original do usuário.
        totals_by_category = {}
        for t in transactions:
            if t.amount.cents < 0:
                totals_by_category[t.category_name] = (
                    totals_by_category.get(t.category_name, 0) + (-t.amount.cents / 100))
        self._chart.update_data(totals_by_category)
        self._trend_chart.update_series(
            self._monthly_category_series(all_transactions, selected_month))

        self._render_transaction_list(self._filtered_transactions())

    @staticmethod
    def _shift_month(month_str: str, delta: int) -> str:
        """`month_str` ("YYYY-MM") deslocado `delta` meses (negativo = passado). Aritmética
        simples em cima do índice absoluto do mês (ano*12+mês) — não precisa de `datetime`
        porque não lida com dias, só ano/mês."""
        year, month = (int(part) for part in month_str.split("-"))
        absolute = year * 12 + (month - 1) + delta
        return f"{absolute // 12}-{absolute % 12 + 1:02d}"

    def _monthly_category_series(self, all_transactions: list, selected_month: str,
                                  months_back: int = 6) -> dict:
        """{categoria: [(rótulo_mês, valor), ...]} pras `months_back` meses civis terminando no
        mês selecionado (mês sem nenhum lançamento entra como 0.0, não é pulado — eixo do tempo
        tem que ficar uniforme). Só as categorias que aparecem no mês selecionado agora entram —
        mesmo conjunto do gráfico de pizza, pra não acumular categoria antiga irrelevante na
        legenda do comparativo (ver ADR-0029). Mesma regra de "consumo" do gráfico de pizza: só
        despesas (`amount.cents < 0`), magnitude em reais."""
        months = [self._shift_month(selected_month, -i) for i in range(months_back - 1, -1, -1)]

        totals_by_month_category: dict[str, dict[str, float]] = {month: {} for month in months}
        for t in all_transactions:
            month = t.occurred_at[:7]
            if month in totals_by_month_category and t.amount.cents < 0:
                bucket = totals_by_month_category[month]
                bucket[t.category_name] = bucket.get(t.category_name, 0.0) + (-t.amount.cents / 100)

        current_categories = totals_by_month_category[selected_month].keys()
        labels = [f"{month[5:7]}/{month[:4]}" for month in months]
        return {
            category: [
                (label, totals_by_month_category[month].get(category, 0.0))
                for month, label in zip(months, labels)]
            for category in current_categories
        }

    def _get_or_create_row(self, index: int) -> dict:
        """Devolve o conjunto de widgets da linha `index` do pool, criando na primeira vez que
        essa posição é usada. Nunca destruído depois — só escondido/reaparecido conforme o
        tamanho da lista atual (ver `_render_transaction_list`)."""
        if index < len(self._row_pool):
            return self._row_pool[index]

        # Alça de arrastar — pega/solta a linha pra reordenar (ver ADR-0033). `index` nunca muda
        # pra este slot do pool depois de criado (o pool só cresce por append), então pode ficar
        # fixo no closure sem risco de apontar pra linha errada depois de renderizações futuras.
        handle = ctk.CTkLabel(self._list_frame, image=self._drag_icon, text="", cursor="hand2")
        handle.bind("<ButtonPress-1>", lambda event, idx=index: self._on_handle_press(event, idx))
        handle.bind("<B1-Motion>", self._on_handle_motion)
        handle.bind("<ButtonRelease-1>", self._on_handle_release)

        # Fixar/desfixar recorrente (ícone de pin, ver ADR-0034) — imagem/comando reais setados
        # em `_render_transaction_list()`, conforme `t.is_recurring` de cada linha.
        pin = ctk.CTkButton(
            self._list_frame, image=self._pin_off_icon, text="", width=24,
            fg_color="transparent", hover_color=theme.BG_SURFACE)

        row = {
            "handle": handle,
            "date": ctk.CTkLabel(self._list_frame, text_color=theme.TEXT_PRIMARY),
            "pin": pin,
            "description": ctk.CTkLabel(self._list_frame, text_color=theme.TEXT_PRIMARY),
            # Contorno preto (ver ADR-0042, relato do usuário: cor de categoria pouco visível
            # no modo claro) — `CTkLabel` não faz contorno de texto, daí o widget dedicado.
            "category": OutlinedLabel(self._list_frame),
            "status": ctk.CTkButton(
                # fg_color/hover_color reais são setados em `_render_transaction_list()`,
                # sempre em função do status atual da transação (ver theme.shade_color).
                self._list_frame, width=80, text_color=theme.CARBON_BLACK,
                border_width=2, border_color=theme.STATUS_BADGE_BORDER),
            "value": ctk.CTkLabel(self._list_frame, width=100, anchor="e"),
            "edit": ctk.CTkButton(
                self._list_frame, text="Editar", width=64, fg_color="transparent",
                text_color=theme.TEXT_PRIMARY, hover_color=theme.BG_SURFACE),
            "remove": ctk.CTkButton(
                self._list_frame, text="Remover", width=64, fg_color="transparent",
                text_color=theme.TEXT_PRIMARY, hover_color=theme.BG_SURFACE),
            "divider": Divider(self._list_frame, color=theme.ROW_SEPARATOR, thickness=2),
        }
        self._row_pool.append(row)
        return row

    def _grid_row_widgets(self, row_widgets: dict, offset: int) -> None:
        """Posiciona uma linha (já com o conteúdo configurado) na posição `offset` — separado
        das chamadas `.configure()` pra poder ser reusado tanto no render normal quanto quando
        uma linha (arrastada ou vizinha) termina de deslizar durante um arrasto e assenta de
        volta no grid (ver `_animate_row_to_offset`, ADR-0033). Seguro chamar mesmo com um
        arrasto em andamento **desde que** `_on_handle_press` já tenha travado a altura de cada
        linha do grid (`minsize`, ver lá) — sem essa trava, isso dispararia o recálculo de
        `scrollregion` do `CTkScrollableFrame` e faria coisas fora da lista tremerem."""
        row = 3 + offset * 2
        for key, column, sticky, padx in _ROW_GRID_SPEC:
            row_widgets[key].grid(row=row, column=column, sticky=sticky, padx=padx, pady=3)
        row_widgets["divider"].grid(
            row=row + 1, column=0, columnspan=len(_COLUMN_HEADERS), sticky="ew", pady=(3, 0))

    def _show_card_bg(self, card: ctk.CTkFrame, row_widgets: dict, offset: int) -> int:
        """Mostra (ou reposiciona) `card` — um dos dois fundos sólidos dedicados e únicos
        (`self._drag_card`/`self._neighbor_card`, ver ADR-0033), nunca um por linha — cobrindo da
        alça de arrastar até o botão Remover, na posição do slot `offset`. Devolve o `y` onde
        `card` acabou de ser posicionado.

        **Sempre calcula a posição pela fórmula** (`list_top + offset * row_step`), nunca lendo
        `row_widgets["date"].winfo_y()` — outra armadilha real do Tk, achada depois da do
        `card.winfo_y()` (ver `_animate_row_to_offset`): ler a posição de um widget bem na
        sequência de um `.grid()` que ACABOU de rodar (ex. `_grid_row_widgets`, ao assentar a
        linha arrastada de volta entre um "hop" e o outro) também pode devolver a geometria
        ANTIGA, porque o Tk só atualiza isso depois de processar a fila de eventos — não é só
        `.place()` que sofre disso. Sem essa correção, o cartão da linha arrastada ficava
        "preso" bem atrás da posição real dela, cada vez mais longe conforme o arrasto continuava
        (relato do usuário: "o item em si fica pra trás enquanto o espaço vazio acompanha
        normalmente" — o "espaço vazio"/conteúdo real usava `_grid_row_widgets`, que sempre
        assenta na posição absoluta certa; só o cartão, por reler `winfo_y()`, pegava a geometria
        obsoleta e nunca mais se corrigia sozinho).

        Ter só 2 widgets fixos (em vez de um por linha do pool) evita qualquer ambiguidade de
        empilhamento entre linhas diferentes disputando `.lift()`/`.lower()` ao mesmo tempo — um
        cartão sobrando na frente do próprio conteúdo da linha, com um retângulo escuro cobrindo
        tudo (relato do usuário, com screenshot). `tkraise()` sem argumento aqui SEMPRE joga esse
        cartão específico pro topo; levantar o conteúdo da linha *depois* garante que ele fica por
        cima do próprio cartão — sem depender da ordem de chamadas entre linhas diferentes."""
        placed_y = self._drag["list_top"] + offset * self._drag["row_step"] - 5
        height = row_widgets["date"].winfo_height() + 10
        width = self._list_frame.winfo_width()
        # CTk não aceita width/height em `.place()` (tem que vir de `.configure()`/construtor —
        # ver ADR-0033) — só x/y no `.place()` propriamente dito.
        card.configure(fg_color=theme.BG_SURFACE, width=width, height=height)
        card.place(x=0, y=placed_y)
        card.tkraise()
        for widget in row_widgets.values():
            # `.tkraise()`, nunca `.lift()` — `tk.Canvas` (usado por `OutlinedLabel`, categoria,
            # ver ADR-0042) sobrescreve `.lift()` pra "levantar item do canvas" (exige um
            # tagOrId, quebra em `widget.lift()` genérico sem argumento); `.tkraise()` é o mesmo
            # levantamento de janela na pilha de empilhamento, sem esse conflito de nome.
            widget.tkraise()
        return placed_y

    def _hide_card_bg(self, card: ctk.CTkFrame) -> None:
        card.place_forget()

    def _render_transaction_list(self, transactions: list) -> None:
        if self._drag is not None:
            # Um arrasto em andamento controla o grid diretamente (ver _on_handle_press/
            # _on_handle_release) — uma renderização no meio do caminho (ex. debounce de busca
            # disparando atrasado) bagunçaria as posições temporárias. `_on_handle_release`
            # sempre chama `refresh()` no final, então nada fica pra trás.
            return

        # Volta a acompanhar o tamanho real do conteúdo fora de um arrasto (ver
        # `_on_handle_press`, que desliga isso e trava a altura só durante o arrasto).
        self._list_frame.grid_propagate(True)
        # Libera as linhas do grid travadas (`minsize`, ver `_on_handle_press`) — sem isso, uma
        # lista que encolhe depois (ex. filtro de busca) ficaria com espaço reservado sobrando
        # das linhas de um arrasto anterior, que não existem mais no novo conjunto.
        for grid_row in self._drag_locked_rows:
            self._list_frame.grid_rowconfigure(grid_row, minsize=0)
        self._drag_locked_rows = []

        transactions = self._apply_date_sort(transactions)
        self._rendered_transactions = transactions
        self._count_label.configure(text=f"{len(transactions)} lançamento(s)")

        if not transactions:
            empty_text = ("Nenhum lançamento encontrado." if self._search_var.get().strip()
                          else "Nenhum lançamento neste mês.")
            self._empty_label.configure(text=empty_text)
            self._empty_label.grid(
                row=3, column=0, columnspan=len(_COLUMN_HEADERS), sticky="w", padx=8, pady=3)
        else:
            self._empty_label.grid_remove()

        # Cada lançamento ocupa uma linha de dado + uma linha de separador fino logo abaixo
        # (ver ADR-0020) — daí o passo de 2 entre um lançamento e o próximo.
        for offset, t in enumerate(transactions):
            row_widgets = self._get_or_create_row(offset)

            row_widgets["date"].configure(text=t.occurred_at)
            row_widgets["pin"].configure(
                image=self._pin_on_icon if t.is_recurring else self._pin_off_icon,
                command=lambda tid=t.id, rec=t.is_recurring: self._toggle_recurring(tid, rec))
            row_widgets["description"].configure(text=t.description)
            row_widgets["category"].set_text(t.category_name)

            is_paid = str(t.status) == "TransactionStatus.PAID"
            status_color = theme.VALUE_INCOME if is_paid else theme.DEEP_SAFFRON
            row_widgets["status"].configure(
                text="Pago" if is_paid else "A pagar",
                fg_color=status_color,
                # Hover é um tom diferente da MESMA cor do status atual (verde-outro-verde,
                # laranja-outro-laranja) — antes era sempre ACCENT_HIGHLIGHT (laranja) fixo no
                # hover_color de criação do botão, então passar o mouse em cima de "Pago" (verde)
                # fazia parecer que tinha virado "A pagar".
                hover_color=theme.shade_color(status_color, -0.2),
                command=lambda tid=t.id, paid=is_paid: self._toggle_status(tid, paid))

            value_color = theme.VALUE_INCOME_TEXT if t.amount.cents >= 0 else theme.VALUE_EXPENSE_TEXT
            row_widgets["value"].configure(
                text=_format_money(t.amount.cents), text_color=value_color)

            row_widgets["edit"].configure(
                command=lambda tx=t: self._open_edit_transaction_dialog(tx))

            row_widgets["remove"].configure(command=lambda tid=t.id: self._delete(tid))

            self._grid_row_widgets(row_widgets, offset)

        # Linhas do pool sobrando de uma renderização anterior maior (ex. limpou a busca e a
        # lista ficou menor) — escondidas, não destruídas, prontas pra reaparecer sem reconstruir
        # nada se a lista crescer de novo.
        for extra_row in self._row_pool[len(transactions):]:
            for widget in extra_row.values():
                widget.grid_remove()
                widget.place_forget()

    def _row_step(self) -> int:
        """Altura em pixels de uma linha (dado + separador) — medida entre duas linhas do pool
        já renderizadas, já que todas têm a mesma altura. Chamado sempre antes de qualquer
        `.place()' entrar em cena (ver `_on_handle_press`), então os valores lidos são sempre da
        posição real do grid, não de uma animação em andamento."""
        if len(self._row_pool) >= 2:
            step = self._row_pool[1]["date"].winfo_y() - self._row_pool[0]["date"].winfo_y()
            if step > 0:
                return step
        return 34

    def _log_drag(self, event_name: str, **fields) -> None:
        """Log de diagnóstico do arrasto — só grava algo se `ITERADOR_DEBUG_DRAG=1` (ver
        constante no topo do módulo). `fields` vira `chave=valor` na linha; `t` é sempre em ms
        desde o `<ButtonPress-1>` que começou o arrasto atual."""
        if not _DRAG_DEBUG:
            return
        t_ms = round((time.monotonic() - self._drag_log_start) * 1000)
        parts = [f"t={t_ms}", f"evento={event_name}"]
        parts += [f"{key}={value}" for key, value in fields.items()]
        self._drag_log.append(" ".join(parts))
        if len(self._drag_log) >= 500:
            # Salva de vez em quando mesmo sem soltar o mouse — se o arrasto travar de verdade
            # (sem chegar a `_on_handle_release`), o log não fica só na memória, perdido.
            self._flush_drag_log()

    def _flush_drag_log(self) -> None:
        if not _DRAG_DEBUG or not self._drag_log:
            return
        with open(_DRAG_DEBUG_LOG_PATH, "a", encoding="utf-8") as handle:
            handle.write("\n".join(self._drag_log))
            handle.write("\n----- fim do arrasto -----\n")
        self._drag_log.clear()

    def _on_handle_press(self, event, offset: int) -> None:
        """Início do arrasto (ver ADR-0033): a linha `offset` sai do grid e passa a ser
        controlada por `.place()`, mas sempre num dos slots válidos da lista — nunca numa
        posição de pixel arbitrária/contínua (ver `_advance_drag_target`)."""
        if self._drag is not None or len(self._rendered_transactions) < 2:
            return

        self._drag_log_start = time.monotonic()
        self._drag_log.clear()

        # Trava a altura do `_list_frame` no valor atual antes de tirar qualquer linha do grid.
        # Achado investigando o `CTkScrollableFrame` (ver `_animate_row_to_offset`): mesmo sem
        # nenhuma chamada `.grid()` durante o arrasto, o simples fato de uma linha SAIR do grid
        # (pra virar `.place()`) já muda quantas células o grid tem que caber, e por padrão o
        # frame se redimensiona pra isso (`grid_propagate`, ligado por padrão) — esse
        # redimensionamento se propaga por `transactions_frame`/`content_panel` até o
        # `CTkScrollableFrame` da página inteira, que recalcula a região de rolagem a cada vez,
        # fazendo coisas fora da lista (gráfico, cards) tremerem junto (relato do usuário).
        # Desligar `grid_propagate` e fixar a altura atual quebra essa corrente na origem —
        # `_render_transaction_list` liga de volta (`grid_propagate(True)`) fora de um arrasto,
        # pra continuar acompanhando o tamanho real quando o nº de lançamentos muda de verdade.
        self._list_frame.configure(height=self._list_frame.winfo_height())
        self._list_frame.grid_propagate(False)

        row_step = self._row_step()
        list_top = self._row_pool[0]["date"].winfo_y()
        row_widgets = self._row_pool[offset]

        # Trava a altura de CADA linha do grid (dado + separador) no valor atual, medida via
        # `grid_bbox` — achado real, direto do log de diagnóstico (ver ADR-0033): assim que uma
        # linha sai do grid (`.place()`), a linha do grid que ela ocupava fica sem nenhum widget
        # e o Tk encolhe a altura dela pra 0, empurrando TODAS as linhas seguintes pra cima (medi
        # e confirmei: tirar só a linha 0 do grid fazia as linhas 1/2/3 subirem um `row_step`
        # inteiro cada uma). Isso invalidava `row_step`/`list_top` — medidos uma vez só aqui — pro
        # resto do arrasto inteiro, base de TODO o cálculo de posição/alvo. `minsize` trava a
        # altura reservada pra aquela linha do grid mesmo sem nenhum widget dentro dela.
        n = len(self._rendered_transactions)
        self._drag_locked_rows = list(range(3, 3 + n * 2))
        for grid_row in self._drag_locked_rows:
            bbox = self._list_frame.grid_bbox(0, grid_row)
            if bbox is not None:
                self._list_frame.grid_rowconfigure(grid_row, minsize=bbox[3])

        self._drag = {
            "start_offset": offset,
            "target_offset": offset,
            # Posição "de verdade" indicada pela posição atual do mouse — pode estar à frente de
            # `target_offset`, que só avança um passo de cada vez (ver `_advance_drag_target`).
            "pending_target": offset,
            "outside_bounds": False,
            "original_list": list(self._rendered_transactions),
            "row_step": row_step,
            "list_top": list_top,
            "grab_y": event.y_root - self._list_frame.winfo_rooty() - row_widgets["date"].winfo_y(),
            "displayed_offset": {},
            "anim_token": {},
        }
        self._log_drag(
            "press", offset=offset, y_root=event.y_root,
            list_frame_rooty=self._list_frame.winfo_rooty(), row_step=row_step,
            list_top=list_top, grab_y=self._drag["grab_y"], n=len(self._rendered_transactions))

        for widget in row_widgets.values():
            # Só x/y — CTk não aceita width/height em `.place()` (tem que vir do construtor);
            # como nenhum widget muda de tamanho entre grid e place, isso não é um problema. Não
            # muda de posição aqui (`target_offset` ainda é o mesmo `offset` de sempre) — só sai
            # do grid pra poder ser animada independente das outras linhas mais tarde.
            widget.place(x=widget.winfo_x(), y=widget.winfo_y())
            # "Elevar" a linha arrastada (fundo sutil) — só nos labels de texto, nunca nos
            # botões (o de Status carrega a cor verde/laranja do Pago/A pagar, não pode mexer).
            # `OutlinedLabel` (categoria, ver ADR-0042) não é `CTkLabel` — Canvas puro não tem
            # fundo "transparent" de verdade, precisa do próprio método pra trocar de cor.
            if isinstance(widget, ctk.CTkLabel):
                widget.configure(fg_color=theme.BG_SURFACE)
            elif isinstance(widget, OutlinedLabel):
                widget.set_background(theme.BG_SURFACE)
        # Fundo sólido atrás de tudo (ver ADR-0033) — também levanta (`.lift()`) o conteúdo por
        # cima dele, então precisa vir depois de posicionar os widgets acima.
        self._show_card_bg(self._drag_card, row_widgets, offset)

        self._drag_tick_id = self.after(_DRAG_TARGET_STEP_INTERVAL_MS, self._advance_drag_target)
        # Rede de segurança contra `<ButtonRelease-1>` se perder (mesmo problema de entrega de
        # evento do `<B1-Motion>`, ver ADR-0033 e `_compute_pending_target`) — relato real do
        # usuário, bem reproduzível: item continuava seguindo o mouse mesmo bem depois de soltar
        # o botão, porque `_on_handle_release` nunca chegou a rodar (nada limpou `self._drag`) e
        # o "tick" consulta a posição do mouse sozinho agora, então sem essa checagem ele
        # continuaria "arrastando" pra sempre. `<Motion>` (sem o prefixo de botão) parece mais
        # confiável — chega mesmo se `<B1-Motion>`/`<ButtonRelease-1>` não chegarem — e o campo
        # `state` do evento revela se o botão 1 ainda está pressionado ou não, sem depender de
        # nenhum evento específico de soltar. `bind_all`/`unbind_all` são bloqueados em widgets
        # CTk comuns (`CTkBaseClass`, "could result in undefined behavior") — só a janela raiz
        # (`CTk`, que NÃO herda dessa classe) permite, então precisa ser `winfo_toplevel()`.
        self._global_motion_bind_id = self.winfo_toplevel().bind_all(
            "<Motion>", self._on_global_motion_check_release, add="+")

    def _compute_pending_target(self, source: str, mouse_y_root: int | None = None) -> None:
        """Recalcula `pending_target` a partir da posição do mouse — chamado tanto por
        `<B1-Motion>` (`mouse_y_root=event.y_root`) quanto, principalmente, por
        `_advance_drag_target` a cada "tick" (sem argumento — consulta `winfo_pointery()`
        diretamente).

        **Achado real via log de diagnóstico** (ver ADR-0033): num arrasto de ~18s, o "tick"
        (`self.after`) disparou certinho o tempo todo, mas o evento `<B1-Motion>` simplesmente
        parou de chegar por vários segundos seguidos — mesmo com o botão ainda pressionado e o
        mouse (presumivelmente) se movendo de verdade (relato do usuário: "o elemento
        frequentemente falha ao seguir o mouse... ele fica travado"). O Tk/gerenciador de janela
        não está entregando esses eventos de forma confiável o tempo todo (bem plausível numa
        sessão Wayland/XWayland). Consultar a posição do ponteiro diretamente via
        `winfo_pointery()` não depende de NENHUMA entrega de evento — funciona mesmo se
        `<B1-Motion>` parar de chegar."""
        drag = self._drag
        if drag is None:
            return

        n = len(drag["original_list"])
        if mouse_y_root is None:
            mouse_y_root = self.winfo_pointery()
        mouse_y = mouse_y_root - self._list_frame.winfo_rooty() - drag["grab_y"]
        raw_target = round((mouse_y - drag["list_top"]) / drag["row_step"])
        # Prende entre a primeira e a última posição — sem isso, arrastar o mouse pra fora do
        # frame apontaria pra um slot inexistente; o item fica "preso" na borda disponível e
        # continua respondendo assim que o mouse volta a ficar dentro do alcance.
        drag["pending_target"] = max(0, min(n - 1, raw_target))
        # Mouse de verdade fora dos limites da lista (não só "encostando" na borda) — ver uso em
        # `_advance_drag_target`: sem isso, um arrasto que sai do frame parecia "sem resposta"
        # por vários segundos até alcançar a borda, andando 1 posição a cada 100ms desde onde
        # estava (relato do usuário: "perde totalmente o track do mouse").
        drag["outside_bounds"] = raw_target < 0 or raw_target > n - 1
        self._log_drag(
            source, y_root=mouse_y_root, mouse_y=mouse_y, raw_target=raw_target,
            pending_target=drag["pending_target"], outside_bounds=drag["outside_bounds"],
            target_offset=drag["target_offset"],
            drag_card_y=self._drag_card.winfo_y() if self._drag_card.winfo_ismapped() else None)

    def _maybe_auto_scroll(self) -> None:
        """Rola a página sozinha se o mouse estiver perto da borda VISÍVEL da área rolável
        (`self._page_scroll`, não os limites da lista em si) — sem isso, arrastar um lançamento
        de baixo pra cima (ou vice-versa) além do que está visível na tela deixava o item
        "preso" numa posição fora da parte visível da janela, sem jeito de alcançar o resto da
        lista (relato do usuário). Chamado a cada "tick" (`_advance_drag_target`), então herda o
        mesmo ritmo — não precisa de agendamento próprio.

        `yview_scroll`/`_parent_canvas` não são API pública do `CTkScrollableFrame` (não existe
        um "role N pixels" oficial) — acesso direto ao canvas interno, mesmo padrão já usado nos
        testes deste projeto pra inspecionar o `CTkScrollableFrame` (ver ADR-0033)."""
        canvas = self._page_scroll._parent_canvas
        canvas_top = canvas.winfo_rooty()
        canvas_bottom = canvas_top + canvas.winfo_height()
        mouse_y_root = self.winfo_pointery()
        if mouse_y_root < canvas_top + _AUTO_SCROLL_MARGIN_PX:
            canvas.yview_scroll(-1, "units")
        elif mouse_y_root > canvas_bottom - _AUTO_SCROLL_MARGIN_PX:
            canvas.yview_scroll(1, "units")

    def _on_global_motion_check_release(self, event) -> None:
        """Rede de segurança: se um arrasto está ativo mas o botão 1 já não está mais
        pressionado (bit `0x100` do `state` do X11/Tk), o `<ButtonRelease-1>` se perdeu — trata
        como se tivesse soltado agora mesmo, em vez de deixar a linha "arrastando" pra sempre
        atrás do mouse (relato real do usuário, bem reproduzível — ver ADR-0033). Ligado em
        `_on_handle_press` via `bind_all("<Motion>", ...)` — sem o prefixo de botão, então
        dispara em qualquer movimento do mouse dentro do app, com ou sem clique."""
        if self._drag is None:
            return
        if not (event.state & 0x100):
            self._log_drag("release_missed_recovered")
            self._on_handle_release()

    def _on_handle_motion(self, event) -> None:
        """Atualiza `pending_target` (onde o mouse aponta agora) a partir do próprio evento —
        `_advance_drag_target` faz a MESMA coisa a cada "tick" (ver `_compute_pending_target`),
        então esse handler é só um "empurrão" extra entre um tick e o outro; o movimento visual
        de verdade (linha arrastada e vizinhas) acontece só lá, no ritmo próprio (ver ADR-0033: o
        item arrastado deve sempre estar ocupando um dos slots válidos, nunca uma posição de
        pixel contínua/arbitrária)."""
        self._compute_pending_target("motion", event.y_root)

    def _advance_drag_target(self) -> None:
        """Roda em ritmo próprio (`_DRAG_TARGET_STEP_INTERVAL_MS`), não a cada evento de mouse —
        avança `target_offset` **uma posição por vez** em direção a `pending_target` (onde o
        mouse está de verdade agora), animando tanto a linha arrastada quanto o único vizinho que
        precisa "abrir espaço" pra ela (ver `_shift_drag_neighbors`) — o item arrastado está
        sempre ocupando um slot de verdade, nunca uma posição solta entre dois slots, e a
        transição entre um slot e o próximo nunca é instantânea (relato do usuário). Se o mouse
        já não se mexe mais, continua rodando até alcançar `pending_target` — nenhum arrasto
        rápido fica "para trás" do que o mouse indica.

        Consulta a posição do mouse (`_compute_pending_target`, sem depender de `<B1-Motion>` ter
        chegado — ver seu docstring) sempre no início, antes de decidir pra onde avançar — é essa
        consulta ativa, não os eventos de movimento, que garante o arrasto nunca "travar" mesmo
        se o Tk parar de entregar `<B1-Motion>` por um tempo."""
        drag = self._drag
        if drag is None:
            return

        self._compute_pending_target("tick_poll")
        self._maybe_auto_scroll()

        current = drag["target_offset"]
        pending = drag["pending_target"]
        if pending > current:
            new_target = current + 1
        elif pending < current:
            new_target = current - 1
        else:
            new_target = current
        self._log_drag("tick", current=current, pending=pending, new_target=new_target)
        if new_target != current:
            try:
                self._shift_drag_neighbors(new_target)
                self._animate_row_to_offset(drag["start_offset"], current, new_target)
                drag["target_offset"] = new_target
            except Exception:
                # Este método reagenda a si mesmo (linha de baixo) — uma exceção não tratada
                # aqui mataria esse reagendamento pra sempre, deixando o arrasto "travado" no
                # meio do caminho (relato do usuário) sem nenhum jeito de sair dele a não ser
                # soltar o mouse (que ainda funciona, `_on_handle_release` não depende deste
                # laço). Melhor logar e continuar tentando no próximo passo do que travar de vez.
                traceback.print_exc()

        # Fora dos limites da lista, acelera o ritmo (continua trocando UMA linha de cada vez —
        # nunca pula várias juntas, só chega na borda mais rápido) — dentro dos limites, mantém o
        # ritmo pedido de 100ms por passo.
        interval = _DRAG_TARGET_OUTSIDE_BOUNDS_INTERVAL_MS if drag["outside_bounds"] \
            else _DRAG_TARGET_STEP_INTERVAL_MS
        self._drag_tick_id = self.after(interval, self._advance_drag_target)

    def _shift_drag_neighbors(self, new_target: int) -> None:
        """Decide, pra cada linha que NÃO é a arrastada, se ela precisa "abrir espaço" (deslocar
        uma posição) pra refletir onde a linha arrastada ficaria se fosse solta agora — e anima
        só as que mudaram desde a última vez (ver `_animate_row_to_offset`)."""
        drag = self._drag
        start = drag["start_offset"]
        n = len(drag["original_list"])
        for pool_index in range(n):
            if pool_index == start:
                continue
            if start < new_target:
                shift = -1 if start < pool_index <= new_target else 0
            elif start > new_target:
                shift = 1 if new_target <= pool_index < start else 0
            else:
                shift = 0
            display_offset = pool_index + shift
            current_display = drag["displayed_offset"].get(pool_index, pool_index)
            if current_display != display_offset:
                self._animate_row_to_offset(pool_index, current_display, display_offset)
                drag["displayed_offset"][pool_index] = display_offset

    def _animate_row_to_offset(self, pool_index: int, from_offset: int, to_offset: int) -> None:
        """Desliza a linha `pool_index` (todos os seus widgets + o fundo sólido, ver
        `_show_card_bg`/ADR-0033) da posição visual `from_offset` até `to_offset`, em
        `_DRAG_ANIMATION_STEPS` passos — é o efeito de "abrir espaço" pedido (aproximação
        realista do que dá pra fazer em Tkinter, sem física de mola nativa). Usa um token por
        linha pra cancelar uma animação anterior ainda em andamento se o mouse mudar de direção
        antes dela terminar.

        Assenta a linha de volta no `.grid()` (`_grid_row_widgets`) assim que o deslize termina
        — nunca fica "flutuando" indefinidamente em `.place()`. Chegou a evitar QUALQUER `.grid()`
        durante o arrasto inteiro numa versão anterior (pra não disparar o recálculo de
        `scrollregion` do `CTkScrollableFrame` — ver ADR, seção sobre coisas fora da lista
        tremendo), mas isso trocava um bug por outro: cada linha tocada ficava presa em
        `.place()` até soltar de vez, deixando um "buraco" vazio (mas reservado por `minsize`,
        ver `_on_handle_press`) na posição de grid que ela abandonou — "fantasmas" onde a
        transação deveria estar, mais de um ao mesmo tempo num arrasto que passa por várias
        linhas (relato do usuário, com screenshot numerado). Testado isolado: com o `minsize`
        já travado, voltar a chamar `.grid()` no meio do arrasto **não** dispara mais nenhum
        recálculo de `scrollregion` — a causa raiz era só o colapso da linha do grid, já resolvida
        ali; não precisava também evitar `.grid()` por completo."""
        if from_offset == to_offset:
            return
        row_widgets = self._row_pool[pool_index]
        pixel_delta = (to_offset - from_offset) * self._drag["row_step"]
        is_dragged_row = pool_index == self._drag["start_offset"]
        card = self._drag_card if is_dragged_row else self._neighbor_card

        token = self._drag["anim_token"].get(pool_index, 0) + 1
        self._drag["anim_token"][pool_index] = token

        if not is_dragged_row:
            # `_neighbor_card` é um único widget reusado por QUALQUER vizinha que esteja
            # deslizando — só pode ter uma "dona" de cada vez. `anim_token` sozinho não bastava:
            # ele é rastreado por linha (`pool_index`), então se dois "hops" disparassem antes do
            # primeiro terminar (bem possível sob uso real — carga do sistema, arrasto rápido
            # cruzando várias linhas), a animação da vizinha ANTERIOR continuava achando que
            # ainda era válida (seu próprio token não mudou) e seguia chamando `.place()` no
            # MESMO widget físico que a vizinha NOVA também estava controlando — as duas
            # brigando pela posição do cartão compartilhado, pulando entre as duas linhas (relato
            # do usuário: "uma cópia dele fica aparecendo e sumindo no topo"). Reivindicar aqui
            # invalida qualquer dona anterior — ver a checagem extra em `step()` abaixo.
            self._drag["neighbor_card_owner"] = pool_index

        # Garante o fundo sólido visível (e por baixo do conteúdo) desde o início do deslize —
        # sem ele, os campos individuais (com espaço transparente entre um e outro) deixavam o
        # conteúdo de outra linha aparecer por trás enquanto cruzavam (relato do usuário).
        #
        # ARMADILHA REAL DO TK (achada no log de diagnóstico, ver ADR-0033): usar o valor
        # DEVOLVIDO por `_show_card_bg`, nunca ler `card.winfo_y()` logo em seguida — na PRIMEIRA
        # vez que um widget é posicionado com `.place()`, o Tk só atualiza a geometria consultável
        # via `winfo_*` depois de processar a fila de eventos; ler na mesma chamada síncrona
        # devolve `0` (nunca foi "realizado" ainda). Isso só afetava `_neighbor_card` na prática —
        # `_drag_card` já tinha sido posicionado em `_on_handle_press`, bem antes, com várias
        # voltas do laço de eventos de sobra (o `self.after(100ms, ...)` até o primeiro passo já
        # garante isso). O sintoma era a linha vizinha começar a deslizar do TOPO do frame (y=0)
        # em vez da posição real dela — o "fantasma aparecendo e sumindo no topo" relatado.
        card_start_y = self._show_card_bg(card, row_widgets, from_offset)

        # Só x/y — CTk não aceita width/height em `.place()` (ver `_on_handle_press`).
        animations = [(widget, widget.winfo_x(), widget.winfo_y()) for widget in row_widgets.values()]
        self._log_drag(
            "animate_start", pool_index=pool_index, from_offset=from_offset, to_offset=to_offset,
            is_dragged_row=is_dragged_row, card="drag" if is_dragged_row else "neighbor",
            card_start_y=card_start_y, token=token)

        def step(i: int) -> None:
            if self._drag is None or self._drag["anim_token"].get(pool_index) != token:
                self._log_drag(
                    "animate_cancel_token", pool_index=pool_index, i=i, reason="anim_token")
                return  # cancelada: outra animação pra essa linha começou antes desta terminar
            if not is_dragged_row and self._drag.get("neighbor_card_owner") != pool_index:
                # Outra vizinha assumiu o cartão compartilhado nesse meio tempo — diferente do
                # cancelamento por `anim_token` (onde uma animação MAIS NOVA da MESMA linha vai
                # terminar o serviço), aqui ninguém mais vai cuidar desta linha: o token dela
                # continua válido, só o cartão que não pode mais usar. Sem assentar aqui, ela
                # ficava órfã, flutuando numa posição intermediária pra sempre — a posição de
                # grid original dela nunca mais era preenchida, um "buraco" (relato do usuário,
                # com screenshot numerado — só "consertava" se essa MESMA linha fosse tocada num
                # arrasto futuro). Snap direto pro destino em vez de animação, já que não dá mais
                # pra continuar usando o cartão compartilhado pra deslizar suavemente.
                self._log_drag(
                    "animate_cancel_owner", pool_index=pool_index, i=i,
                    owner_agora=self._drag.get("neighbor_card_owner"))
                # Assenta direto no destino (sem terminar a animação suave — não dá mais pra usar
                # o cartão compartilhado) — `.grid()` troca o gerenciador de geometria sozinho,
                # não precisa desfazer o `.place()` antes.
                self._grid_row_widgets(row_widgets, to_offset)
                return
            t = i / _DRAG_ANIMATION_STEPS
            card.place(y=round(card_start_y + pixel_delta * t))
            for widget, x, start_y in animations:
                widget.place(x=x, y=round(start_y + pixel_delta * t))
            if i < _DRAG_ANIMATION_STEPS:
                self.after(_DRAG_ANIMATION_INTERVAL_MS, lambda: step(i + 1))
            else:
                self._log_drag(
                    "animate_end", pool_index=pool_index, card_final_y=card.winfo_y())
                # Assenta de volta no grid — nunca deixa a linha "flutuando" indefinidamente em
                # `.place()` (ver docstring: isso deixava um buraco vazio na posição antiga
                # dela). Com `minsize` travado (`_on_handle_press`), isso não dispara mais o
                # recálculo de `scrollregion` que fazia coisas fora da lista tremerem.
                self._grid_row_widgets(row_widgets, to_offset)
                if is_dragged_row:
                    # A arrastada volta a ficar visível no grid, mas continua "segurada" — o
                    # cartão dela reaparece por cima (senão sumiria entre um hop e o outro).
                    # `to_offset`, não reler a posição — ver docstring de `_show_card_bg`.
                    self._show_card_bg(card, row_widgets, to_offset)
                else:
                    self._hide_card_bg(card)

        step(0)

    def _on_handle_release(self, _event=None) -> None:
        drag = self._drag
        if drag is None:
            return
        self._log_drag(
            "release", target_offset=drag["target_offset"], pending_target=drag["pending_target"])
        self._drag = None
        if self._drag_tick_id is not None:
            self.after_cancel(self._drag_tick_id)
            self._drag_tick_id = None
        if self._global_motion_bind_id is not None:
            self.winfo_toplevel().unbind_all("<Motion>")
            self._global_motion_bind_id = None

        start = drag["start_offset"]
        # `pending_target` (não `target_offset`) — é a posição de verdade indicada pelo mouse no
        # instante de soltar; `target_offset` só avança um passo por vez (ver
        # `_advance_drag_target`) e pode estar atrasado se o usuário soltar logo depois de um
        # arrasto rápido. O drop sempre respeita onde o mouse está, mesmo que a "dominó" visual
        # de abrir espaço não tenha alcançado ali ainda — o `refresh()` no final corrige a tela
        # inteira de qualquer forma.
        target = drag["pending_target"]
        row_widgets = self._row_pool[start]
        self._hide_card_bg(self._drag_card)
        self._hide_card_bg(self._neighbor_card)  # por segurança, caso alguma vizinha ainda esteja com o dela visível
        for widget in row_widgets.values():
            if isinstance(widget, ctk.CTkLabel):
                widget.configure(fg_color="transparent")
            elif isinstance(widget, OutlinedLabel):
                widget.reset_background()

        if target == start:
            # Só um clique/arrasto que voltou pro mesmo lugar — re-renderiza pra devolver tudo
            # ao grid (a linha arrastada ainda está em modo `.place()`).
            self._render_transaction_list(self._filtered_transactions())
            self._flush_drag_log()
            return

        original_list = drag["original_list"]
        dragged = original_list[start]
        final_order = list(original_list)
        final_order.pop(start)
        final_order.insert(target, dragged)

        # Indexação fracionária entre os vizinhos finais (lista topo->baixo em sort_order
        # decrescente, ver ADR-0033): sem vizinho acima = novo topo (maior que quem ficou
        # embaixo); sem vizinho abaixo = novo fim (menor que quem ficou acima); senão, a média.
        above = final_order[target - 1].sort_order if target > 0 else None
        below = final_order[target + 1].sort_order if target < len(final_order) - 1 else None
        if above is None:
            new_sort_order = below + 1.0
        elif below is None:
            new_sort_order = above - 1.0
        else:
            new_sort_order = (above + below) / 2.0

        old_sort_order = dragged.sort_order
        backend_bridge.update_transaction_sort_order(dragged.id, new_sort_order)
        self._undo_stack.push(ReorderTransactionCommand(dragged.id, old_sort_order, new_sort_order))
        # Arrastar sempre volta pro modo manual, mesmo se a lista estava sendo vista ordenada
        # por data no momento (ver ADR-0033) — o usuário acabou de tomar controle manual.
        self._date_sort_mode = None
        self._date_header_label.configure(text=self._date_header_text())
        self.refresh()
        self._flush_drag_log()

    def _toggle_status(self, transaction_id: str, currently_paid: bool) -> None:
        enums = backend_bridge.transaction_enums()
        old_status = enums["paid"] if currently_paid else enums["pending"]
        new_status = enums["pending"] if currently_paid else enums["paid"]
        backend_bridge.set_transaction_status(transaction_id, new_status)
        self._undo_stack.push(ToggleStatusCommand(transaction_id, old_status, new_status))
        self.refresh()

    def _toggle_recurring(self, transaction_id: str, currently_recurring: bool) -> None:
        """Fixa/desfixa (ícone de pin, ver ADR-0034) — a clonagem pro mês novo em si só acontece
        em `_on_month_added`, não aqui; isso só grava a marca."""
        new_value = not currently_recurring
        backend_bridge.update_transaction_recurring(transaction_id, new_value)
        self._undo_stack.push(TogglePinCommand(transaction_id, currently_recurring))
        self.refresh()

    def _delete(self, transaction_id: str) -> None:
        target = next(
            (t for t in backend_bridge.list_transactions() if t.id == transaction_id), None)
        backend_bridge.delete_transaction(transaction_id)
        if target is not None:
            self._undo_stack.push(DeleteTransactionCommand(target))
        self.refresh()


def _format_money(cents: int) -> str:
    return f"R$ {cents / 100:,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")
