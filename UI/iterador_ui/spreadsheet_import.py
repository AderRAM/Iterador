"""Importador da planilha Excel de controle financeiro que o usuário já usava antes do
Iterador. Ver Guide/spreadsheet-reference.md (formato real, levantado lendo o arquivo de
verdade) e Guide/decisions/0022-generic-unlabeled-investment-link.md.

Só lógica de leitura/mapeamento aqui — nenhuma chamada a `backend_bridge` ou escrita no banco.
Quem decide o que fazer com o resultado (criar as transações, deduplicar, mostrar resumo) é
`SettingsView` (UI/iterador_ui/views/settings_view.py).

Além disso, o módulo exporta a função `detect_conflicts()` que pode ser usada pela UI para
identificar transações já existentes na base de dados que têm mesma data+descrição mas valor
diferente — permitindo ao usuário decidir qual valor manter e evitando redundância silenciosa.

Formato observado (3 eras, planilha de ~3 anos de uso real):

- Cada aba é um período, nomeada "dd-mm-aa" (só mês/ano são confiáveis no nome).
- Uma aba só conta como importável se tiver colunas de cabeçalho "$$$", "Prioridade" e
  "Efetuado" na primeira linha — sem isso (abas bem antigas, só Descrição+Valor) não dá pra
  mapear categoria/status com confiança; a aba entra em `skipped_sheets`.
- A coluna de Descrição é sempre a primeira coluna à esquerda de "$$$" que tem texto de verdade
  nas linhas de dado (às vezes cola no "$$$", às vezes tem uma coluna vazia de separação no
  meio — o formato mudou entre eras).
- Nem toda aba tem uma coluna de Data por linha (algumas eras só têm uma data solta no
  cabeçalho) — quando não tem, todas as linhas da aba caem no dia 1 do mês/ano da aba (aviso
  registrado em `warnings`, não trava a importação).
- Quando a coluna de Data existe mas guarda só o dia do mês (número, não `datetime`), o mês/ano
  vêm do nome da aba.
- Painel de resumo (colunas depois de Efetuado) e a listinha "Comida" são sempre ignorados — só
  as colunas do livro-caixa em si importam.
"""

import re
from dataclasses import dataclass, field
from datetime import date

import openpyxl

_SHEET_NAME_RE = re.compile(r"^(\d{2})-(\d{2})-(\d{2})$")

_HEADER_VALOR = "$$$"
_HEADER_PRIORIDADE = "prioridade"
_HEADER_EFETUADO = "efetuado"

# Prioridade → nome de categoria do Iterador, por sinal do valor (ver ADR-0012/0014).
_EXPENSE_CATEGORY_BY_PRIORITY = {1: "Essencial", 2: "Lazer", 3: "Investimento"}
_INCOME_CATEGORY_BY_PRIORITY = {3: "Passiva"}
_DEFAULT_EXPENSE_CATEGORY = "Essencial"
_DEFAULT_INCOME_CATEGORY = "Ativa"

_MAX_HEADER_SCAN_COL = 20  # nunca precisou passar disso nas abas reais (painel bugado inclusive)


@dataclass
class ParsedTransaction:
    occurred_at: str  # "YYYY-MM-DD"
    description: str
    amount_cents: int
    category_name: str
    is_income: bool
    is_paid: bool
    sheet_name: str


@dataclass
class ImportResult:
    transactions: list[ParsedTransaction] = field(default_factory=list)
    skipped_sheets: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _normalize(value) -> str:
    return str(value).strip().lower() if value is not None else ""


def _sheet_year_month(sheet_name: str) -> tuple[int, int] | None:
    match = _SHEET_NAME_RE.match(sheet_name.strip())
    if not match:
        return None
    _day, month, year = match.groups()
    return 2000 + int(year), int(month)


