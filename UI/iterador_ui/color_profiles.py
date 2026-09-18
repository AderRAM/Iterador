"""Persistência e CRUD dos perfis de cor — ver Guide/decisions/0025-color-profile-management.md.

Fica em `~/.iterador/color_profiles.json` (arquivo próprio, nunca `~/.iterador/iterador.db` —
mesmo padrão de `preferences.py`).

Dois "modos" de perfil coexistem no mesmo arquivo:

- `"detailed"` — guarda os ~30 papéis de cor completos (mesmo formato que
  `theme._default_palette()` sempre devolveu). Só o perfil `Prizmo_V1` (o visual de hoje,
  preservado exatamente como estava antes deste sistema existir) usa esse modo nesta v1 — não
  editável por aqui, só renomeável/removível.
- `"simple"` — guarda só 4 campos (`static_text`, `primary`, `secondary`, `tertiary`, cada um uma
  tupla/lista `[claro, escuro]`) que `theme._expand_simple_profile()` expande pro formato
  completo na hora de aplicar. É o que `create_profile()`/`update_profile()` sempre criam —
  perfil novo simplifica fundo/frame/borda/texto estático em vez de ~30 campos independentes.

Cores de marca, valores monetários, cor por categoria e status Pago/A pagar **não fazem parte**
de nenhum perfil — ficam fixas (vêm de `theme._fixed_roles()`), iguais em qualquer perfil.
"""

import json
from pathlib import Path

_PROFILES_PATH = Path.home() / ".iterador" / "color_profiles.json"

DEFAULT_PROFILE_NAME = "Prizmo_V1"
ROZE_QUARTZ_PROFILE_NAME = "Roze Quartz"

SIMPLE_FIELDS = ("static_text", "primary", "secondary", "tertiary")


class ProfileError(ValueError):
    """Erro de uso da API de perfis (nome duplicado, perfil inexistente, etc.) — mensagem já
    pronta pra mostrar ao usuário num diálogo."""


def _seed_detailed_profile() -> dict:
    from iterador_ui import theme  # import tardio: evita ciclo (theme importa este módulo)
    profile = theme.snapshot_default_palette()
    profile["mode"] = "detailed"
    return profile


