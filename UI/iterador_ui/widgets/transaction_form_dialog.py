"""Diálogo modal para adicionar ou editar um lançamento (receita/despesa). Ver Guide/file-map.md.

Data, Descrição, Valor, Tipo (Receita/Despesa) e Pago/Pendente. As categorias dependem do Tipo
(ver ADR-0014): Despesa → Essencial/Lazer/Investimento; Receita → Ativa/Passiva. Quando a
categoria é "Investimento" ou "Passiva", um segundo seletor aparece com os investimentos
existentes (mais a opção "Nenhum (genérico)", o padrão) — escolher um investimento faz a
transação influenciar o valor dele (aporte ou resgate/rendimento, ver
Guide/decisions/0012-fixed-categories-and-investment-link.md); "Nenhum" não afeta nenhum
investimento e pode ser trocado por um real depois, editando o lançamento (ver
Guide/decisions/0022-generic-unlabeled-investment-link.md).
"""

import datetime

import customtkinter as ctk

from iterador_ui import backend_bridge, theme
from iterador_ui.widgets.category_picker import CategoryPicker
from iterador_ui.widgets.dialog_utils import make_modal

# Altura generosa de propósito: com os campos + botão, o conteúdo já passava da altura
# original, deixando o botão "Adicionar" cortado até o usuário redimensionar a janela na mão.
# +50px em relação ao original — `CategoryPicker` (ver ADR-0029) pode ocupar até 2 linhas de
# chips, contra 1 linha do `CTkSegmentedButton` antigo; altura fixa independente de quantas
# categorias existem (excesso rola dentro do espaço fixo, não estica a janela).
_HEIGHT_BASE = "320x670"
_HEIGHT_WITH_INVESTMENT = "320x750"

_DATE_FORMAT = "%d/%m/%Y"

# Ver ADR-0022 — investimento vinculado é opcional pra categorias Investimento/Passiva.
_NO_INVESTMENT_LABEL = "Nenhum (genérico)"


