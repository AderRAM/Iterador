"""Fundo em mosaico triangular ("low-poly") pro título "Iterador" da sidebar — ver
Guide/decisions/0025-color-profile-management.md.

Antes era um `CTkLabel` com fundo sólido Sunflower Gold. O usuário pediu uma cor que combinasse
mais com o ícone do app (`UI/assets/icon.png`) — amostrei o arquivo de verdade (análise de pixel,
não só olhando) e o laranja do ícone é um aglomerado de tonalidades (`#F8A000` mais vibrante até
`#D06800` mais escuro/queimado), não uma cor única. Em cima disso, o usuário pediu uma textura de
triângulos, cada um com uma tonalidade sorteada dentro desse mesmo aglomerado (não cor arbitrária)
— um mosaico "low-poly" em vez de fundo chapado.

Desenhado num `tkinter.Canvas` puro, mesmo padrão de `ConsumptionChart`/`LineChart`. Sem cantos
arredondados (o `CTkLabel` antigo tinha `corner_radius=6`) — recortar triângulos dentro de um
raio arredondado é bem mais trabalho por pouco ganho visual; vira um retângulo reto (ver ADR-0025).
"""

import random
import tkinter as tk

import customtkinter as ctk

from iterador_ui import theme

_WIDTH = 156
_HEIGHT = 44
_COLUMNS = 8
_ROWS = 3

# Aglomerado real de laranjas do ícone (amostrado por análise de pixel de UI/assets/icon.png,
# não escolhido a olho) — do mais vibrante ao mais escuro/queimado.
ICON_ORANGE_CLUSTER = ["#F8A000", "#F89000", "#F09800", "#E89800", "#D88800", "#D06800"]


def _jitter(hex_color: str, amount: int = 12) -> str:
    """Pequena variação aleatória de brilho em cima de uma cor do aglomerado — dá mais variedade
    de tons sem sair da família de laranjas do ícone."""
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    delta = random.randint(-amount, amount)
    r, g, b = (max(0, min(255, c + delta)) for c in (r, g, b))
    return f"#{r:02X}{g:02X}{b:02X}"


class TriangleHeading(ctk.CTkFrame):
    def __init__(self, master, text: str):
        super().__init__(master, fg_color="transparent")
        # Nome próprio (não `self._canvas`) — `CTkFrame` (superclasse) já usa esse atributo
        # internamente pro canvas do próprio fundo arredondado; sobrescrever quebra o recolore
        # automático de tema (mesmo bug já corrigido em ConsumptionChart/LineChart, ver ADR-0020).
        self._mosaic_canvas = tk.Canvas(
            self, width=_WIDTH, height=_HEIGHT, highlightthickness=0,
            bg=ICON_ORANGE_CLUSTER[0])
        self._mosaic_canvas.pack()
        self._draw_mosaic()
        self._draw_border()
        self._draw_outlined_text(text)

    def _draw_border(self) -> None:
        """Borda fina escura ao redor do retângulo do mosaico — sem isso o laranja do mosaico se
        mistura com o fundo da Sidebar (BG_PANEL_BLUE) em alguns perfis de cor, perdendo o limite
        do retângulo (relato do usuário)."""
        self._mosaic_canvas.create_rectangle(
            0, 0, _WIDTH - 1, _HEIGHT - 1, outline=theme.CARBON_BLACK, width=1)

    def _draw_outlined_text(self, text: str) -> None:
        """`tkinter.Canvas.create_text` não tem opção de contorno por letra — o texto escuro
        sozinho ficava com pouca visibilidade em cima do mosaico laranja. Efeito de borda branca
        "por letra" simulado desenhando o mesmo texto várias vezes em branco, deslocado 1px em
        cada direção ao redor, e por cima disso o texto normal (escuro) — como o texto de baixo
        sempre aparece um pouco pra fora do de cima em todas as direções, vira uma borda branca
        ao redor de cada letra."""
        font = (theme.HEADING_FONT_FAMILY, 18, "bold")
        cx, cy = _WIDTH / 2, _HEIGHT / 2
        for dx, dy in ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)):
            self._mosaic_canvas.create_text(
                cx + dx, cy + dy, text=text, fill="#FFFFFF", font=font)
        self._mosaic_canvas.create_text(cx, cy, text=text, fill=theme.HEADING_TEXT, font=font)

    def _draw_mosaic(self) -> None:
        cell_w = _WIDTH / _COLUMNS
        cell_h = _HEIGHT / _ROWS
        for col in range(_COLUMNS):
            for row in range(_ROWS):
                x0, y0 = col * cell_w, row * cell_h
                x1, y1 = x0 + cell_w, y0 + cell_h
                # Cada célula vira 2 triângulos (diagonal alternada, pra não formar um padrão
                # óbvio de "X" repetido) — cada um com sua própria cor sorteada.
                if (col + row) % 2 == 0:
                    triangles = [(x0, y0, x1, y0, x0, y1), (x1, y0, x1, y1, x0, y1)]
                else:
                    triangles = [(x0, y0, x1, y0, x1, y1), (x0, y0, x1, y1, x0, y1)]
                for points in triangles:
                    color = _jitter(random.choice(ICON_ORANGE_CLUSTER))
                    self._mosaic_canvas.create_polygon(*points, fill=color, outline="")