def _seed_roze_quartz_profile() -> dict:
    """Perfil "Roze Quartz" (pedido do usuário: tema mais feminino, estilo a Rose Quartz das
    Crystal Gems) — rosa quartzo/rose gold em vez de laranja/roxo, feito à mão (não deriva de
    `theme._fixed_roles()`, ver ADR-0041). `mode: "detailed"` como `Prizmo_V1` — dá controle
    total sobre TODOS os papéis (incl. os normalmente "fixos" como cor de despesa/receita), não
    só os 4 campos de um perfil "simple"; é a única forma de um perfil realmente parecer outro
    tema, não só trocar o fundo."""
    return {
        "mode": "detailed",
        # "Fixos" nos outros perfis, mas cada perfil "detailed" pode sobrescrever — ver
        # `theme.apply_profile()` (modo "detailed" usa o dict inteiro salvo, sem recair em
        # `_fixed_roles()`).
        "BRICK_EMBER": "#D46A85",       # rosa quartzo — despesa
        "INDIGO": "#8B5D7B",            # ameixa/malva — receita
        "CARBON_BLACK": "#2B1B22",      # preto ameixa (quente, não neutro)
        "DEEP_SAFFRON": "#E8A87C",      # pêssego suave — status "a pagar"
        "SUNFLOWER_GOLD": "#B76E79",    # rose gold — destaque
        "ELECTRIC_BLUE": "#D88C9A",     # rosa empoeirado — borda de destaque
        "TEXT_ON_BLACK": "#F5E6E8",
        "HEADING_TEXT": "#2B1B22",
        "ACCENT_EXPENSE": "#D46A85",
        "ACCENT_INCOME": "#8B5D7B",
        "ACCENT_HIGHLIGHT": "#B76E79",
        # Números da coluna Valor/Total do mês — 20% mais escuros que o pastel original de cada
        # um, senão ficam claros demais pra ler contra fundo claro. Usados também na fatia do
        # gráfico de consumo e no fundo do badge "Pago" (que tem texto preto fixo em cima —
        # continuam cor única nos dois temas de propósito, ver `VALUE_INCOME_TEXT` abaixo).
        "VALUE_INCOME": "#86AA95",      # verde-sálvia
        "VALUE_EXPENSE": "#BA4A5E",     # vermelho-rosado
        # Par claro/escuro só pro NÚMERO em si (coluna Valor, "Fim do mês", "Saldo atual",
        # cards "Receitas/Despesas do mês") — o `VALUE_INCOME` acima ainda ficava claro demais
        # pra ler como texto contra o fundo claro deste perfil. Verde escuro de verdade no claro
        # (mesmo matiz do sálvia, só bem mais escuro/saturado); no escuro volta pro sálvia
        # pastel original (`#A8D5BA`), que já tinha ótimo contraste lá.
        "VALUE_INCOME_TEXT": ("#255638", "#A8D5BA"),
        "NAV_INDICATOR_ACTIVE": "#D46A85",
        "THEME_SWITCH_DARK_COLOR": "#B76E79",
        "THEME_SWITCH_DARK_HOVER": "#9A5A63",
        "THEME_SWITCH_LIGHT_COLOR": "#C9A8AE",
        "THEME_SWITCH_LIGHT_HOVER": "#B08D93",
        # Estruturais — claro/escuro.
        "BG_APP": ("#FAF0F2", "#2B1B22"),
        "BG_SURFACE": ("#FFF5F7", "#3D2530"),
        "BG_PANEL_BLUE": ("#F5DEE3", "#34212A"),
        "TEXT_PRIMARY": ("#2B1B22", "#F5E6E8"),
        "BORDER_NEUTRAL": ("#D9AEB7", "#F5E6E8"),
        "BORDER_ACCENT": "#D88C9A",
        "STATUS_BADGE_BORDER": ("#2B1B22", "#F5E6E8"),
        "ROW_SEPARATOR": "#A8D5BA",
        # Cor de Investimento/Passiva (ver Guide/decisions/0047-per-profile-investment-category-color.md
        # e Guide/decisions/0048-roze-quartz-investment-category-color.md) — campo próprio desde
        # a ADR-0047. Era o mesmo rosa de Essencial/Despesa (`#C2185B`, perto demais de
        # `VALUE_EXPENSE`/`BRICK_EMBER` acima) até a ADR-0048, que trocou pra uma ametista/lilás
        # (roxo de verdade, não rosa) — mesma ideia do `Prizmo_V1` (ADR-0043), mas num tom mais
        # suave pra combinar com o resto da paleta pastel deste perfil.
        "INVESTMENT_CATEGORY_COLOR": "#9B43B1",
        "INVESTMENT_CATEGORY_LABEL_LIGHT_TEXT": "#9B43B1",
        "INVESTMENT_CATEGORY_LABEL_DARK_TEXT": "#DAB5E3",
        # Sem contorno preto (ver ADR-0042) em NENHUMA categoria neste perfil (ver
        # Guide/decisions/0049-*.md) — campo por perfil desde essa ADR. Contra o fundo pastel do
        # Roze Quartz, o contorno atrapalhava a leitura de Essencial/Lazer/Ativa em vez de
        # ajudar — Investimento/Passiva já não tinham desde a ADR-0047/0048.
        "CATEGORY_NO_OUTLINE": ["Essencial", "Lazer", "Investimento", "Ativa", "Passiva"],
    }


def _load() -> dict:
    try:
        data = json.loads(_PROFILES_PATH.read_text(encoding="utf-8"))
        if not (isinstance(data, dict) and data.get("profiles")):
            raise ValueError("arquivo de perfis vazio/corrompido")
    except (OSError, ValueError):
        data = {
            "active_profile": DEFAULT_PROFILE_NAME,
            "profiles": {DEFAULT_PROFILE_NAME: _seed_detailed_profile()},
        }

    # Garante que "Roze Quartz" sempre existe como opção pronta pra usar, mesmo em
    # `color_profiles.json` já existentes de antes desse perfil ter sido adicionado — não é só
    # semeado na primeira execução (diferente de `Prizmo_V1` acima), porque quem já tinha um
    # arquivo de perfis nunca ganharia o novo sozinho.
    if ROZE_QUARTZ_PROFILE_NAME not in data["profiles"]:
        data["profiles"][ROZE_QUARTZ_PROFILE_NAME] = _seed_roze_quartz_profile()
        _save(data)

    # Mesmo motivo do backfill do Roze Quartz acima: quem já tinha `color_profiles.json` de
    # antes da ADR-0047 (cor de Investimento/Passiva virou campo por perfil, não mais uma
    # constante global) não tem esses 3 campos novos nos perfis "detailed" já salvos — sem isso,
    # `theme.apply_profile()` cairia sempre no fallback (inofensivo, mas nunca refletiria uma
    # eventual mudança de cor de um perfil "detailed" específico).
    if _backfill_investment_category_fields(data):
        _save(data)

    if _migrate_roze_quartz_investment_color(data):
        _save(data)

    if _migrate_roze_quartz_value_colors(data):
        _save(data)

    if _backfill_category_no_outline_field(data):
        _save(data)

    if _backfill_roze_quartz_value_income_text(data):
        _save(data)

    return data


