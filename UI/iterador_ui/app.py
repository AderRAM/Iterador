"""Janela raiz, navegação entre views e toggle de tema claro/escuro. Ver Guide/file-map.md."""

import tkinter as tk
from pathlib import Path

import customtkinter as ctk
from customtkinter.windows.widgets.core_rendering.draw_engine import DrawEngine

# CustomTkinter desenha todo widget arredondado (qualquer CTkButton/CTkFrame com corner_radius)
# via um destes 3 métodos (`DrawEngine.DRAWING_METHODS`, opção pública — o próprio app de
# exemplo do pacote expõe um seletor pra isso). No Linux/Windows o padrão é "font_shapes" (glifos
# de uma fonte especial via `create_text`, mais suave visualmente) — bem mais caro que
# "polygon_shapes" (usado por padrão só no macOS): 2 polígonos redesenhados via `coords()`, sem
# `create_text`/`create_aa_circle` por widget. Medido (ver Guide/decisions/0049, banco sintético
# numa escala realista de uso — ~700 lançamentos/33 meses, nunca o banco real): trocar pra
# "polygon_shapes" cortou o tempo de abrir o app de ~0.90s pra ~0.37s, revisitar uma aba com
# várias linhas de ~0.30s pra ~0.04s, e trocar de mês no Início em ~25% — sem cair pro
# "circle_shapes" (o único dos 3 documentado pelo próprio pacote como "má qualidade", usado só
# se a fonte não carregar). Setado aqui, antes de qualquer widget CTk ser construído (a única
# exigência) — sem condicional de plataforma porque no macOS isso só reafirma o padrão que já
# seria usado, sem efeito.
DrawEngine.preferred_drawing_method = "polygon_shapes"

from iterador_ui import backend_bridge, preferences, theme
from iterador_ui.views.budgets_view import BudgetsView
from iterador_ui.views.dashboard_view import DashboardView
from iterador_ui.views.investments_view import InvestmentsView
from iterador_ui.views.settings_view import SettingsView
from iterador_ui.views.wiki_view import WikiView
from iterador_ui.widgets.sidebar import Sidebar

_ICON_PATH = Path(__file__).resolve().parent.parent / "assets" / "icon.png"

_VIEW_CLASSES = {
    "dashboard": DashboardView,
    "investments": InvestmentsView,
    "budgets": BudgetsView,
    "wiki": WikiView,
    "settings": SettingsView,
}


