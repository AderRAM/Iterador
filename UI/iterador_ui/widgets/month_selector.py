"""Seletor de mês da aba Início — navega pelas transações mês a mês. Ver Guide/file-map.md,
Guide/decisions/0016-monthly-transaction-navigation.md,
Guide/decisions/0018-bounded-month-navigation-and-add-month.md e
Guide/decisions/0019-remove-month-with-undo.md.

As setas ◀/▶ são limitadas aos meses que já existem (com lançamento, ou adicionados manualmente
via "+ Mês") — não ficam avançando indefinidamente por meses vazios que "não existem" ainda. Pra
começar a lançar num mês que ainda não tem nada, o usuário usa "+ Mês" e digita a data.

Remover um mês (botão "Remover mês") é orquestrado pela `DashboardView`, não por este widget —
ele só expõe os métodos de bookkeeping (`is_extra_month`/`remove_month`/`neighbor_of`/
`force_select`) que o comando de desfazer/refazer (`RemoveMonthCommand`) precisa pra repor o mês
na tira em caso de undo. A confirmação e a decisão de apagar transações de verdade ficam do lado
de fora, porque só quem tem acesso ao backend/undo stack sabe o que precisa ser desfeito.
"""

import datetime

import customtkinter as ctk

from iterador_ui import theme
from iterador_ui.widgets.add_month_dialog import AddMonthDialog
from iterador_ui.widgets.dialog_utils import open_singleton

_MONTH_NAMES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


def current_month() -> str:
    return datetime.date.today().strftime("%Y-%m")


def month_label(month_str: str) -> str:
    year, month = (int(part) for part in month_str.split("-"))
    return f"{_MONTH_NAMES[month - 1]}/{year}"


