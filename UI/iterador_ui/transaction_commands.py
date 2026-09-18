"""Comandos de desfazer/refazer para a lista de lançamentos. Ver undo_stack.py.

Cada comando guarda os campos necessários para reverter/reaplicar uma ação via
backend_bridge — não mexe na UI diretamente (quem chama refresh() é o DashboardView).
Exceção: `RemoveMonthCommand` também repõe o bookkeeping do `MonthSelector` (mês
adicionado manualmente / mês selecionado), porque isso não vive no backend — ver
Guide/decisions/0019-remove-month-with-undo.md.
"""

from iterador_ui import backend_bridge


def _fields(t) -> dict:
    return {
        "description": t.description,
        "category_name": t.category_name,
        "type_": t.type,
        "amount_cents": t.amount.cents,
        "currency": t.amount.currency,
        "status": t.status,
        "occurred_at_date": t.occurred_at,
        "investment_id": t.investment_id,
    }


class CreateTransactionCommand:
    def __init__(self, created_transaction):
        self._fields = _fields(created_transaction)
        self.id = created_transaction.id

    def undo(self) -> None:
        backend_bridge.delete_transaction(self.id)

    def redo(self) -> None:
        self.id = backend_bridge.create_transaction(**self._fields).id


class DeleteTransactionCommand:
    def __init__(self, deleted_transaction):
        self._fields = _fields(deleted_transaction)
        self.id = deleted_transaction.id

    def undo(self) -> None:
        self.id = backend_bridge.create_transaction(**self._fields).id

    def redo(self) -> None:
        backend_bridge.delete_transaction(self.id)


class UpdateTransactionCommand:
    def __init__(self, before_transaction, after_transaction):
        self.id = after_transaction.id
        self._before = _fields(before_transaction)
        self._after = _fields(after_transaction)

    def undo(self) -> None:
        backend_bridge.update_transaction(self.id, **self._before)

    def redo(self) -> None:
        backend_bridge.update_transaction(self.id, **self._after)


class ToggleStatusCommand:
    def __init__(self, transaction_id, old_status, new_status):
        self.id = transaction_id
        self._old = old_status
        self._new = new_status

    def undo(self) -> None:
        backend_bridge.set_transaction_status(self.id, self._old)

    def redo(self) -> None:
        backend_bridge.set_transaction_status(self.id, self._new)


class ReorderTransactionCommand:
    """Um arrasto na lista (ver ADR-0033) — guarda o `sort_order` antigo/novo, undo/redo só
    reatribuem o valor, mesmo padrão de ToggleStatusCommand."""

    def __init__(self, transaction_id, old_sort_order, new_sort_order):
        self.id = transaction_id
        self._old = old_sort_order
        self._new = new_sort_order

    def undo(self) -> None:
        backend_bridge.update_transaction_sort_order(self.id, self._old)

    def redo(self) -> None:
        backend_bridge.update_transaction_sort_order(self.id, self._new)


class ResetTransactionOrderCommand:
    """Reseta a ordem manual (arrastar, ver ADR-0033) de várias transações de uma vez pra ordem
    padrão (por data) — um único item no desfazer, mesmo padrão de RemoveMonthCommand (ADR-0019).
    """

    def __init__(self, entries: list[tuple[str, float, float]]):
        # entries: [(transaction_id, sort_order_antigo, sort_order_novo), ...]
        self._entries = entries

    def undo(self) -> None:
        for transaction_id, old_sort_order, _new_sort_order in self._entries:
            backend_bridge.update_transaction_sort_order(transaction_id, old_sort_order)

    def redo(self) -> None:
        for transaction_id, _old_sort_order, new_sort_order in self._entries:
            backend_bridge.update_transaction_sort_order(transaction_id, new_sort_order)


class TogglePinCommand:
    """Fixar/desfixar (ícone de pin, ver ADR-0034) — mesmo padrão de ToggleStatusCommand."""

    def __init__(self, transaction_id, was_recurring: bool):
        self.id = transaction_id
        self._old = was_recurring
        self._new = not was_recurring

    def undo(self) -> None:
        backend_bridge.update_transaction_recurring(self.id, self._old)

    def redo(self) -> None:
        backend_bridge.update_transaction_recurring(self.id, self._new)


class AddMonthCommand:
    """Adicionar um mês novo ("+ Mês") clonando as transações fixadas pra dentro dele (ver
    ADR-0034) — um único item no desfazer cobre a adição do mês E das transações clonadas
    juntas, mesmo princípio de RemoveMonthCommand (ADR-0019); as duas são inversas uma da outra.
    Só é empilhado quando existe pelo menos uma transação fixada pra clonar — sem isso, "+ Mês"
    continua sem nenhum item no desfazer, como sempre foi.
    """

    def __init__(self, month_str, created_entries, previous_month, month_selector):
        self._month_str = month_str
        self._entries = created_entries  # [{"fields": {...}, "id": ...}, ...]
        self._previous_month = previous_month
        self._month_selector = month_selector

    def undo(self) -> None:
        for entry in self._entries:
            backend_bridge.delete_transaction(entry["id"])
        self._month_selector.remove_month(self._month_str)
        self._month_selector.force_select(self._previous_month)

    def redo(self) -> None:
        for entry in self._entries:
            entry["id"] = backend_bridge.create_transaction(**entry["fields"]).id
        self._month_selector.add_extra_month(self._month_str)
        self._month_selector.force_select(self._month_str)


class RemoveMonthCommand:
    """Remove todas as transações de um mês de uma vez (ou só o mês vazio, se não tinha
    nenhuma) — um único "Desfazer" restaura tudo de novo, em vez de precisar desfazer
    lançamento por lançamento. Ver ADR-0019.
    """

    def __init__(self, month_transactions, month_str, was_extra_month, fallback_month,
                 month_selector):
        self._entries = [{"fields": _fields(t), "id": t.id} for t in month_transactions]
        self._month_str = month_str
        self._was_extra_month = was_extra_month
        self._fallback_month = fallback_month
        self._month_selector = month_selector

    def undo(self) -> None:
        for entry in self._entries:
            entry["id"] = backend_bridge.create_transaction(**entry["fields"]).id
        if self._was_extra_month:
            self._month_selector.add_extra_month(self._month_str)
        self._month_selector.force_select(self._month_str)

    def redo(self) -> None:
        for entry in self._entries:
            backend_bridge.delete_transaction(entry["id"])
        self._month_selector.remove_month(self._month_str)
        self._month_selector.force_select(self._fallback_month)
