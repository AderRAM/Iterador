"""Ponto de entrada da UI. Rode com: python UI/main.py (ver Guide/usage.md).

O script garante que as pastas necessárias existam:
- ~/.iterador/ — banco de dados do aplicativo (padrão, sempre criado)
- Dados/ — pasta local do usuário para planilhas/arquivos (não versionada via git, conteúdo próprio do usuário)

O banco de dados do aplicativo SEMPRE fica em ~/.iterador/iterador.db, independentemente
da existência da pasta Dados. A pasta Dados é apenas para arquivos do usuário (planilhas,
extratos CSV), não para o banco de dados interno.
"""

from pathlib import Path

from iterador_ui.app import IteradorApp

_DB_PATH = Path.home() / ".iterador" / "iterador.db"


def main() -> None:
    # Garante pastas necessárias
    # O banco de dados do aplicativo SEMPRE fica em ~/.iterador/iterador.db
    (Path.home() / ".iterador").mkdir(parents=True, exist_ok=True)
    (Path.home() / ".iterador" / "Dados").mkdir(parents=True, exist_ok=True)
    
    _DB_PATH = Path.home() / ".iterador" / "iterador.db"
    
    app = IteradorApp(str(_DB_PATH))
    app.mainloop()


if __name__ == "__main__":
    main()