def _find_header_columns(ws) -> dict[str, int] | None:
    """Acha, na primeira linha, as colunas de "$$$"/"Prioridade"/"Efetuado". None se faltar
    alguma — sinal de que a aba não tem o formato importável (era mais antiga da planilha)."""
    header_row = next(ws.iter_rows(min_row=1, max_row=1, max_col=_MAX_HEADER_SCAN_COL), ())
    found: dict[str, int] = {}
    for cell in header_row:
        normalized = _normalize(cell.value)
        if normalized == _HEADER_VALOR and "valor" not in found:
            found["valor"] = cell.column
        elif normalized == _HEADER_PRIORIDADE and "prioridade" not in found:
            found["prioridade"] = cell.column
        elif normalized == _HEADER_EFETUADO and "efetuado" not in found:
            found["efetuado"] = cell.column
    if {"valor", "prioridade", "efetuado"} <= found.keys():
        return found
    return None


def _find_description_column(ws, valor_col: int) -> int | None:
    """A coluna de descrição é a mais próxima à esquerda de `valor_col` que tem texto de
    verdade numa linha de dado — cobre tanto o layout com coluna vazia separadora quanto sem."""
    for candidate in (valor_col - 1, valor_col - 2):
        if candidate < 1:
            continue
        for row in ws.iter_rows(min_row=2, max_row=min(ws.max_row, 30), min_col=candidate,
                                 max_col=candidate):
            value = row[0].value
            if isinstance(value, str) and value.strip():
                return candidate
    return None


def _find_date_column(ws, description_col: int) -> int | None:
    """Coluna de Data por linha, se existir — procurada à esquerda da Descrição (pode não
    existir; nesse caso quem chama cai no 1º dia do mês da aba)."""
    for candidate in range(description_col - 1, 0, -1):
        for row in ws.iter_rows(min_row=2, max_row=min(ws.max_row, 60), min_col=candidate,
                                 max_col=candidate):
            if isinstance(row[0].value, (int, float)) and row[0].value:
                return candidate
            if hasattr(row[0].value, "year"):  # datetime
                return candidate
    return None


def _resolve_date(cell_value, year_month: tuple[int, int] | None) -> tuple[date, bool]:
    """Retorna (data, teve_aproximacao). Se `cell_value` já é uma data completa, usa direto —
    do contrário (dia solto ou nada) monta a partir do mês/ano da aba."""
    if hasattr(cell_value, "year"):
        return date(cell_value.year, cell_value.month, cell_value.day), False

    year, month = year_month or (date.today().year, date.today().month)
    if isinstance(cell_value, (int, float)) and cell_value:
        day = max(1, min(28, int(cell_value)))  # 28 evita estourar mês (dia solto é aproximação)
        return date(year, month, day), False

    return date(year, month, 1), True


def _category_for(priority: float | None, is_income: bool) -> str:
    priority_int = int(priority) if priority is not None else None
    table = _INCOME_CATEGORY_BY_PRIORITY if is_income else _EXPENSE_CATEGORY_BY_PRIORITY
    default = _DEFAULT_INCOME_CATEGORY if is_income else _DEFAULT_EXPENSE_CATEGORY
    return table.get(priority_int, default)


