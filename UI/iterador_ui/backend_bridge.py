"""Único ponto da UI que importa o módulo compilado iterador_core (ver Guide/functions.md).

Todo o resto de UI/ chama funções daqui, nunca `import iterador_core` diretamente — isso
mantém o caminho de build (UI/_build/) isolado num só lugar.
"""

import sys
from pathlib import Path

from iterador_ui import custom_categories

_BUILD_DIR = Path(__file__).resolve().parent.parent / "_build"
if str(_BUILD_DIR) not in sys.path:
    sys.path.insert(0, str(_BUILD_DIR))

try:
    import iterador_core
except ImportError as exc:  # pragma: no cover - mensagem de ajuda, não lógica de negócio
    raise ImportError(
        "Nao foi possivel importar iterador_core. Rode ./scripts/build_backend.sh "
        f"(ou build_backend.ps1) e confirme que existe um binario em {_BUILD_DIR}. "
        "Veja Guide/usage.md > Troubleshooting."
    ) from exc

_app: "iterador_core.Application | None" = None


def open_database(path: str) -> None:
    global _app
    _app = iterador_core.Application(path)


def _require_app() -> "iterador_core.Application":
    if _app is None:
        raise RuntimeError("backend_bridge.open_database() precisa ser chamado antes de usar a UI")
    return _app


def list_investments() -> list:
    return _require_app().list_investments()


def create_investment(name: str, type_: str, current_value_cents: int, currency: str,
                       yield_rate: float, fees_rate: float, selic_percentage: float):
    return _require_app().create_investment(
        name, type_, current_value_cents, currency, yield_rate, fees_rate, selic_percentage)


def update_investment(investment_id: str, name: str, type_: str, current_value_cents: int,
                       currency: str, yield_rate: float, fees_rate: float,
                       selic_percentage: float):
    return _require_app().update_investment(
        investment_id, name, type_, current_value_cents, currency, yield_rate, fees_rate,
        selic_percentage)


def delete_investment(investment_id: str) -> None:
    """Antes de apagar, o backend desvincula (não apaga) qualquer lançamento/orçamento que
    apontava pro investimento (investment_id vira "" = nenhum, mesmo estado de ADR-0022) —
    ver Application::deleteInvestment."""
    _require_app().delete_investment(investment_id)


def list_transactions() -> list:
    return _require_app().list_transactions()


# Categorias fixas (não mais texto livre por descrição — ver ADR-0012/0014). Só valem para
# Despesa; Receita usa outro conjunto (Ativa/Passiva). "Investimento" e "Passiva" são especiais:
# a UI mostra um segundo seletor com os investimentos existentes quando qualquer uma é
# escolhida — Investimento = aporte, Passiva = resgate/rendimento (mesmo investimento, sinais
# opostos, ver Application.adjustInvestmentValue). Além dessas 5, o usuário pode criar categorias
# personalizadas em Configurações (`custom_categories.py`, ver ADR-0028) — por isso as três
# funções abaixo, em vez de listas fixas: mesclam as fixas com as personalizadas toda vez que são
# chamadas (nunca guardam cache, pra uma categoria criada aparecer sem precisar reiniciar o app).
_FIXED_EXPENSE_CATEGORY_NAMES = ["Essencial", "Lazer", "Investimento"]
_FIXED_INCOME_CATEGORY_NAMES = ["Ativa", "Passiva"]
_FIXED_INVESTMENT_LINKED_CATEGORIES = {"Investimento", "Passiva"}
_FIXED_CATEGORY_NAMES = set(_FIXED_EXPENSE_CATEGORY_NAMES) | set(_FIXED_INCOME_CATEGORY_NAMES)


def expense_category_names() -> list[str]:
    custom = [c["name"] for c in custom_categories.list_custom_categories()
              if c["type"] == "Despesa"]
    return _FIXED_EXPENSE_CATEGORY_NAMES + custom


def income_category_names() -> list[str]:
    custom = [c["name"] for c in custom_categories.list_custom_categories()
              if c["type"] == "Receita"]
    return _FIXED_INCOME_CATEGORY_NAMES + custom


def investment_linked_categories() -> set[str]:
    custom = {c["name"] for c in custom_categories.list_custom_categories()
              if c["investment_linked"]}
    return _FIXED_INVESTMENT_LINKED_CATEGORIES | custom


def fixed_category_names() -> set[str]:
    """Nomes reservados pelas 5 categorias fixas — usado por `custom_categories.add_custom_category`
    pra impedir uma categoria personalizada de colidir com uma fixa."""
    return _FIXED_CATEGORY_NAMES


def create_transaction(description: str, category_name: str, type_, amount_cents: int,
                        currency: str, status, occurred_at_date: str, investment_id: str = ""):
    return _require_app().create_transaction(
        description, category_name, type_, amount_cents, currency, status, occurred_at_date,
        investment_id)


def update_transaction(transaction_id: str, description: str, category_name: str, type_,
                        amount_cents: int, currency: str, status, occurred_at_date: str,
                        investment_id: str = ""):
    return _require_app().update_transaction(
        transaction_id, description, category_name, type_, amount_cents, currency, status,
        occurred_at_date, investment_id)


def set_transaction_status(transaction_id: str, status):
    return _require_app().set_transaction_status(transaction_id, status)


def update_transaction_sort_order(transaction_id: str, sort_order: float):
    """Ordem manual de exibição (arrastar na lista, ver ADR-0033). `sort_order` é calculado na
    UI (indexação fracionária entre os vizinhos do arrasto), aqui só repassa pro backend."""
    return _require_app().update_transaction_sort_order(transaction_id, sort_order)


def update_transaction_recurring(transaction_id: str, is_recurring: bool):
    """Fixa/desfixa (ícone de pin na lista, ver ADR-0034) — repassa pro backend; a decisão de
    clonar pro mês novo é da UI (`DashboardView`), não daqui."""
    return _require_app().update_transaction_recurring(transaction_id, is_recurring)


def delete_transaction(transaction_id: str) -> None:
    _require_app().delete_transaction(transaction_id)


def list_budgets() -> list:
    return _require_app().list_budgets()


def create_budget(name: str, target_value_cents: int, currency: str, months: int,
                   investment_id: str = ""):
    return _require_app().create_budget(name, target_value_cents, currency, months, investment_id)


def update_budget(budget_id: str, name: str, target_value_cents: int, currency: str, months: int,
                   investment_id: str = ""):
    return _require_app().update_budget(
        budget_id, name, target_value_cents, currency, months, investment_id)


def delete_budget(budget_id: str) -> None:
    _require_app().delete_budget(budget_id)


def transaction_enums() -> dict:
    """Valores de TransactionType/TransactionStatus, para a UI não importar iterador_core
    diretamente (ver módulo docstring)."""
    return {
        "income": iterador_core.TransactionType.INCOME,
        "expense": iterador_core.TransactionType.EXPENSE,
        "paid": iterador_core.TransactionStatus.PAID,
        "pending": iterador_core.TransactionStatus.PENDING,
    }


def sync_status() -> dict:
    status = _require_app().sync_status()
    return {
        "running": status.running,
        "known_peers": status.known_peers,
        "last_sync_at": status.last_sync_at,
        "last_error": status.last_error,
    }