class MonthSelector(ctk.CTkFrame):
    def __init__(self, master, on_select, on_remove_month, on_add_month=None):
        super().__init__(master, fg_color="transparent")
        self._on_select = on_select
        self._on_remove_month = on_remove_month
        # Chamado ANTES de selecionar o mês novo (ver `_add_month`) — dá pra quem estiver
        # ouvindo (`DashboardView`) clonar transações fixadas pra dentro dele (ADR-0034) antes
        # da seleção/refresh acontecerem, e ainda ler `selected_month()` como "o mês anterior".
        self._on_add_month = on_add_month
        self._selected_month = current_month()
        # Meses adicionados manualmente via "+ Mês", sem lançamento ainda — precisa lembrar
        # deles à parte, já que `update_months()` só recebe os meses que têm transação.
        self._extra_months: set[str] = set()
        self._months_sorted: list[str] = [self._selected_month]
        # month_str -> botão da tira — reaproveitado entre chamadas de `update_months()` quando
        # o conjunto de meses não muda (ver ADR-0026): trocar de mês, marcar Pago/A pagar,
        # digitar na busca etc. quase nunca muda quais meses existem, então reconstruir a tira
        # inteira nesses casos era desperdício (~290ms medidos com ~30 meses reais).
        self._month_buttons: dict[str, ctk.CTkButton] = {}
        # Último mês que ficou com o destaque roxo aplicado de verdade — ver `update_months()`:
        # só reconfigura os 2 botões cujo estado (destacado/não) realmente mudou, em vez de
        # TODOS os da tira (qualquer `.configure(fg_color=...)` redesenha o botão inteiro no
        # CustomTkinter mesmo quando o valor não muda — medido ~34ms por troca de mês à toa,
        # com ~30 meses reais, só nisso).
        self._highlighted_month: str | None = None

        self._prev_button = ctk.CTkButton(
            self, text="◀", width=32, fg_color=theme.BG_SURFACE, text_color=theme.TEXT_PRIMARY,
            hover_color=theme.INDIGO, command=self._go_next,
        )
        self._prev_button.pack(side="left", padx=(0, 4))

        self._strip = ctk.CTkScrollableFrame(
            self, orientation="horizontal", fg_color="transparent", height=44)
        self._strip.pack(side="left", fill="x", expand=True)

        self._next_button = ctk.CTkButton(
            self, text="▶", width=32, fg_color=theme.BG_SURFACE, text_color=theme.TEXT_PRIMARY,
            hover_color=theme.INDIGO, command=self._go_previous,
        )
        self._next_button.pack(side="left", padx=(4, 0))

        ctk.CTkButton(
            self, text="+ Mês", width=72, command=self._open_add_month_dialog,
            **theme.outline_button_style(),
        ).pack(side="left", padx=(8, 0))

        ctk.CTkButton(
            self, text="Remover mês", width=100, command=self._request_remove_month,
            **theme.outline_button_style(),
        ).pack(side="left", padx=(4, 0))

    def selected_month(self) -> str:
        return self._selected_month

    def update_months(self, available_months) -> None:
        """available_months: meses (YYYY-MM) que têm pelo menos um lançamento. O mês
        selecionado atual e os meses adicionados manualmente sempre aparecem na tira, mesmo
        sem lançamento."""
        months = sorted(set(available_months) | self._extra_months | {self._selected_month})

        rebuilt = months != self._months_sorted or not self._month_buttons
        if rebuilt:
            # Conjunto de meses mudou de verdade (ou é a primeira vez) — reconstrói a tira toda.
            # Cada botão já nasce com a cor certa (destacado ou não) — evita um `.configure()`
            # redundante logo depois só pra aplicar o que já dava pra passar na criação.
            for child in self._strip.winfo_children():
                child.destroy()
            self._month_buttons = {}

            for month_str in reversed(months):  # mais recente primeiro
                is_selected = month_str == self._selected_month
                button = ctk.CTkButton(
                    self._strip, text=month_label(month_str), width=120,
                    fg_color=theme.INDIGO if is_selected else "transparent",
                    text_color="#FFFFFF" if is_selected else theme.TEXT_PRIMARY,
                    hover_color=theme.BG_SURFACE,
                    command=lambda m=month_str: self._select(m))
                button.pack(side="left", padx=2)
                self._month_buttons[month_str] = button
            self._highlighted_month = self._selected_month
        elif self._highlighted_month != self._selected_month:
            # Caso comum (trocar de mês dentro do mesmo conjunto): só os 2 botões cujo estado
            # realmente mudou — o que perde o destaque e o que ganha — precisam de
            # `.configure()`. Texto branco fixo (não `theme.TEXT_PRIMARY`) no destacado — o
            # fundo é sempre `theme.INDIGO` (roxo) nos dois temas, e `TEXT_PRIMARY` no modo
            # claro é quase preto, ilegível em cima do roxo.
            old_button = self._month_buttons.get(self._highlighted_month)
            if old_button is not None:
                old_button.configure(fg_color="transparent", text_color=theme.TEXT_PRIMARY)
            new_button = self._month_buttons.get(self._selected_month)
            if new_button is not None:
                new_button.configure(fg_color=theme.INDIGO, text_color="#FFFFFF")
            self._highlighted_month = self._selected_month

        self._months_sorted = months
        index = months.index(self._selected_month)
        self._prev_button.configure(state="normal" if index < len(months) - 1 else "disabled")
        self._next_button.configure(state="normal" if index > 0 else "disabled")

    def _select(self, month_str: str) -> None:
        self._selected_month = month_str
        self._on_select(month_str)

    def _go_previous(self) -> None:
        index = self._months_sorted.index(self._selected_month)
        if index > 0:
            self._select(self._months_sorted[index - 1])

    def _go_next(self) -> None:
        index = self._months_sorted.index(self._selected_month)
        if index < len(self._months_sorted) - 1:
            self._select(self._months_sorted[index + 1])

    def _open_add_month_dialog(self) -> None:
        open_singleton(self, "_add_month_dialog",
                        lambda: AddMonthDialog(self, on_add=self._add_month))

    def _add_month(self, month_str: str) -> None:
        # Avisa ANTES de mudar qualquer bookkeeping/seleção — ver comentário de `_on_add_month`
        # em __init__ (ADR-0034).
        if self._on_add_month is not None:
            self._on_add_month(month_str)
        self.add_extra_month(month_str)
        self._select(month_str)

    def _request_remove_month(self) -> None:
        self._on_remove_month(self._selected_month)

    def add_extra_month(self, month_str: str) -> None:
        """Marca month_str como adicionado manualmente (sem lançamento) — usado por "+ Mês" e
        por `RemoveMonthCommand.undo()` quando o mês removido não tinha nenhuma transação."""
        self._extra_months.add(month_str)

    def is_extra_month(self, month_str: str) -> bool:
        return month_str in self._extra_months

    def remove_month(self, month_str: str) -> None:
        """Tira month_str do bookkeeping local (`_extra_months`). Não mexe em transação nenhuma
        — quem decide o que apagar/desfazer é `DashboardView`/`RemoveMonthCommand`; não mexe na
        seleção — usar `force_select()` depois, se for o caso."""
        self._extra_months.discard(month_str)

    def neighbor_of(self, month_str: str) -> str:
        """Mês vizinho mais próximo de month_str na tira atual — pra onde ir depois de remover
        o mês selecionado. Prefere o mês anterior (mais antigo); se month_str for o mais antigo,
        usa o próximo; se não sobrar nenhum, cai no mês atual."""
        months = self._months_sorted
        if month_str not in months:
            return current_month()
        index = months.index(month_str)
        remaining = [m for m in months if m != month_str]
        if not remaining:
            return current_month()
        return months[index - 1] if index > 0 else remaining[0]

    def force_select(self, month_str: str) -> None:
        """Troca o mês selecionado sem disparar `on_select` — quem chama é responsável por
        atualizar a UI depois (ex. `RemoveMonthCommand`, que é seguido de `DashboardView.refresh()`
        pelo próprio `UndoStack.undo()/redo()`)."""
        self._selected_month = month_str
