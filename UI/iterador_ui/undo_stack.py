"""Pilha de desfazer/refazer para ações na lista de lançamentos. Ver Guide/file-map.md.

Escopo por sessão (não persiste entre reinícios do app) e específico das mutações feitas pela
UI de transações (criar/editar/remover/alternar status) — não é um sistema genérico de undo
para o app inteiro. Comandos são objetos com .undo()/.redo(); ver
UI/iterador_ui/views/dashboard_view.py para os comandos concretos.
"""


class UndoStack:
    def __init__(self):
        self._undo_stack = []
        self._redo_stack = []

    def push(self, command) -> None:
        """Chamar DEPOIS de já ter aplicado a ação — push só registra o comando pra poder
        desfazer, não executa `command.redo()` sozinho."""
        self._undo_stack.append(command)
        self._redo_stack.clear()

    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    def undo(self) -> None:
        if not self._undo_stack:
            return
        command = self._undo_stack.pop()
        command.undo()
        self._redo_stack.append(command)

    def redo(self) -> None:
        if not self._redo_stack:
            return
        command = self._redo_stack.pop()
        command.redo()
        self._undo_stack.append(command)
