"""Menu de navegação lateral, com o toggle de tema claro/escuro. Ver Guide/file-map.md e
Guide/decisions/0020-color-profile-system.md.

Cada item de navegação tem uma barrinha fina embaixo (`Divider`) que serve dois papéis: separa
visualmente um item do próximo (neutra, ver ADR-0020) e, na página atualmente selecionada, vira
vermelha e mais grossa — o indicador de "você está aqui" (não existia nenhum sinal visual disso
antes, ver `set_active()`).
"""

import customtkinter as ctk

from iterador_ui import sidebar_image, theme
from iterador_ui.widgets.divider import Divider
from iterador_ui.widgets.triangle_heading import TriangleHeading

_NAV_ITEMS = [
    ("dashboard", "Início"),
    ("investments", "Investimentos"),
    ("budgets", "Orçamentos"),
    ("wiki", "Wiki"),
    ("settings", "Configurações"),
]

_INDICATOR_INACTIVE_HEIGHT = 2
_INDICATOR_ACTIVE_HEIGHT = 3


class Sidebar(ctk.CTkFrame):
    def __init__(self, master, on_navigate, on_toggle_theme, appearance_mode: str):
        # Fundo BG_PANEL_BLUE na própria sidebar — sem frame aninhado por baixo, ela já é o
        # único frame que precisa cobrir "Iterador" e os itens de navegação/botão de tema (o
        # heading continua se destacando por ter sua própria textura, ver TriangleHeading).
        # Borda preta fixa (CARBON_BLACK, não varia por tema) — no modo claro, BG_PANEL_BLUE
        # ficava perto demais do fundo do app pra dar pra notar o limite da sidebar sem ela.
        super().__init__(
            master, fg_color=theme.BG_PANEL_BLUE, width=180, corner_radius=0,
            border_width=1, border_color=theme.CARBON_BLACK)
        # Sem isso, um filho mais largo que 180 (ex. a imagem customizada, ver
        # sidebar_image.LOGO_SIZE) faz a Sidebar INTEIRA crescer pra caber nele — o `width=180`
        # acima vira só um tamanho inicial, não um limite de verdade. Travado aqui pra "não
        # encostar na borda" ser uma restrição real, testável, não um alvo que se move sozinho.
        self.pack_propagate(False)
        self._on_navigate = on_navigate
        self._on_toggle_theme = on_toggle_theme
        self._is_light = appearance_mode == "light"
        self._indicators: dict[str, Divider] = {}
        self._active_view: str | None = None

        # Imagem customizada (Configurações > "Imagem da barra lateral") aparece ACIMA do
        # mosaico "Iterador" — não no lugar dele (relato do usuário: a marca "Iterador" some
        # nunca deveria acontecer, ver ADR-0037). Se o usuário nunca enviou uma própria, cai na
        # imagem padrão embutida em assets/ ("Atlas.*", emoldurada na hora, ver
        # sidebar_image.get_display_image()). padx=2 (bem menor que os 12 do mosaico) — é o
        # mínimo de respiro pra não encostar de fato na borda da Sidebar, deixando a imagem o
        # mais larga possível — ver sidebar_image.LOGO_SIZE/ADR-0040.
        logo_image = sidebar_image.get_display_image()
        if logo_image is not None:
            custom_image = ctk.CTkLabel(
                self, image=ctk.CTkImage(logo_image, size=sidebar_image.LOGO_SIZE),
                text="")
            custom_image.pack(fill="x", padx=2, pady=(16, 8))

        heading = TriangleHeading(self, "Iterador")
        heading.pack(fill="x", padx=12, pady=(16 if logo_image is None else 0, 12))

        for index, (view_name, label) in enumerate(_NAV_ITEMS):
            item = ctk.CTkFrame(self, fg_color="transparent")
            top_pad = 8 if index == 0 else 0
            item.pack(fill="x", padx=8, pady=(top_pad, 8 if index == len(_NAV_ITEMS) - 1 else 4))

            button = ctk.CTkButton(
                item, text=label, anchor="w",
                fg_color="transparent", hover_color=theme.ACCENT_INCOME,
                text_color=theme.TEXT_PRIMARY,
                command=lambda v=view_name: self._on_navigate(v),
            )
            button.pack(fill="x")

            indicator = Divider(
                item, color=theme.BORDER_NEUTRAL, thickness=_INDICATOR_INACTIVE_HEIGHT)
            indicator.pack(fill="x", pady=(3, 0))
            self._indicators[view_name] = indicator

            # A cor de hover do botão sozinha não cobre a barrinha indicadora logo abaixo dele
            # (ver relato do usuário) — colorindo também o item (fundo) e a barrinha, o destaque
            # cobre a linha branca/vermelha junto, não só o texto do botão.
            button.bind(
                "<Enter>",
                lambda _e, i=item, ind=indicator, b=button: self._on_item_hover(i, ind, True, b=b))
            button.bind(
                "<Leave>",
                lambda _e, i=item, ind=indicator, v=view_name, b=button: self._on_item_hover(
                    i, ind, False, v, b=b))

        # Botão (era switch) que alterna tema claro/escuro — quadrado, não mais em formato de
        # pílula, com ícone de sol (modo claro) ou lua minguante (modo escuro) e cor própria por
        # modo: amarelo (Sunflower Gold) = escuro, cinza = claro (mesmas cores do switch antigo,
        # THEME_SWITCH_DARK_COLOR/THEME_SWITCH_LIGHT_COLOR); hover um tom mais escuro de cada
        # uma, pra reagir visivelmente à presença do mouse.
        self._theme_button = ctk.CTkButton(
            self, text=self._theme_button_icon(), font=ctk.CTkFont(size=14),
            width=32, height=32, corner_radius=8, text_color=theme.CARBON_BLACK,
            fg_color=self._theme_button_color(), hover_color=self._theme_button_hover_color(),
            command=self._toggle_theme,
        )
        self._theme_button.pack(side="bottom", padx=8, pady=16, anchor="w")

    def _theme_button_icon(self) -> str:
        return "☀️" if self._is_light else "🌘"

    def _theme_button_color(self) -> str:
        return theme.THEME_SWITCH_LIGHT_COLOR if self._is_light else theme.THEME_SWITCH_DARK_COLOR

    def _theme_button_hover_color(self) -> str:
        return theme.THEME_SWITCH_LIGHT_HOVER if self._is_light else theme.THEME_SWITCH_DARK_HOVER

    def _toggle_theme(self) -> None:
        self._is_light = not self._is_light
        self._theme_button.configure(
            text=self._theme_button_icon(), fg_color=self._theme_button_color(),
            hover_color=self._theme_button_hover_color())
        self._on_toggle_theme(self._is_light)

    def _on_item_hover(self, item, indicator, entering: bool, view_name: str | None = None,
                        b=None) -> None:
        if entering:
            item.configure(fg_color=theme.ACCENT_INCOME)
            indicator.configure(fg_color=theme.ACCENT_INCOME)
            # Texto branco fixo (não `theme.TEXT_PRIMARY`) durante o hover — o fundo vira
            # `theme.ACCENT_INCOME` (roxo neste perfil de cor), e `TEXT_PRIMARY` no modo claro é
            # quase preto, ilegível em cima dele (mesmo problema do mês selecionado no Início).
            b.configure(text_color="#FFFFFF")
            return

        item.configure(fg_color="transparent")
        b.configure(text_color=theme.TEXT_PRIMARY)
        is_active = view_name == self._active_view
        indicator.configure(
            fg_color=theme.NAV_INDICATOR_ACTIVE if is_active else theme.BORDER_NEUTRAL,
            height=_INDICATOR_ACTIVE_HEIGHT if is_active else _INDICATOR_INACTIVE_HEIGHT)

    def set_active(self, view_name: str) -> None:
        """Chamado pela `IteradorApp` a cada navegação — recolore a barrinha de cada item:
        vermelha e mais grossa na página atual, neutra e fina nas outras."""
        self._active_view = view_name
        for name, indicator in self._indicators.items():
            if name == view_name:
                indicator.configure(
                    fg_color=theme.NAV_INDICATOR_ACTIVE, height=_INDICATOR_ACTIVE_HEIGHT)
            else:
                indicator.configure(
                    fg_color=theme.BORDER_NEUTRAL, height=_INDICATOR_INACTIVE_HEIGHT)
