"""Diálogo modal para criar ou editar um investimento. Ver Guide/file-map.md.

Campos essenciais (Nome, Tipo, Valor atual) ficam sempre visíveis; o resto (moeda,
rentabilidade, taxas, % da Selic/CDI) fica atrás do botão "Mais opções", colapsado por padrão.

Ao criar (sem passar `investment`), os campos avançados vêm pré-preenchidos com o padrão de uma
Caixinha Nubank (100% do CDI, sem taxas) — é o investimento que o usuário mais adiciona/resgata
no dia a dia, então quem não abrir "Mais opções" já cria com esses valores (ver
Guide/decisions/0009-investment-edit-and-nubank-caixinha-defaults.md).
"""

import customtkinter as ctk

from iterador_ui import backend_bridge, market_data, theme
from iterador_ui.widgets.dialog_utils import make_modal

# Padrão de uma Caixinha Nubank (RDB de resgate imediato): 100% do CDI, sem taxa de
# administração/custódia. Ver ADR-0009 e a pesquisa em ADR-0008.
_NUBANK_CAIXINHA_DEFAULTS = {
    "type": "Caixinha Nubank",
    "yield_rate": "0",
    "fees_rate": "0",
    "selic_percentage": "100",
}


class InvestmentFormDialog(ctk.CTkToplevel):
    def __init__(self, master, on_created, investment=None):
        super().__init__(master)
        self._on_created = on_created
        self._investment = investment
        is_edit = investment is not None

        self.title("Editar investimento" if is_edit else "Novo investimento")
        self.geometry("360x400")  # margem extra — ver TransactionFormDialog._HEIGHT
        self.configure(fg_color=theme.BG_APP)
        make_modal(self, master)

        self._name_entry = self._add_field(
            self, "Nome", "ex. Tesouro Selic, CDB Itaú...",
            default=investment.name if is_edit else "")
        self._type_entry = self._add_field(
            self, "Tipo", "ex. Renda fixa, Ações, Fundos...",
            default=investment.type if is_edit else _NUBANK_CAIXINHA_DEFAULTS["type"])
        self._value_entry = self._add_field(
            self, "Valor atual (R$)", "0,00",
            default=f"{investment.current_value.cents / 100:.2f}".replace(".", ",")
            if is_edit else "")

        self._advanced_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._currency_entry = self._add_field(
            self._advanced_frame, "Moeda", None,
            default=investment.current_value.currency if is_edit else "BRL")
        self._yield_entry = self._add_field(
            self._advanced_frame, "Rentabilidade (%)", "0,0",
            default=str(investment.yield_rate) if is_edit
            else _NUBANK_CAIXINHA_DEFAULTS["yield_rate"])
        self._fees_entry = self._add_field(
            self._advanced_frame, "Taxas (%)", "0,0",
            default=str(investment.fees_rate) if is_edit
            else _NUBANK_CAIXINHA_DEFAULTS["fees_rate"])
        self._selic_entry = self._add_field(
            self._advanced_frame, "% da Selic/CDI", "0,0",
            default=str(investment.selic_percentage) if is_edit
            else _NUBANK_CAIXINHA_DEFAULTS["selic_percentage"])

        self._selic_info_label = ctk.CTkLabel(
            self._advanced_frame, text="", text_color=theme.TEXT_PRIMARY, font=ctk.CTkFont(size=11))
        self._selic_info_label.pack(anchor="w", padx=20, pady=(0, 4))
        ctk.CTkButton(
            self._advanced_frame, text="Buscar taxa Selic atual (BCB)", fg_color=theme.INDIGO,
            command=self._fetch_selic,
        ).pack(fill="x", padx=20, pady=(0, 8))

        self._advanced_visible = False

        self._toggle_button = ctk.CTkButton(
            self, text="Mais opções ▾", fg_color="transparent",
            text_color=theme.TEXT_PRIMARY, hover_color=theme.BG_SURFACE,
            command=self._toggle_advanced,
        )
        self._toggle_button.pack(fill="x", padx=20, pady=(8, 0))

        self._error_label = ctk.CTkLabel(self, text="", text_color=theme.ACCENT_EXPENSE)
        self._error_label.pack(anchor="w", padx=20, pady=(10, 0))

        ctk.CTkButton(
            self, text="Salvar alterações" if is_edit else "Criar investimento",
            fg_color=theme.ACCENT_EXPENSE, command=self._submit,
        ).pack(fill="x", padx=20, pady=(20, 20))

    def _add_field(self, parent, label: str, placeholder, default: str = "") -> ctk.CTkEntry:
        ctk.CTkLabel(parent, text=label, text_color=theme.TEXT_PRIMARY).pack(
            anchor="w", padx=20, pady=(12, 4))
        entry = ctk.CTkEntry(parent, placeholder_text=placeholder)
        if default:
            entry.insert(0, default)
        entry.pack(fill="x", padx=20)
        return entry

    def _toggle_advanced(self) -> None:
        self._advanced_visible = not self._advanced_visible
        if self._advanced_visible:
            self._advanced_frame.pack(fill="x", before=self._toggle_button)
            self._toggle_button.configure(text="Menos opções ▴")
            self.geometry("360x680")
        else:
            self._advanced_frame.pack_forget()
            self._toggle_button.configure(text="Mais opções ▾")
            self.geometry("360x400")

    def _fetch_selic(self) -> None:
        # Chamada síncrona: a API do BCB responde rápido e o timeout (5s) é curto o bastante
        # para não travar a UI de forma perceptível. Nunca lança exceção — ver market_data.py.
        self._selic_info_label.configure(text="Buscando...")
        self.update_idletasks()

        rate = market_data.fetch_current_selic_rate()
        if rate is None:
            self._selic_info_label.configure(
                text="Não foi possível buscar (sem internet?). Preencha manualmente.")
            return

        self._selic_info_label.configure(
            text=f"Selic atual: {rate.percent_per_year:.2f}% a.a. (BCB, {rate.reference_date})")

    def _submit(self) -> None:
        name = self._name_entry.get().strip()
        investment_type = self._type_entry.get().strip()
        if not name or not investment_type:
            self._error_label.configure(text="Informe nome e tipo.")
            return

        try:
            value_cents = round(float(self._value_entry.get().strip().replace(",", ".") or "0") * 100)
            yield_rate = float(self._yield_entry.get().strip().replace(",", ".") or "0")
            fees_rate = float(self._fees_entry.get().strip().replace(",", ".") or "0")
            selic_percentage = float(self._selic_entry.get().strip().replace(",", ".") or "0")
        except ValueError:
            self._error_label.configure(text="Verifique os valores numéricos.")
            return

        currency = self._currency_entry.get().strip().upper() or "BRL"

        if self._investment is not None:
            backend_bridge.update_investment(
                self._investment.id, name, investment_type, value_cents, currency, yield_rate,
                fees_rate, selic_percentage)
        else:
            backend_bridge.create_investment(
                name, investment_type, value_cents, currency, yield_rate, fees_rate,
                selic_percentage)
        self._on_created()
        self.destroy()