class IteradorApp(ctk.CTk):
    def __init__(self, db_path: str):
        super().__init__()

        # Lembra o último modo escolhido entre execuções (ver preferences.py) — antes sempre
        # abria em "dark", ignorando o que o usuário tinha deixado configurado da última vez.
        self._appearance_mode = preferences.load_appearance_mode()
        ctk.set_appearance_mode(self._appearance_mode)

        self.title("Iterador")
        # Alto o suficiente pra lista de lançamentos do Início mostrar uns 10 itens de cara,
        # sem precisar redimensionar a janela na mão (relato do usuário) — ver ADR-0016.
        # PRECISA vir antes de `ctk.set_widget_scaling()` abaixo (bug real, ver ADR-0046):
        # `CTk._set_scaling()` trava minsize=maxsize=tamanho-atual-da-janela por ~1s toda vez
        # que a escala é aplicada (hack interno do CustomTkinter), usando `_current_width/height`
        # no momento da chamada — com `set_widget_scaling` ANTES da geometry, esse tamanho-atual
        # ainda era o default de 600x500 do CTk, não os 1200x900 pedidos aqui, e a janela nunca
        # se recuperava depois (min/max se autocorrigem, mas o Tk não redimensiona a janela de
        # volta sozinho) — abria sempre em 900x600 (o mínimo) e, durante esse ~1s inicial com
        # minsize>maxsize invertido, o WM via a janela como não-redimensionável e escondia os
        # botões de maximizar/restaurar da decoração (relato do usuário: só o X aparecia).
        self.geometry("1200x900")
        self.minsize(900, 600)

        # Escala geral da interface (ver ADR-0044, preferences.py) — CustomTkinter já reescala
        # todo widget construído a partir daqui sozinho, sem precisar de `rebuild_ui()`.
        ctk.set_widget_scaling(preferences.load_ui_scale())
        self.configure(fg_color=theme.BG_APP)
        # Ícone da própria janela (independente do ícone do menu do KDE, que fica em
        # UI/assets/icon.svg + scripts/install_desktop_launcher.sh) — evita depender de cache
        # de ícone do desktop para a janela em si mostrar a cor certa.
        if _ICON_PATH.exists():
            self._window_icon = tk.PhotoImage(file=str(_ICON_PATH))
            self.iconphoto(True, self._window_icon)

        backend_bridge.open_database(db_path)

        self._content = ctk.CTkFrame(self, fg_color=theme.BG_APP)
        self._content.pack(side="right", fill="both", expand=True)

        self._sidebar = Sidebar(
            self, on_navigate=self.show_view, on_toggle_theme=self._on_toggle_theme,
            appearance_mode=self._appearance_mode,
        )
        self._sidebar.pack(side="left", fill="y")

        self._current_view = None
        self._current_view_name = "dashboard"
        # Views já construídas, uma por aba — reaproveitadas entre trocas de aba em vez de
        # destruir/recriar (ver `show_view()`). Início é a mais cara de construir (lista de
        # lançamentos, gráfico, cards); destruir e recriar do zero a cada ida-e-volta pra outra
        # aba também jogava fora o pool de widgets da lista (ver ADR-0026), então voltar pro
        # Início tinha o mesmo delay que o primeiro carregamento, sempre — relato do usuário.
        self._views: dict[str, ctk.CTkBaseClass] = {}
        self.show_view("dashboard")

    def show_view(self, name: str) -> None:
        if self._current_view is not None:
            self._current_view.pack_forget()

        self._current_view_name = name
        view = self._views.get(name)
        if view is None:
            view_class = _VIEW_CLASSES[name]
            if name == "settings":
                view = SettingsView(self._content, on_visuals_changed=self.rebuild_ui)
            else:
                view = view_class(self._content)
            self._views[name] = view
        elif hasattr(view, "refresh"):
            # View já existia (ex. voltando pro Início) — recarrega os dados sem reconstruir os
            # widgets, pra não perder o ganho do pool (ADR-0026) nem pagar de novo o custo de
            # construção inicial.
            view.refresh()

        self._current_view = view
        self._current_view.pack(fill="both", expand=True)
        self._sidebar.set_active(name)

    def rebuild_ui(self) -> None:
        """Reconstrói Sidebar + TODAS as views do zero — necessário depois de trocar/editar um
        perfil de cor (ver ADR-0025) OU trocar/remover a imagem customizada da sidebar (ver
        ADR-0036): nada disso recolore/reconstrói widget já criado sozinho (só troca de tema
        claro/escuro faz isso nativamente no CustomTkinter). Views não visíveis no momento
        também precisam ser descartadas do cache de `show_view()` (ver ADR-0026/0027) — senão
        continuariam com o visual antigo preso quando o usuário voltasse a visitá-las. Passado
        pra `SettingsView` como `on_visuals_changed` — nome genérico porque hoje serve dois
        motivos diferentes, não só perfil de cor."""
        self.configure(fg_color=theme.BG_APP)
        self._content.configure(fg_color=theme.BG_APP)
        self._sidebar.destroy()
        self._sidebar = Sidebar(
            self, on_navigate=self.show_view, on_toggle_theme=self._on_toggle_theme,
            appearance_mode=self._appearance_mode,
        )
        self._sidebar.pack(side="left", fill="y")

        for view in self._views.values():
            view.destroy()
        self._views = {}
        self._current_view = None
        self.show_view(self._current_view_name)

    def _on_toggle_theme(self, is_light: bool) -> None:
        self._appearance_mode = "light" if is_light else "dark"
        ctk.set_appearance_mode(self._appearance_mode)
        preferences.save_appearance_mode(self._appearance_mode)
