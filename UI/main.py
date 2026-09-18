"""Ponto de entrada da UI. Rode com: python UI/main.py (ver Guide/usage.md)."""

from pathlib import Path

from iterador_ui.app import IteradorApp

_DB_PATH = Path.home() / ".iterador" / "iterador.db"


def main() -> None:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    app = IteradorApp(str(_DB_PATH))
    app.mainloop()


if __name__ == "__main__":
    main()