_OLD_ROZE_QUARTZ_INVESTMENT_COLOR = "#C2185B"


def _migrate_roze_quartz_investment_color(data: dict) -> bool:
    """Corrige, num `color_profiles.json` já salvo, a cor de Investimento/Passiva do perfil
    "Roze Quartz" pro novo tom (ver ADR-0048) — o rosa antigo (`#C2185B`) ficava parecido demais
    com o de Essencial/Despesa. Roze Quartz é "detailed" e não editável pela UI (só perfil
    "simple" é, ver docstring do módulo), então qualquer valor salvo aqui só pode ter vindo do
    seed antigo — seguro sobrescrever sem checar customização nenhuma.
    Compara pelo valor exato do rosa antigo (não só "campo existe", diferente do backfill acima)
    pra não reaplicar depois que já rodou uma vez. Devolve `True` se mudou algo."""
    profile = data["profiles"].get(ROZE_QUARTZ_PROFILE_NAME)
    if profile is None or profile.get("INVESTMENT_CATEGORY_COLOR") != _OLD_ROZE_QUARTZ_INVESTMENT_COLOR:
        return False
    fresh = _seed_roze_quartz_profile()
    for field in ("INVESTMENT_CATEGORY_COLOR", "INVESTMENT_CATEGORY_LABEL_LIGHT_TEXT",
                  "INVESTMENT_CATEGORY_LABEL_DARK_TEXT"):
        profile[field] = fresh[field]
    return True


_OLD_ROZE_QUARTZ_VALUE_COLORS = {"VALUE_INCOME": "#A8D5BA", "VALUE_EXPENSE": "#E85D75"}


def _migrate_roze_quartz_value_colors(data: dict) -> bool:
    """Escurece (20%) `VALUE_INCOME`/`VALUE_EXPENSE` num `color_profiles.json` já salvo do
    perfil "Roze Quartz" — o tom pastel original ficava claro demais pra ler nos números da
    coluna Valor/Total do mês. Mesma lógica de `_migrate_roze_quartz_investment_color`: compara
    pelos 2 valores antigos exatos (não editáveis pela UI, então só podem ter vindo do seed
    antigo), pra não reaplicar depois que já rodou uma vez."""
    profile = data["profiles"].get(ROZE_QUARTZ_PROFILE_NAME)
    if profile is None or any(
            profile.get(field) != old for field, old in _OLD_ROZE_QUARTZ_VALUE_COLORS.items()):
        return False
    fresh = _seed_roze_quartz_profile()
    for field in _OLD_ROZE_QUARTZ_VALUE_COLORS:
        profile[field] = fresh[field]
    return True


def _backfill_investment_category_fields(data: dict) -> bool:
    """Preenche `INVESTMENT_CATEGORY_COLOR`/`INVESTMENT_CATEGORY_LABEL_LIGHT_TEXT`/
    `INVESTMENT_CATEGORY_LABEL_DARK_TEXT` em qualquer perfil "detailed" que ainda não os tenha
    (ver ADR-0047) — usa `Prizmo_V1`/`Roze Quartz` como fonte única de verdade (as próprias
    funções de seed, nunca duplica os valores), e o mesmo tom de Roze Quartz como fallback pra
    qualquer outro perfil "detailed" desconhecido (não deveria existir hoje, só a UI não cria
    perfil "detailed" — mas evita KeyError se algum dia existir). Devolve `True` se mudou algo
    (quem chama decide se salva)."""
    from iterador_ui import theme  # import tardio: evita ciclo (theme importa este módulo)

    defaults_by_name = {
        DEFAULT_PROFILE_NAME: theme.snapshot_default_palette(),
        ROZE_QUARTZ_PROFILE_NAME: _seed_roze_quartz_profile(),
    }
    fallback_defaults = defaults_by_name[ROZE_QUARTZ_PROFILE_NAME]
    fields = (
        "INVESTMENT_CATEGORY_COLOR",
        "INVESTMENT_CATEGORY_LABEL_LIGHT_TEXT",
        "INVESTMENT_CATEGORY_LABEL_DARK_TEXT",
    )

    changed = False
    for name, profile in data["profiles"].items():
        if profile.get("mode") != "detailed" or "INVESTMENT_CATEGORY_COLOR" in profile:
            continue
        source = defaults_by_name.get(name, fallback_defaults)
        for field in fields:
            profile[field] = source[field]
        changed = True
    return changed


