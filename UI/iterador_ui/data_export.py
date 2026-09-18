"""Exporta os dados do Iterador (investimentos, lançamentos, metas de economia) para um único
arquivo `.zip` — um CSV por entidade, mais um `metadata.json` com quando/qual versão gerou o
export. Pensado tanto como cópia de segurança manual quanto pra levar os dados pra outra
máquina. Ver UI/iterador_ui/views/settings_view.py (quem chama isto) e
Guide/decisions/0022-generic-unlabeled-investment-link.md.

Só leitura do banco via `backend_bridge` — nunca grava nada.
"""

import csv
import io
import json
import zipfile
from datetime import datetime, timezone

from iterador_ui import backend_bridge
from iterador_ui.version import APP_VERSION


def _write_csv(rows: list[dict], fieldnames: list[str]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def export_to_zip(path: str) -> None:
    investments = backend_bridge.list_investments()
    transactions = backend_bridge.list_transactions()
    budgets = backend_bridge.list_budgets()

    investments_csv = _write_csv(
        [{
            "id": inv.id, "name": inv.name, "type": inv.type,
            "current_value_cents": inv.current_value.cents,
            "currency": inv.current_value.currency, "yield_rate": inv.yield_rate,
            "fees_rate": inv.fees_rate, "selic_percentage": inv.selic_percentage,
        } for inv in investments],
        ["id", "name", "type", "current_value_cents", "currency", "yield_rate", "fees_rate",
         "selic_percentage"])

    transactions_csv = _write_csv(
        [{
            "id": t.id, "description": t.description, "category_name": t.category_name,
            "type": str(t.type), "amount_cents": t.amount.cents, "currency": t.amount.currency,
            "status": str(t.status), "occurred_at": t.occurred_at,
            "investment_id": t.investment_id,
        } for t in transactions],
        ["id", "description", "category_name", "type", "amount_cents", "currency", "status",
         "occurred_at", "investment_id"])

    budgets_csv = _write_csv(
        [{
            "id": b.id, "name": b.name, "target_value_cents": b.target_value.cents,
            "currency": b.target_value.currency, "months": b.months,
            "investment_id": b.investment_id,
        } for b in budgets],
        ["id", "name", "target_value_cents", "currency", "months", "investment_id"])

    metadata = {
        "app_version": APP_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "counts": {
            "investments": len(investments),
            "transactions": len(transactions),
            "budgets": len(budgets),
        },
    }

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("metadata.json", json.dumps(metadata, indent=2, ensure_ascii=False))
        archive.writestr("investments.csv", investments_csv)
        archive.writestr("transactions.csv", transactions_csv)
        archive.writestr("budgets.csv", budgets_csv)
