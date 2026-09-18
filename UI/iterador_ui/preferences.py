"""Preferências locais persistidas entre execuções — tema claro/escuro e escala da interface
(ver ADR-0044).

Fica num arquivo próprio (`~/.iterador/preferences.json`), **separado** de
`~/.iterador/iterador.db` — nunca mistura com o banco de dados real do usuário (ver CLAUDE.md).
É só um arquivo de configuração pequeno, seguro de recriar do zero se faltar ou corromper.

`_load()`/`_save()` fazem round-trip (lê tudo, guarda tudo) — igual `color_profiles.py`/
`custom_categories.py` — pra um campo novo não apagar os outros já salvos.
"""

import json
from pathlib import Path

from iterador_ui import theme

_PREFERENCES_PATH = Path.home() / ".iterador" / "preferences.json"


def _load() -> dict:
    try:
        data = json.loads(_PREFERENCES_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (OSError, ValueError):
        pass
    return {}


def _save(data: dict) -> None:
    _PREFERENCES_PATH.parent.mkdir(parents=True, exist_ok=True)
    _PREFERENCES_PATH.write_text(json.dumps(data), encoding="utf-8")


def load_appearance_mode() -> str:
    """Último modo de aparência salvo ("dark"/"light"); `theme.DEFAULT_APPEARANCE_MODE` se o
    arquivo não existir, estiver corrompido, ou tiver um valor que não seja um modo válido."""
    mode = _load().get("appearance_mode")
    return mode if mode in theme.APPEARANCE_MODES else theme.DEFAULT_APPEARANCE_MODE


def save_appearance_mode(mode: str) -> None:
    data = _load()
    data["appearance_mode"] = mode
    _save(data)


def load_ui_scale() -> float:
    """Última escala de interface salva (0.9/1.0/1.1/1.25/1.5 — ver
    `theme.UI_SCALE_OPTIONS`); `theme.DEFAULT_UI_SCALE` se o arquivo não existir, estiver
    corrompido, ou tiver um valor que não seja uma das opções válidas."""
    scale = _load().get("ui_scale")
    return scale if scale in theme.UI_SCALE_OPTIONS else theme.DEFAULT_UI_SCALE


def save_ui_scale(scale: float) -> None:
    data = _load()
    data["ui_scale"] = scale
    _save(data)
