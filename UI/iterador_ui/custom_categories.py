"""Persistência e CRUD de categorias personalizadas — ver
Guide/decisions/0028-custom-categories.md.

Fica em `~/.iterador/custom_categories.json` (arquivo próprio, nunca `~/.iterador/iterador.db` —
mesmo padrão de `preferences.py`/`color_profiles.py`). As 5 categorias fixas (Essencial/Lazer/
Investimento/Ativa/Passiva) não vivem aqui — continuam hardcoded em `backend_bridge.py`, iguais
em qualquer instalação e não removíveis.

O backend C++ não precisa saber nada disso: `CategoryRepository::findOrCreateByName` já
acha-ou-cria uma linha na tabela `categories` pra qualquer nome passado por `create_transaction`/
`update_transaction` (ver ADR-0028) — uma categoria personalizada só vira uma linha de verdade no
banco na primeira vez que um lançamento a usa, exatamente como já acontece com as 5 fixas. Este
módulo só guarda a "declaração": que nome existe como opção, se é Despesa ou Receita, se se
comporta como um tipo de investimento (mostra o seletor de investimento e ajusta o valor dele,
como Investimento/Passiva) ou como um gasto/receita comum (só categoriza, como Essencial/Lazer/
Ativa), e a cor dela (`theme.category_color()` usa essa cor pra qualquer categoria personalizada,
ver ADR-0030) — quem decide o padrão aleatório é a UI que chama `add_custom_category`, não este
módulo, pra não precisar importar `theme.py` aqui (mesmo princípio de independência de
`color_profiles.py`).
"""

import json
from pathlib import Path

_CATEGORIES_PATH = Path.home() / ".iterador" / "custom_categories.json"

TYPES = ("Despesa", "Receita")


class CategoryError(ValueError):
    """Erro de uso da API de categorias (nome duplicado/vazio, tipo inválido, etc.) — mensagem
    já pronta pra mostrar ao usuário num diálogo."""


def _load() -> list[dict]:
    try:
        data = json.loads(_CATEGORIES_PATH.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    except (OSError, ValueError):
        pass
    return []


def _save(categories: list[dict]) -> None:
    _CATEGORIES_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CATEGORIES_PATH.write_text(
        json.dumps(categories, indent=2, ensure_ascii=False), encoding="utf-8")


def list_custom_categories() -> list[dict]:
    """[{"name": str, "type": "Despesa"|"Receita", "investment_linked": bool, "color": str}, ...]"""
    return _load()


def add_custom_category(name: str, type_: str, investment_linked: bool,
                         fixed_names: set[str], color: str) -> None:
    """`fixed_names`: nomes já reservados pelas categorias fixas (case-insensitive) — quem chama
    (`backend_bridge.py`) sabe quais são; este módulo não depende de `backend_bridge` pra evitar
    import circular. `color`: hex "#RRGGBB" — quem chama decide o padrão (ex. aleatório), este
    módulo só guarda o que vier."""
    name = name.strip()
    if not name:
        raise CategoryError("Informe um nome pra categoria.")
    if type_ not in TYPES:
        raise CategoryError(f'Tipo inválido: "{type_}".')
    existing_lower = {c["name"].lower() for c in _load()} | {n.lower() for n in fixed_names}
    if name.lower() in existing_lower:
        raise CategoryError(f'Já existe uma categoria chamada "{name}".')
    categories = _load()
    categories.append({
        "name": name, "type": type_, "investment_linked": investment_linked, "color": color})
    _save(categories)


def update_custom_category_color(name: str, color: str) -> None:
    """Só troca a cor de uma categoria já existente — nome/tipo/comportamento intactos (mudar
    esses depois de já ter lançamentos usando a categoria complicaria a lógica de Despesa/Receita
    sem necessidade; a cor é só rótulo visual, sem esse problema). Sem erro se não existir."""
    categories = _load()
    for category in categories:
        if category["name"] == name:
            category["color"] = color
            break
    _save(categories)


def remove_custom_category(name: str) -> None:
    """Só tira `name` da lista de opções — nunca mexe em lançamentos já gravados no banco (mesmo
    princípio da categoria órfã "Necessário", ver Guide/checklist.md). Sem erro se não existir."""
    categories = [c for c in _load() if c["name"] != name]
    _save(categories)