class TransactionFormDialog(ctk.CTkToplevel):
    def __init__(self, master, on_created, transaction=None):
        super().__init__(master)
        self._on_created = on_created
        self._transaction = transaction
        is_edit = transaction is not None

        self.title("Editar lançamento" if is_edit else "Novo lançamento")
        self.geometry(_HEIGHT_BASE)
        self.configure(fg_color=theme.BG_APP)
        make_modal(self, master)

        ctk.CTkLabel(self, text="Data", text_color=theme.TEXT_PRIMARY).pack(
            anchor="w", padx=20, pady=(20, 4))
        self._date_entry = ctk.CTkEntry(self, placeholder_text="DD/MM/AAAA")
        # Padrão: dia atual — editável pelo usuário, tanto ao criar quanto ao editar.
        initial_date = (datetime.date.fromisoformat(transaction.occurred_at) if is_edit
                         else datetime.date.today())
        self._date_entry.insert(0, initial_date.strftime(_DATE_FORMAT))
        self._date_entry.pack(fill="x", padx=20)

        ctk.CTkLabel(self, text="Descrição", text_color=theme.TEXT_PRIMARY).pack(
            anchor="w", padx=20, pady=(16, 4))
        self._description_entry = ctk.CTkEntry(self, placeholder_text="ex. Mercado, Salário...")
        if is_edit:
            self._description_entry.insert(0, transaction.description)
        self._description_entry.pack(fill="x", padx=20)

        ctk.CTkLabel(self, text="Valor (R$)", text_color=theme.TEXT_PRIMARY).pack(
            anchor="w", padx=20, pady=(16, 4))
        self._value_entry = ctk.CTkEntry(self, placeholder_text="0,00")
        if is_edit:
            value_text = f"{abs(transaction.amount.cents) / 100:.2f}".replace(".", ",")
            self._value_entry.insert(0, value_text)
        self._value_entry.pack(fill="x", padx=20)

        ctk.CTkLabel(self, text="Tipo", text_color=theme.TEXT_PRIMARY).pack(
            anchor="w", padx=20, pady=(16, 4))
        initial_type = "Receita" if (is_edit and transaction.amount.cents >= 0) else "Despesa"
        self._type_var = ctk.StringVar(value=initial_type)
        ctk.CTkSegmentedButton(
            self, values=["Despesa", "Receita"], variable=self._type_var,
            selected_color=theme.ACCENT_EXPENSE,
            command=lambda _choice: self._update_category_options(),
        ).pack(fill="x", padx=20)

        ctk.CTkLabel(self, text="Categoria", text_color=theme.TEXT_PRIMARY).pack(
            anchor="w", padx=20, pady=(16, 4))
        self._category_var = ctk.StringVar(
            value=transaction.category_name if is_edit else backend_bridge.expense_category_names()[0])
        # `CategoryPicker` (ver ADR-0029), não `CTkSegmentedButton` — esse não quebra em várias
        # linhas, e com categorias personalizadas (ADR-0028) a lista pode passar de ~4 nomes.
        self._category_picker = CategoryPicker(
            self, values=self._category_options(), variable=self._category_var)
        self._category_picker.pack(fill="x", padx=20)
        # Cobre tanto clicar num chip quanto `.set()` programático (`_update_category_options()`
        # corrigindo uma seleção inválida) — `CategoryPicker` não tem um parâmetro `command`
        # próprio, só observa a StringVar por conta própria pro destaque do chip selecionado.
        self._category_var.trace_add("write", lambda *_args: self._update_investment_visibility())

        self._investments = backend_bridge.list_investments()
        self._investment_label = ctk.CTkLabel(
            self, text="Investimento afetado", text_color=theme.TEXT_PRIMARY)
        # "Nenhum" sempre presente — investimento vinculado é opcional (ver ADR-0022): o
        # lançamento fica com categoria Investimento/Passiva "genérica", sem mexer no valor de
        # nenhum Investment, e pode ser rotulado depois só editando e trocando esse seletor.
        investment_names = [_NO_INVESTMENT_LABEL] + [inv.name for inv in self._investments]
        initial_investment = next(
            (inv.name for inv in self._investments
             if is_edit and inv.id == transaction.investment_id),
            _NO_INVESTMENT_LABEL)
        self._investment_var = ctk.StringVar(value=initial_investment)
        self._investment_menu = ctk.CTkOptionMenu(
            self, values=investment_names, variable=self._investment_var,
            fg_color=theme.BG_SURFACE, button_color=theme.INDIGO)

        self._error_label = ctk.CTkLabel(self, text="", text_color=theme.ACCENT_EXPENSE)

        self._status_switch = ctk.CTkSwitch(
            self, text="Já foi pago/recebido", text_color=theme.TEXT_PRIMARY,
            progress_color=theme.ACCENT_HIGHLIGHT,
        )
        initial_paid = (not is_edit) or str(transaction.status) == "TransactionStatus.PAID"
        if initial_paid:
            self._status_switch.select()  # padrão em criação: já efetuado
        self._status_switch.pack(anchor="w", padx=20, pady=(16, 0))

        self._error_label.pack(anchor="w", padx=20, pady=(10, 0))

        ctk.CTkButton(
            self, text="Salvar alterações" if is_edit else "Adicionar",
            fg_color=theme.ACCENT_EXPENSE, command=self._submit,
        ).pack(fill="x", padx=20, pady=(20, 20))

        self._update_investment_visibility()

    def _category_options(self) -> list:
        is_expense = self._type_var.get() == "Despesa"
        return (backend_bridge.expense_category_names() if is_expense
                else backend_bridge.income_category_names())

    def _update_category_options(self) -> None:
        options = self._category_options()
        self._category_picker.set_values(options)
        if self._category_var.get() not in options:
            self._category_var.set(options[0])
        self._update_investment_visibility()

    def _update_investment_visibility(self) -> None:
        if self._category_var.get() in backend_bridge.investment_linked_categories():
            self._investment_label.pack(anchor="w", padx=20, pady=(16, 4), before=self._error_label)
            self._investment_menu.pack(fill="x", padx=20, before=self._error_label)
            self.geometry(_HEIGHT_WITH_INVESTMENT)
        else:
            self._investment_label.pack_forget()
            self._investment_menu.pack_forget()
            self.geometry(_HEIGHT_BASE)

    def _submit(self) -> None:
        description = self._description_entry.get().strip()
        if not description:
            self._error_label.configure(text="Informe uma descrição.")
            return

        try:
            date = datetime.datetime.strptime(self._date_entry.get().strip(), _DATE_FORMAT).date()
        except ValueError:
            self._error_label.configure(text="Data inválida. Use DD/MM/AAAA.")
            return

        try:
            value_cents = round(float(self._value_entry.get().strip().replace(",", ".") or "0") * 100)
        except ValueError:
            self._error_label.configure(text="Valor inválido.")
            return
        if value_cents == 0:
            self._error_label.configure(text="Informe um valor diferente de zero.")
            return

        category_name = self._category_var.get()
        investment_id = ""
        if (category_name in backend_bridge.investment_linked_categories()
                and self._investment_var.get() != _NO_INVESTMENT_LABEL):
            selected = next(
                (inv for inv in self._investments if inv.name == self._investment_var.get()), None)
            if selected is None:
                self._error_label.configure(text="Selecione um investimento.")
                return
            investment_id = selected.id

        enums = backend_bridge.transaction_enums()
        is_expense = self._type_var.get() == "Despesa"
        transaction_type = enums["expense"] if is_expense else enums["income"]
        # Valor sempre digitado como magnitude positiva; o sinal vem do tipo (despesa = negativo).
        signed_cents = -abs(value_cents) if is_expense else abs(value_cents)
        status = enums["paid"] if self._status_switch.get() == 1 else enums["pending"]
        date_iso = date.isoformat()

        if self._transaction is not None:
            result = backend_bridge.update_transaction(
                self._transaction.id, description, category_name, transaction_type, signed_cents,
                "BRL", status, date_iso, investment_id)
        else:
            result = backend_bridge.create_transaction(
                description, category_name, transaction_type, signed_cents, "BRL", status,
                date_iso, investment_id)
        # Passa o resultado pro chamador poder registrar um comando de desfazer/refazer — ver
        # UI/iterador_ui/transaction_commands.py.
        self._on_created(result)
        self.destroy()