def parse_workbook(path: str) -> ImportResult:
    result = ImportResult()
    workbook = openpyxl.load_workbook(path, data_only=True)

    for sheet_name in workbook.sheetnames:
        ws = workbook[sheet_name]
        columns = _find_header_columns(ws)
        if columns is None:
            result.skipped_sheets.append(sheet_name)
            continue

        description_col = _find_description_column(ws, columns["valor"])
        if description_col is None:
            result.skipped_sheets.append(sheet_name)
            result.warnings.append(f'"{sheet_name}": coluna de descrição não identificada.')
            continue

        date_col = _find_date_column(ws, description_col)
        year_month = _sheet_year_month(sheet_name)
        if date_col is None:
            result.warnings.append(
                f'"{sheet_name}": sem coluna de data por linha — usando dia 1 do mês da aba.')

        last_known_date = None
        for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
            description_cell = row[description_col - 1].value
            valor_cell = row[columns["valor"] - 1].value
            has_value = isinstance(valor_cell, (int, float)) and valor_cell != 0
            has_description = isinstance(description_cell, str) and description_cell.strip()

            if not has_description and not has_value:
                continue  # linha vazia/padding — inclusive o painel de resumo, que não tem isso
            if not has_description:
                result.warnings.append(
                    f'"{sheet_name}": linha {row[0].row} tem valor ({valor_cell}) mas sem '
                    "descrição — ignorada (não dá pra criar um lançamento sem descrição).")
                continue
            if not has_value:
                continue  # descrição sem valor (ou valor 0) — nada a lançar

            if date_col is not None:
                raw_date = row[date_col - 1].value
                if raw_date not in (None, ""):
                    resolved, approximated = _resolve_date(raw_date, year_month)
                    last_known_date = resolved
                    if approximated:
                        result.warnings.append(
                            f'"{sheet_name}": linha {row[0].row} com data não reconhecida, '
                            f"usando {resolved.isoformat()}.")
                elif last_known_date is not None:
                    resolved = last_known_date  # dia repetido — planilha só marca no 1º da série
                else:
                    resolved, _ = _resolve_date(None, year_month)
                    last_known_date = resolved
            else:
                resolved, _ = _resolve_date(None, year_month)

            priority_cell = row[columns["prioridade"] - 1].value
            efetuado_cell = row[columns["efetuado"] - 1].value

            is_income = valor_cell >= 0
            category_name = _category_for(priority_cell, is_income)
            is_paid = bool(efetuado_cell)

            result.transactions.append(ParsedTransaction(
                occurred_at=resolved.isoformat(),
                description=description_cell.strip(),
                amount_cents=round(valor_cell * 100),
                category_name=category_name,
                is_income=is_income,
                is_paid=is_paid,
                sheet_name=sheet_name,
            ))


def detect_conflicts(parsed_transactions, existing_transactions):
    """Detect conflicts between parsed transactions and existing database entries.

    For each parsed transaction, checks if there's already a transaction in the database
    with the same occurred_at + description but different amount_cents.

    Returns a list of dicts with:
      - parsed: the ParsedTransaction
      - existing: the matching existing Transaction object (or None)
      - conflict: True if there's a value mismatch
      - key: (occurred_at, description) for reference
      - is_duplicate_value_match: True if same value already exists (no conflict, just duplicate)
    """
    conflicts = []
    existing_by_key = {}

    # Build lookup: (occurred_at, description_lower) -> list of existing transactions
    for t in existing_transactions:
        key = (t.occurred_at, t.description.lower())
        existing_by_key.setdefault(key, []).append(t)

    for parsed in parsed_transactions:
        key = (parsed.occurred_at, parsed.description.lower())
        matches = existing_by_key.get(key, [])

        if not matches:
            # No existing transaction with same data+description
            conflicts.append({
                'parsed': parsed,
                'existing': None,
                'conflict': False,
                'key': key,
            })
        else:
            # Find matches with different value
            value_matches = [t for t in matches if t.amount_cents == parsed.amount_cents]
            if value_matches:
                # Same value exists - no conflict, but it's a duplicate
                conflicts.append({
                    'parsed': parsed,
                    'existing': value_matches[0],
                    'conflict': False,
                    'key': key,
                    'is_duplicate_value_match': True,
                })
            else:
                # Different value(s) exist - this is a conflict
                # Show the existing values for the user to choose
                existing_values = {
                    t.amount_cents: {'description': t.description, 'category': t.category_name}
                    for t in matches
                }
                conflicts.append({
                    'parsed': parsed,
                    'existing': matches[0],
                    'conflict': True,
                    'key': key,
                    'existing_values': existing_values,
                })

    return conflicts

