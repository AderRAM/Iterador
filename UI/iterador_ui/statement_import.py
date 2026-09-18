"""Leitor de extratos bancários do Nubank (CSV) — ver
Guide/decisions/0024-nubank-statement-import.md.

Só lógica de leitura/mapeamento aqui — nenhuma chamada a `backend_bridge` ou escrita no banco.
Quem decide o que fazer com o resultado (deduplicar, mostrar pra revisão, criar as transações) é
`StatementReviewDialog` (UI/iterador_ui/widgets/statement_review_dialog.py).

O Nubank exporta pelo menos 2 formatos de CSV diferentes (confirmados com arquivos reais do
usuário — detalhe completo no ADR-0024):

- **Extrato de conta/PIX**: cabeçalho "Data,Valor,Identificador,Descrição". Data em
  "dd/mm/aaaa"; Valor já assinado igual à convenção do Iterador (positivo = entrada, negativo =
  saída).
- **Fatura de cartão de crédito**: cabeçalho "date,title,amount" (em inglês, só 3 colunas — sem
  categoria). Data em "aaaa-mm-dd"; amount vem como texto com vírgula decimal (ex. "6,00"), às
  vezes com espaço depois do sinal (ex. "- 454,36"), e o sinal é **oposto** ao do Iterador:
  positivo = compra (despesa), negativo = pagamento/crédito na fatura (receita).

Diferente do importador da planilha (ADR-0023), o CSV do Nubank não tem nenhuma coluna
equivalente a "Prioridade" pra mapear categoria — por isso `ParsedStatementRow` não tem
`category_name`: quem escolhe a categoria é o usuário, na tela de revisão.
"""

import csv
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ParsedStatementRow:
    occurred_at: str  # "YYYY-MM-DD"
    description: str
    amount_cents: int  # sinal já na convenção do Iterador (negativo = despesa)
    is_income: bool


@dataclass
class StatementImportResult:
    rows: list[ParsedStatementRow] = field(default_factory=list)
    format_name: str = ""
    errors: list[str] = field(default_factory=list)


def _normalize_header(fieldnames: list[str] | None) -> tuple[str, ...]:
    if not fieldnames:
        return ()
    return tuple(name.strip().lower() for name in fieldnames)


_ACCOUNT_STATEMENT_HEADER = ("data", "valor", "identificador", "descrição")
_CREDIT_CARD_HEADER = ("date", "title", "amount")


def _parse_account_statement(reader: csv.DictReader) -> list[ParsedStatementRow]:
    rows = []
    for record in reader:
        date = datetime.strptime(record["Data"].strip(), "%d/%m/%Y").date()
        amount_cents = round(float(record["Valor"].strip()) * 100)
        rows.append(ParsedStatementRow(
            occurred_at=date.isoformat(),
            description=record["Descrição"].strip(),
            amount_cents=amount_cents,
            is_income=amount_cents >= 0,
        ))
    return rows


def _parse_credit_card_statement(reader: csv.DictReader) -> list[ParsedStatementRow]:
    rows = []
    for record in reader:
        date = datetime.strptime(record["date"].strip(), "%Y-%m-%d").date()
        raw_amount = record["amount"].strip().replace(" ", "").replace(",", ".")
        # Sinal invertido: positivo na fatura é compra (despesa no Iterador); negativo é
        # pagamento/crédito (receita) — ver docstring do módulo.
        amount_cents = -round(float(raw_amount) * 100)
        rows.append(ParsedStatementRow(
            occurred_at=date.isoformat(),
            description=record["title"].strip(),
            amount_cents=amount_cents,
            is_income=amount_cents >= 0,
        ))
    return rows


def parse_statement(path: str) -> StatementImportResult:
    result = StatementImportResult()
    try:
        with open(path, newline="", encoding="utf-8-sig") as csv_file:
            reader = csv.DictReader(csv_file)
            header = _normalize_header(reader.fieldnames)

            if header == _ACCOUNT_STATEMENT_HEADER:
                result.format_name = "Extrato de conta/PIX"
                result.rows = _parse_account_statement(reader)
            elif header == _CREDIT_CARD_HEADER:
                result.format_name = "Fatura de cartão de crédito"
                result.rows = _parse_credit_card_statement(reader)
            else:
                result.errors.append(
                    "Cabeçalho do CSV não reconhecido — esperado o extrato de conta/PIX "
                    '("Data,Valor,Identificador,Descrição") ou a fatura de cartão '
                    f'("date,title,amount"). Encontrado: {", ".join(reader.fieldnames or [])}')
    except (OSError, ValueError, KeyError) as exc:
        result.errors.append(f"Falha ao ler o arquivo: {exc}")

    return result
