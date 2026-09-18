"""Helper pra garantir no máximo uma instância de cada diálogo modal aberta por vez.

Sem isso, clicar várias vezes rápido num botão que abre diálogo (ex. "+ Mês", "+ Adicionar")
empilha várias janelas `CTkToplevel` idênticas — bagunçado e fácil de perder o controle (a
seguinte só é fechada se o usuário achar/fechar cada uma na mão). `open_singleton` guarda a
referência do diálogo aberto num atributo do dono (`owner`) e, se ainda existir, só traz pra
frente em vez de criar outra.
"""


def make_modal(dialog, master) -> None:
    """Deixa `dialog` transiente e modal em relação a `master`. `grab_set()` exige que a janela
    já esteja mapeada pelo window manager — chamado direto após criar o `Toplevel`, sem essa
    garantia, lança `_tkinter.TclError: grab failed: window not viewable`. Isso interrompe o
    `__init__` do diálogo antes de qualquer widget de conteúdo ser adicionado (janela some vazia)
    e, pior, antes de `open_singleton` registrar a instância — então a trava de janela única
    nunca chega a valer, e o próximo clique (ex. clique duplo rápido com o mouse parado no botão)
    empilha outro diálogo por cima. Adiar `grab_set()` via `after()` (em vez de chamar direto) dá
    tempo do window manager mapear a janela primeiro, sem bloquear a fila de eventos como
    `wait_visibility()` faria (o que reabriria essa mesma janela de corrida)."""
    dialog.transient(master)
    dialog.after(10, dialog.grab_set)


def open_singleton(owner, attr: str, factory):
    """Abre `factory()` (deve retornar um `CTkToplevel`) só se não houver uma instância viva
    guardada em `owner.<attr>`; caso contrário, traz a janela existente pra frente."""
    existing = getattr(owner, attr, None)
    if existing is not None and existing.winfo_exists():
        existing.lift()
        existing.focus_force()
        return existing

    dialog = factory()
    setattr(owner, attr, dialog)
    return dialog
