"""Lista de investimentos — chama o backend de verdade (fatia de referência).

Não existe conceito de "Conta" no Iterador: dinheiro e investimentos são os dois lugares onde o
valor do usuário fica (ver Guide/decisions/0007-remove-account-add-investment.md). Esta view
substitui a antiga tela de Contas. Ver Guide/functions.md.
"""

import customtkinter as ctk

from iterador_ui import backend_bridge, theme
from iterador_ui.widgets.confirm_dialog import ConfirmDialog
from iterador_ui.widgets.dialog_utils import open_singleton
from iterador_ui.widgets.investment_form_dialog import InvestmentFormDialog


class InvestmentsView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=theme.BG_APP)

        # Rola a tela inteira (mesmo padrão do DashboardView) — com muitos investimentos a lista
        # passava da altura da janela e ficava inalcançável sem redimensionar a janela na mão.
        page_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        page_scroll.pack(fill="both", expand=True)

        header = ctk.CTkFrame(page_scroll, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(24, 8))

        ctk.CTkLabel(
            header, text="Investimentos",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=theme.TEXT_PRIMARY,
        ).pack(side="left")

        ctk.CTkButton(
            header, text="+ Novo investimento", fg_color=theme.ACCENT_EXPENSE,
            command=self._open_new_investment_dialog,
        ).pack(side="right")

        self._list_frame = ctk.CTkFrame(page_scroll, fg_color="transparent")
        self._list_frame.pack(fill="both", expand=True, padx=24, pady=8)
        self._list_frame.grid_columnconfigure(0, weight=1)

        self._empty_label = ctk.CTkLabel(
            self._list_frame, text="Nenhum investimento ainda.", text_color=theme.TEXT_PRIMARY)

        # Pool de linhas — reaproveitado entre chamadas de `refresh()` em vez de destruir/
        # recriar tudo toda vez (mesmo motivo/técnica de `DashboardView`, ver ADR-0026): cada
        # linha tem uns 6 widgets CTk, caros de construir (redesenho de retângulo arredondado
        # por widget); recriar tudo a cada troca de aba/edição fazia a lista inteira "piscar" e
        # ficava perceptivelmente lento com poucos investimentos já (medido: ~270ms só pra
        # revisitar a aba com 8 investimentos, escalando linear com a quantidade). `grid()` (não
        # `pack()`) pra cada linha, com `row=index` explícito — dá posição determinística por
        # índice mesmo se a ordem dos investimentos mudar entre uma renderização e outra
        # (`pack()` reaproveitado não reordena sozinho quem já está gerenciado).
        self._row_pool: list[dict] = []

        self.refresh()

    def _open_new_investment_dialog(self) -> None:
        open_singleton(self, "_investment_dialog",
                        lambda: InvestmentFormDialog(self, on_created=self.refresh))

    def _open_edit_investment_dialog(self, investment) -> None:
        open_singleton(self, "_investment_dialog", lambda: InvestmentFormDialog(
            self, on_created=self.refresh, investment=investment))

    def _get_or_create_row(self, index: int) -> dict:
        if index < len(self._row_pool):
            return self._row_pool[index]

        row = ctk.CTkFrame(self._list_frame, fg_color=theme.BG_SURFACE,
                            border_width=1, border_color=theme.INDIGO, corner_radius=8)

        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", padx=12, pady=8, fill="x", expand=True)
        name_label = ctk.CTkLabel(
            info, text_color=theme.TEXT_PRIMARY, font=ctk.CTkFont(weight="bold"))
        name_label.pack(anchor="w")
        details_label = ctk.CTkLabel(
            info, text_color=theme.TEXT_PRIMARY, font=ctk.CTkFont(size=11))
        details_label.pack(anchor="w")

        value_label = ctk.CTkLabel(row, text_color=theme.ACCENT_HIGHLIGHT)
        value_label.pack(side="right", padx=12, pady=8)

        remove_button = ctk.CTkButton(
            row, text="Remover", width=64, fg_color="transparent",
            text_color=theme.TEXT_PRIMARY, hover_color=theme.BG_APP)
        remove_button.pack(side="right", padx=(0, 4), pady=8)
        edit_button = ctk.CTkButton(
            row, text="Editar", width=64, fg_color="transparent",
            text_color=theme.TEXT_PRIMARY, hover_color=theme.BG_APP)
        edit_button.pack(side="right", padx=(0, 4), pady=8)

        row_widgets = {
            "frame": row, "name": name_label, "details": details_label,
            "value": value_label, "edit": edit_button, "remove": remove_button,
        }
        self._row_pool.append(row_widgets)
        return row_widgets

    def refresh(self) -> None:
        investments = backend_bridge.list_investments()

        if not investments:
            self._empty_label.grid(row=0, column=0, sticky="w")
        else:
            self._empty_label.grid_remove()

        for index, investment in enumerate(investments):
            row_widgets = self._get_or_create_row(index)
            row_widgets["name"].configure(text=investment.name)
            details = (f"{investment.type} · rentabilidade {investment.yield_rate:.2f}% · "
                       f"taxas {investment.fees_rate:.2f}% · {investment.selic_percentage:.0f}% "
                       f"da Selic")
            row_widgets["details"].configure(text=details)
            value_text = f"{investment.current_value.cents / 100:.2f} {investment.current_value.currency}"
            row_widgets["value"].configure(text=value_text)
            row_widgets["edit"].configure(
                command=lambda inv=investment: self._open_edit_investment_dialog(inv))
            row_widgets["remove"].configure(
                command=lambda inv=investment: self._delete_investment(inv))
            row_widgets["frame"].grid(row=index, column=0, sticky="ew", pady=4)

        # Linhas do pool sobrando de uma renderização anterior maior (investimento removido) —
        # escondidas, não destruídas, prontas pra reaparecer sem reconstruir nada se a lista
        # crescer de novo (mesmo princípio de `DashboardView._render_transaction_list`).
        for extra_row in self._row_pool[len(investments):]:
            extra_row["frame"].grid_remove()

    def _delete_investment(self, investment) -> None:
        open_singleton(self, "_confirm_dialog", lambda: ConfirmDialog(
            self, title="Remover investimento",
            message=f'Remover "{investment.name}"? Lançamentos e metas de economia que '
                    "apontavam pra ele continuam existindo, só perdem esse vínculo.",
            confirm_text="Remover",
            on_confirm=lambda: self._do_delete_investment(investment.id)))

    def _do_delete_investment(self, investment_id: str) -> None:
        backend_bridge.delete_investment(investment_id)
        self.refresh()