def _backfill_category_no_outline_field(data: dict) -> bool:
    """Preenche `CATEGORY_NO_OUTLINE` em qualquer perfil "detailed" que ainda não o tenha (ver
    ADR-0049) — separado de `_backfill_investment_category_fields` de propósito: esse campo é
    novo depois que `INVESTMENT_CATEGORY_COLOR` já existia em instalações que passaram pela
    ADR-0047/0048, então checar só `"INVESTMENT_CATEGORY_COLOR" in profile` (como lá) pularia
    esses perfis sem nunca adicionar o campo novo. Mesma fonte única de verdade (funções de
    seed), mesmo fallback pra perfil "detailed" desconhecido. Devolve `True` se mudou algo."""
    from iterador_ui import theme  # import tardio: evita ciclo (theme importa este módulo)

    defaults_by_name = {
        DEFAULT_PROFILE_NAME: theme.snapshot_default_palette(),
        ROZE_QUARTZ_PROFILE_NAME: _seed_roze_quartz_profile(),
    }
    fallback_defaults = defaults_by_name[ROZE_QUARTZ_PROFILE_NAME]

    changed = False
    for name, profile in data["profiles"].items():
        if profile.get("mode") != "detailed" or "CATEGORY_NO_OUTLINE" in profile:
            continue
        source = defaults_by_name.get(name, fallback_defaults)
        profile["CATEGORY_NO_OUTLINE"] = source["CATEGORY_NO_OUTLINE"]
        changed = True
    return changed


def _backfill_roze_quartz_value_income_text(data: dict) -> bool:
    """Preenche `VALUE_INCOME_TEXT` num `color_profiles.json` já salvo do perfil "Roze Quartz"
    que ainda não o tenha (ver ADR-0050) — só esse perfil usa o campo (`Prizmo_V1`/"simple" caem
    no par (cor única, cor única) calculado em `theme.apply_profile()`, nada pra preencher
    aqui). Devolve `True` se mudou algo."""
    profile = data["profiles"].get(ROZE_QUARTZ_PROFILE_NAME)
    if profile is None or "VALUE_INCOME_TEXT" in profile:
        return False
    profile["VALUE_INCOME_TEXT"] = _seed_roze_quartz_profile()["VALUE_INCOME_TEXT"]
    return True


def _save(data: dict) -> None:
    _PROFILES_PATH.parent.mkdir(parents=True, exist_ok=True)
    _PROFILES_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def list_profiles() -> list[str]:
    return list(_load()["profiles"].keys())


def get_active_profile_name() -> str:
    return _load()["active_profile"]


def get_profile(name: str) -> dict:
    data = _load()
    if name not in data["profiles"]:
        raise ProfileError(f'Perfil "{name}" não existe.')
    return data["profiles"][name]


def set_active_profile(name: str) -> None:
    data = _load()
    if name not in data["profiles"]:
        raise ProfileError(f'Perfil "{name}" não existe.')
    data["active_profile"] = name
    _save(data)


def create_profile(name: str, fields: dict) -> None:
    name = name.strip()
    if not name:
        raise ProfileError("Informe um nome pro perfil.")
    data = _load()
    if name in data["profiles"]:
        raise ProfileError(f'Já existe um perfil chamado "{name}".')
    data["profiles"][name] = {"mode": "simple", **{k: fields[k] for k in SIMPLE_FIELDS}}
    _save(data)


def update_profile(name: str, fields: dict) -> None:
    data = _load()
    profile = data["profiles"].get(name)
    if profile is None:
        raise ProfileError(f'Perfil "{name}" não existe.')
    if profile.get("mode") != "simple":
        raise ProfileError(f'Perfil "{name}" não é editável (só perfis criados manualmente são).')
    profile.update({k: fields[k] for k in SIMPLE_FIELDS})
    _save(data)


def rename_profile(old_name: str, new_name: str) -> None:
    new_name = new_name.strip()
    if not new_name:
        raise ProfileError("Informe um nome novo.")
    data = _load()
    if old_name not in data["profiles"]:
        raise ProfileError(f'Perfil "{old_name}" não existe.')
    if new_name != old_name and new_name in data["profiles"]:
        raise ProfileError(f'Já existe um perfil chamado "{new_name}".')
    data["profiles"][new_name] = data["profiles"].pop(old_name)
    if data["active_profile"] == old_name:
        data["active_profile"] = new_name
    _save(data)


def delete_profile(name: str) -> None:
    data = _load()
    if name not in data["profiles"]:
        return
    if len(data["profiles"]) <= 1:
        raise ProfileError("Não dá pra remover o último perfil restante.")
    del data["profiles"][name]
    if data["active_profile"] == name:
        data["active_profile"] = next(iter(data["profiles"]))
    _save(data)
