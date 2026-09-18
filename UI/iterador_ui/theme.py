"""Paleta de cores do Iterador. Ver Guide/architecture.md -> Identidade visual (UI),
Guide/decisions/0020-color-profile-system.md e Guide/decisions/0025-color-profile-management.md.

Dois grupos de papéis de cor:

- **Fixos** (`_fixed_roles()`) — cores de marca (Brick Ember/Indigo dos botões), valores
  monetários, cor por categoria, badge Pago/A pagar, botão de tema — iguais em **qualquer**
  perfil, não fazem parte do que o usuário customiza (ver ADR-0025).
- **Estruturais** (fundo do app, fundo de painel/card, texto estático, borda/separador) — esses
  sim variam por perfil. Um perfil "detailed" (só `Prizmo_V1`, o visual de sempre) guarda os
  valores certinho como sempre foram; um perfil "simple" (criado pelo usuário via Configurações)
  guarda só 4 cores (`color_profiles.SIMPLE_FIELDS`) que `_expand_simple_profile()` estica pros
  mesmos papéis estruturais.

`apply_profile()` combina fixos + estruturais (do perfil ativo, lido de `color_profiles.py`) e
empurra tudo pro nível de módulo — o resto da UI continua usando `theme.NOME_DA_COR`/
`theme.helper()` do jeito de sempre, sem saber que existe um sistema de perfis por trás.

Nenhum outro arquivo da UI deve usar cores "soltas" — sempre importar os papéis daqui.
"""

import customtkinter as ctk

from iterador_ui import color_profiles, custom_categories

# Declarações (sem valor) pra editores/type checkers (ex. Pylance) reconhecerem `theme.NOME`
# como atributo válido do módulo — sem isso, todo import de uma cor daqui aparece como erro
# ("X is not a known attribute of module") mesmo funcionando em runtime. Os valores de verdade
# são injetados por `apply_profile()` no fim deste arquivo (ver ADR-0020); as anotações abaixo
# não têm nenhum efeito em runtime.
BRICK_EMBER: str
INDIGO: str
CARBON_BLACK: str
DEEP_SAFFRON: str
SUNFLOWER_GOLD: str
ELECTRIC_BLUE: str
BG_APP: tuple[str, str]
BG_SURFACE: tuple[str, str]
BG_PANEL_BLUE: tuple[str, str]
TEXT_PRIMARY: tuple[str, str]
TEXT_ON_BLACK: str
ACCENT_EXPENSE: str
ACCENT_INCOME: str
ACCENT_HIGHLIGHT: str
VALUE_INCOME: str
VALUE_EXPENSE: str
VALUE_INCOME_TEXT: tuple[str, str]
VALUE_EXPENSE_TEXT: tuple[str, str]
BORDER_NEUTRAL: tuple[str, str]
BORDER_ACCENT: str
STATUS_BADGE_BORDER: tuple[str, str]
NAV_INDICATOR_ACTIVE: str
ROW_SEPARATOR: str
THEME_SWITCH_DARK_COLOR: str
THEME_SWITCH_DARK_HOVER: str
THEME_SWITCH_LIGHT_COLOR: str
THEME_SWITCH_LIGHT_HOVER: str
CATEGORY_COLORS: dict[str, str]
CATEGORY_LABEL_COLORS: dict[str, tuple[str, str]]
CATEGORY_NO_OUTLINE: set[str]
HEADING_TEXT: str
INVESTMENT_CATEGORY_COLOR: str
INVESTMENT_CATEGORY_LABEL_LIGHT_TEXT: str
INVESTMENT_CATEGORY_LABEL_DARK_TEXT: str


def _fixed_roles() -> dict:
    """Papéis de cor iguais em qualquer perfil — marca, valores monetários, indicadores, botão
    de tema. Ver módulo docstring / ADR-0025 pro porquê disso não ser customizável ainda."""
    brick_ember = "#B7410E"
    indigo = "#4B0082"
    carbon_black = "#1A1A1A"
    deep_saffron = "#FF9933"
    # Antes era o mesmo amarelo do fundo do logo "Iterador" (Sunflower Gold, #FFC72C) — o
    # usuário achou pouco a ver com o ícone do app e pediu uma cor mais parecida com o laranja
    # dele. Ícone lido de verdade (análise de pixel de UI/assets/icon.png, não escolhido a olho):
    # aglomerado de laranjas de #F8A000 (mais vibrante/frequente) a #D06800 (mais escuro) — usei
    # o tom mais frequente. O fundo do próprio logo foi além disso e virou uma textura de
    # triângulos com esse aglomerado inteiro (ver `widgets/triangle_heading.py`), não só essa
    # cor sólida — mas ACCENT_HIGHLIGHT/THEME_SWITCH_DARK_COLOR (borda do card de Total do mês,
    # botão de tema no escuro) usam essa cor sólida mesmo, por ainda serem elementos de UI
    # normais, não texturizados.
    sunflower_gold = "#F8A000"
    sunflower_gold_hover = "#DA8D00"  # tom mais escuro, só pra feedback de hover
    electric_blue = "#3B82F6"

    return {
        "BRICK_EMBER": brick_ember,
        "INDIGO": indigo,
        "CARBON_BLACK": carbon_black,
        "DEEP_SAFFRON": deep_saffron,
        "SUNFLOWER_GOLD": sunflower_gold,
        "ELECTRIC_BLUE": electric_blue,

        # Cor resolvida (não-tupla) pra widgets tkinter puros (ex. Canvas) que não entendem os
        # pares (claro, escuro) do CustomTkinter — usada sobre fundos fixos em Carbon Black.
        "TEXT_ON_BLACK": "#EAEAEA",
        "HEADING_TEXT": carbon_black,

        # Brick Ember é a cor de destaque principal do app.
        "ACCENT_EXPENSE": brick_ember,
        "ACCENT_INCOME": indigo,
        "ACCENT_HIGHLIGHT": sunflower_gold,

        # Só pra exibir valores monetários de receita/despesa (lista de lançamentos, Total do
        # mês) — diferente de ACCENT_INCOME/ACCENT_EXPENSE, que continuam Indigo/Brick Ember no
        # resto da UI (ex. botões).
        "VALUE_INCOME": "#90EE90",   # verde claro
        "VALUE_EXPENSE": "#FF0000",  # vermelho puro
        "NAV_INDICATOR_ACTIVE": "#FF0000",

        # Botão de tema claro/escuro (sidebar): invertido de propósito — amarelo no modo
        # escuro, cinza no modo claro. As versões _HOVER são um tom mais escuro de cada uma,
        # só pra dar feedback visível quando o mouse passa por cima (ver ADR-0013).
        "THEME_SWITCH_DARK_COLOR": sunflower_gold,
        "THEME_SWITCH_DARK_HOVER": sunflower_gold_hover,
        "THEME_SWITCH_LIGHT_COLOR": "#9E9E9E",
        "THEME_SWITCH_LIGHT_HOVER": "#868686",
    }


def snapshot_default_palette() -> dict:
    """Papéis completos (fixos + estruturais) do visual original do Iterador — usado só pra
    semear o perfil `Prizmo_V1` na primeira execução (ver `color_profiles._seed_detailed_profile`).
    Depois de semeado, `Prizmo_V1` vive só no `color_profiles.json`; esta função não é mais
    consultada pra ele (só serviria de novo se o arquivo de perfis fosse apagado)."""
    palette = _fixed_roles()

    # Tons neutros que variam por tema — sempre tuplas (claro, escuro), CustomTkinter troca
    # sozinho quando ctk.set_appearance_mode() muda. Estes SIM fazem parte do perfil (papéis
    # "estruturais") — um perfil "simple" novo os substitui por 4 cores só (ver
    # `_expand_simple_profile`).
    light_bg = "#F5F1EA"
    light_surface = "#FFFFFF"
    light_text = palette["CARBON_BLACK"]
    light_border_neutral = "#B8B2A3"  # separador neutro: contraste contra fundo claro
    # Fundo de frame estrutural (ver DashboardView/Sidebar): quase igual a light_bg, só um
    # pouco puxado pro azul — dá pra notar o contorno do frame sem destacar demais.
    light_panel_blue = "#EAF0FA"

    dark_bg = palette["CARBON_BLACK"]
    dark_surface = "#242424"
    dark_text = "#EAEAEA"
    dark_border_neutral = "#FFFFFF"  # separador neutro: branco no modo escuro, como pedido
    # Mesma ideia de light_panel_blue, só que puxando dark_bg (Carbon Black) pro azul.
    dark_panel_blue = "#1A212C"

    palette.update({
        "BG_APP": (light_bg, dark_bg),
        "BG_SURFACE": (light_surface, dark_surface),
        "BG_PANEL_BLUE": (light_panel_blue, dark_panel_blue),
        "TEXT_PRIMARY": (light_text, dark_text),

        # Separadores/bordas estruturais (ver ADR-0020): BORDER_NEUTRAL isola grupos de forma
        # discreta (ex. entre itens da sidebar); BORDER_ACCENT marca divisões mais importantes
        # da tela (cabeçalho, barra de colunas da lista) e é a cor da borda dos botões de
        # contorno; ROW_SEPARATOR separa cada lançamento na lista do Início.
        "BORDER_NEUTRAL": (light_border_neutral, dark_border_neutral),
        "BORDER_ACCENT": palette["ELECTRIC_BLUE"],
        # Borda dos botões "Pago"/"A pagar" — branca no escuro, preta no claro (branco sobre
        # fundo claro ficava invisível, ver relato do usuário).
        "STATUS_BADGE_BORDER": (palette["CARBON_BLACK"], "#FFFFFF"),
        "ROW_SEPARATOR": "#3FA796",  # verde-azulado dos separadores finos entre lançamentos

        # Cor de Investimento/Passiva (ver ADR-0043/ADR-0047) — campo POR PERFIL desde a
        # ADR-0047 (antes era uma constante global, mudar pro perfil Roze Quartz mudava também
        # o Prizmo_V1, relato do usuário). Roxo/violeta (não o Indigo de _fixed_roles, que
        # também pinta ACCENT_INCOME/botão de Receita) — escolhido pra ter contraste bom sem
        # precisar do contorno preto (ver ADR-0042/OutlinedLabel) nas duas categorias: mesmo tom
        # nas fatias do gráfico em qualquer tema, e no texto pequeno da lista no modo claro;
        # variante mais clara (pastel) só pro texto pequeno no modo escuro.
        "INVESTMENT_CATEGORY_COLOR": _PRIZMO_INVESTMENT_CATEGORY_COLOR,
        "INVESTMENT_CATEGORY_LABEL_LIGHT_TEXT": _PRIZMO_INVESTMENT_CATEGORY_COLOR,
        "INVESTMENT_CATEGORY_LABEL_DARK_TEXT": _PRIZMO_INVESTMENT_CATEGORY_LABEL_DARK_TEXT,
        # Contorno preto nas letras da coluna Categoria (ver ADR-0042) — mantido pra Essencial/
        # Lazer/Ativa neste perfil (campo POR PERFIL desde a ADR-0049: ver `Roze Quartz`, que
        # desliga pras 5 — contra fundo pastel, o contorno atrapalha a leitura em vez de ajudar).
        "CATEGORY_NO_OUTLINE": list(_FALLBACK_CATEGORY_NO_OUTLINE),
    })
    return palette


def _expand_simple_profile(fields: dict) -> dict:
    """Papéis fixos + os 4 campos de um perfil "simple" esticados pros papéis estruturais.
    Cada campo é uma cor só (não par claro/escuro) — um perfil "simple" fica com a mesma cor
    estrutural nos dois temas de propósito (é a simplificação que o usuário pediu: quem achar o
    visual padrão colorido/complexo demais ganha um perfil só com 4 cores, sem precisar acertar
    uma versão clara E escura de cada uma)."""
    palette = _fixed_roles()
    primary = fields["primary"]
    secondary = fields["secondary"]
    tertiary = fields["tertiary"]
    static_text = fields["static_text"]
    palette.update({
        "BG_APP": (primary, primary),
        "BG_SURFACE": (secondary, secondary),
        "BG_PANEL_BLUE": (secondary, secondary),
        "TEXT_PRIMARY": (static_text, static_text),
        "BORDER_NEUTRAL": (tertiary, tertiary),
        "BORDER_ACCENT": tertiary,
        "STATUS_BADGE_BORDER": (tertiary, tertiary),
        "ROW_SEPARATOR": tertiary,
        # Cor de Investimento/Passiva (ver ADR-0047) — um perfil "simple" novo não tem campo
        # próprio pra isso (só os 4 de sempre), cai no mesmo rosa que todo perfil usava antes
        # dessa cor virar por-perfil (Roze Quartz também usa esse valor, ver `color_profiles.py`).
        "INVESTMENT_CATEGORY_COLOR": _FALLBACK_INVESTMENT_CATEGORY_COLOR,
        "INVESTMENT_CATEGORY_LABEL_LIGHT_TEXT": _FALLBACK_INVESTMENT_CATEGORY_COLOR,
        "INVESTMENT_CATEGORY_LABEL_DARK_TEXT": _FALLBACK_INVESTMENT_CATEGORY_LABEL_DARK_TEXT,
    })
    return palette


_active_profile_name: str | None = None


def available_profiles() -> list[str]:
    return color_profiles.list_profiles()


def current_profile() -> str:
    return _active_profile_name


def apply_profile(name: str | None = None) -> None:
    """Troca o perfil de cor ativo — recalcula CATEGORY_COLORS e empurra tudo pro nível de
    módulo, então `theme.CONSTANTE` em qualquer arquivo já lê o valor novo na próxima vez que
    for usado (não precisa reimportar nada). `name=None` usa o perfil ativo salvo em
    `color_profiles.json` (chamado assim uma vez, na primeira importação deste módulo).
    Widgets já construídos não recolorem sozinhos ao trocar de PERFIL (só ao trocar claro/escuro,
    que o CustomTkinter trata nativamente) — quem troca de perfil em runtime precisa também
    reconstruir a UI (ver `IteradorApp.rebuild_ui`)."""
    global _active_profile_name
    if name is None:
        name = color_profiles.get_active_profile_name()

    profile = color_profiles.get_profile(name)
    mode = profile.get("mode")
    if mode == "simple":
        palette = _expand_simple_profile(profile)
    else:
        palette = {k: v for k, v in profile.items() if k != "mode"}

    # Cor de cada categoria de transação (ver ADR-0014) — Essencial (vermelho), Lazer (verde),
    # Ativa (verde) são fixas em qualquer perfil (ver módulo docstring). Investimento/Passiva
    # (não é coincidência, são as duas categorias ligadas a um investimento) são a ÚNICA
    # exceção: viram um campo POR PERFIL desde a ADR-0047 (antes vinham de uma constante global
    # — mudar a cor pro perfil Roze Quartz mudava também o Prizmo_V1 sem querer, relato do
    # usuário). `.get(..., fallback)` protege perfis "detailed" já persistidos em disco antes
    # desses campos existirem (ver `color_profiles._backfill_investment_category_fields`, mas
    # a UI não deveria depender só do backfill pra não quebrar). Usada tanto no texto da coluna
    # Categoria da lista quanto nas fatias do gráfico de consumo — mesma cor nos dois, de
    # propósito (legenda visual consistente, ver ADR-0029/0043).
    # Par claro/escuro pra texto (valor da coluna Valor, cards "Receitas/Despesas do mês", "Fim
    # do mês", "Saldo atual", e a coluna Categoria em Ativa/Lazer/Essencial logo abaixo) —
    # calculado antes de `CATEGORY_LABEL_COLORS` pra poder ser reaproveitado lá. Separado de
    # `VALUE_INCOME`/`VALUE_EXPENSE` (que continuam cor única nos dois temas: preenchem
    # `CATEGORY_COLORS`, a fatia do gráfico de consumo, e o fundo do badge "Pago"/"A pagar",
    # nenhum desses lugares pode variar por tema sem quebrar contraste com o texto preto fixo do
    # badge ou mudar a cor do gráfico entre temas). Perfil sem campo próprio cai na cor única de
    # sempre nos dois temas (sem mudança de comportamento).
    palette["VALUE_INCOME_TEXT"] = tuple(
        palette.get("VALUE_INCOME_TEXT", (palette["VALUE_INCOME"], palette["VALUE_INCOME"])))
    palette["VALUE_EXPENSE_TEXT"] = tuple(
        palette.get("VALUE_EXPENSE_TEXT", (palette["VALUE_EXPENSE"], palette["VALUE_EXPENSE"])))

    investment_color = palette.get("INVESTMENT_CATEGORY_COLOR", _FALLBACK_INVESTMENT_CATEGORY_COLOR)
    palette["CATEGORY_COLORS"] = {
        "Essencial": palette["VALUE_EXPENSE"],
        "Lazer": palette["VALUE_INCOME"],
        "Investimento": investment_color,
        "Ativa": palette["VALUE_INCOME"],
        "Passiva": investment_color,
        # "Necessário" era o nome de "Essencial" antes da ADR-0014 — quem já tinha lançamentos
        # criados com o nome antigo (categoria já existente no banco, não migrada) continua
        # vendo "Necessário" no texto, mas pelo menos com a cor certa em vez de cair no branco
        # de fallback (relato do usuário).
        "Necessário": palette["VALUE_EXPENSE"],
    }
    # Variante clara/escura só pro **texto** da coluna Categoria na lista (mais escura no claro,
    # mais clara/pastel no escuro) — o gráfico de consumo continua com a cor normal (mesma) nos
    # dois temas (`CATEGORY_COLORS` acima, ver ADR-0029/0043). Junto com `CATEGORY_NO_OUTLINE`
    # abaixo (sem contorno preto nessas duas, ver ADR-0042/0047), é a cor quem precisa garantir
    # o contraste sozinha agora.
    palette["CATEGORY_LABEL_COLORS"] = {
        "Investimento": (
            palette.get("INVESTMENT_CATEGORY_LABEL_LIGHT_TEXT", _FALLBACK_INVESTMENT_CATEGORY_COLOR),
            palette.get("INVESTMENT_CATEGORY_LABEL_DARK_TEXT", _FALLBACK_INVESTMENT_CATEGORY_LABEL_DARK_TEXT)),
        "Passiva": (
            palette.get("INVESTMENT_CATEGORY_LABEL_LIGHT_TEXT", _FALLBACK_INVESTMENT_CATEGORY_COLOR),
            palette.get("INVESTMENT_CATEGORY_LABEL_DARK_TEXT", _FALLBACK_INVESTMENT_CATEGORY_LABEL_DARK_TEXT)),
        # Mesmo par claro/escuro do valor da coluna Valor (`VALUE_INCOME_TEXT` acima) — Ativa/
        # Lazer usam a cor de `CATEGORY_COLORS` (única, mesma dos dois temas) por padrão; perfil
        # com `VALUE_INCOME_TEXT` próprio (Roze Quartz) também melhora a legibilidade aqui.
        "Ativa": palette["VALUE_INCOME_TEXT"],
        "Lazer": palette["VALUE_INCOME_TEXT"],
    }
    # Quais categorias NÃO levam o contorno preto da coluna Categoria (ver ADR-0042) — campo por
    # perfil desde a ADR-0049 (mesmo padrão da cor de Investimento/Passiva acima, ADR-0047):
    # `Roze Quartz` desliga o contorno de todas as 5 (contra o fundo pastel desse perfil, o
    # contorno atrapalha a leitura em vez de ajudar), `Prizmo_V1` continua só com
    # Investimento/Passiva. Perfil "simple"/qualquer "detailed" sem o campo cai no de sempre.
    palette["CATEGORY_NO_OUTLINE"] = set(
        palette.get("CATEGORY_NO_OUTLINE", _FALLBACK_CATEGORY_NO_OUTLINE))

    globals().update(palette)
    _active_profile_name = name


# Cor de Investimento/Passiva do perfil Prizmo_V1 (ver ADR-0047) — roxo/violeta, não o Indigo de
# `_fixed_roles()` (que também pinta ACCENT_INCOME/botão de Receita). Substituiu o rosa da
# ADR-0043 nesse perfil especificamente: pro usuário, aquele rosa "não lia como roxo" — esse tom
# foi escolhido por ter contraste suficiente pra dispensar o contorno preto (ver
# `CATEGORY_NO_OUTLINE`/OutlinedLabel) nos dois temas, sem cair na faixa magenta/rosa que
# motivou a troca original. Só usado dentro de `snapshot_default_palette()`.
_PRIZMO_INVESTMENT_CATEGORY_COLOR = "#7C3AED"
_PRIZMO_INVESTMENT_CATEGORY_LABEL_DARK_TEXT = "#C4B5FD"

# Fallback pra perfil "simple" novo (sem campo próprio pra isso) e pra qualquer perfil
# "detailed" que ainda não tenha os 3 campos novos (ver `.get()` em `apply_profile()` acima) —
# mesmo rosa que Roze Quartz usa (ver `color_profiles._seed_roze_quartz_profile`) e que TODO
# perfil usava antes da ADR-0047 (era a constante global `_CATEGORY_INVESTMENT_ROSE`, ver
# ADR-0043).
_FALLBACK_INVESTMENT_CATEGORY_COLOR = "#C2185B"
_FALLBACK_INVESTMENT_CATEGORY_LABEL_DARK_TEXT = "#F48FB1"

# Investimento/Passiva sem contorno preto (ver ADR-0042/0047) — a cor sozinha (mais o texto
# claro/escuro acima) já garante contraste suficiente; o contorno só deixava as letras mais
# grossas/difíceis de ler sem ganhar legibilidade real. Fallback pra perfil
# "simple" novo (sem campo próprio pra isso, ver `_expand_simple_profile`) e pra qualquer perfil
# "detailed" que ainda não tenha o campo (ver `.get()` em `apply_profile()`) — mesmo conjunto que
# TODO perfil usava antes de virar campo por perfil (ADR-0049, mesmo motivo/padrão da ADR-0047
# pra `INVESTMENT_CATEGORY_COLOR`: perfil Roze Quartz precisava desligar o contorno de TODAS as
# categorias sem afetar `Prizmo_V1`, que só desliga em Investimento/Passiva).
_FALLBACK_CATEGORY_NO_OUTLINE = {"Investimento", "Passiva"}

# Paleta pra categorias personalizadas (ver ADR-0028) — sem cor fixa própria, escolhida na hora
# por `category_color()`. 8 tons espaçados por matiz (HSL, S=65%/L=58%), evitando de propósito
# as faixas de matiz já usadas pelas cores fixas: vermelho/laranja (Essencial/destaque), verde
# (Lazer/Ativa) e rosa/magenta (Investimento/Passiva no perfil padrão pré-ADR-0047, ver
# `_FALLBACK_INVESTMENT_CATEGORY_COLOR` acima) — pra uma categoria nova nunca parecer "a mesma
# cor" de uma das 5 fixas. Fixa (não muda com o perfil de
# cor) — categoria não é uma cor de interface, é um rótulo de dado, igual `CATEGORY_COLORS`.
_AUTO_CATEGORY_PALETTE = [
    "#51D6AA", "#51D6D1", "#51B2D6", "#518BD6", "#5163D6", "#D651CB", "#D651AE", "#D65193",
]


def category_color(category_name: str) -> str:
    """Cor da categoria (mesma no texto da lista, nas fatias do gráfico de consumo e na linha do
    comparativo mensal, ver ADR-0029/0030) — ver `category_label_color()` pra a variante usada só
    no texto da lista, com roxo mais claro no modo escuro pra Investimento/Passiva. Categoria
    sem cor fixa (qualquer personalizada, ver ADR-0028) usa a cor guardada em
    `custom_categories.json` (escolhida pelo usuário na criação/edição, ver ADR-0030). Só cai no
    hash determinístico de `_AUTO_CATEGORY_PALETTE` como último recurso (categoria personalizada
    sem cor guardada por algum motivo — não deveria acontecer depois da ADR-0030, mas evita
    KeyError em vez de confiar que todo registro sempre vai ter o campo)."""
    fixed = CATEGORY_COLORS.get(category_name)
    if fixed is not None:
        return fixed
    for entry in custom_categories.list_custom_categories():
        if entry["name"] == category_name and entry.get("color"):
            return entry["color"]
    index = sum(category_name.encode("utf-8")) % len(_AUTO_CATEGORY_PALETTE)
    return _AUTO_CATEGORY_PALETTE[index]


def category_label_color(category_name: str) -> str:
    """Como `category_color()`, mas com roxo mais claro no modo escuro pra Investimento/Passiva
    — só pra texto pequeno (coluna Categoria da lista de lançamentos), onde Indigo normal tinha
    pouca visibilidade. Não usar no gráfico de consumo (esse continua com `category_color()`)."""
    variant = CATEGORY_LABEL_COLORS.get(category_name)
    if variant is not None:
        return variant[1] if ctk.get_appearance_mode() == "Dark" else variant[0]
    return category_color(category_name)


def shade_color(hex_color: str, amount: float) -> str:
    """Clareia (`amount` > 0) ou escurece (`amount` < 0) uma cor hex, mantendo o mesmo tom —
    usado pro hover do botão Pago/A pagar refletir a cor atual do status em vez de uma cor fixa
    (ex. laranja de A pagar fica um laranja diferente ao passar o mouse, verde de Pago fica um
    verde diferente), em vez de um hover genérico igual pra qualquer estado."""
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    if amount >= 0:
        r, g, b = (c + (255 - c) * amount for c in (r, g, b))
    else:
        r, g, b = (c * (1 + amount) for c in (r, g, b))
    return f"#{int(max(0, min(255, r))):02X}{int(max(0, min(255, g))):02X}{int(max(0, min(255, b))):02X}"


def outline_button_style(strong_border: bool = False) -> dict:
    """kwargs pra um CTkButton de contorno: fundo transparente, borda fina em BORDER_ACCENT,
    cantos bem arredondados (ver ADR-0020) — usado em ações secundárias de cabeçalho (Desfazer/
    Refazer). Um só lugar pra mudar a cor/espessura dessa borda em todo o app.

    `strong_border=True` — reforço de contraste neutro (preto no claro, quase-branco no escuro)
    em vez do azul de destaque, mais texto em negrito (ver ADR-0029, relato do usuário: borda e
    texto pouco visíveis em "Perfis de cor" no modo claro). `CTkButton` só aceita 1 par borda/cor
    (confirmado lendo o código do customtkinter) — não dá pra "empilhar" duas bordas, então isso
    SUBSTITUI `BORDER_ACCENT` nesses botões em vez de somar a ela. Usar só onde o contraste for
    reportado como problema — o resto do app mantém a borda de destaque padrão."""
    style = {
        "fg_color": "transparent",
        "border_width": 1,
        "border_color": BORDER_ACCENT,
        "corner_radius": 10,
        "text_color": TEXT_PRIMARY,
        "hover_color": BG_SURFACE,
    }
    if strong_border:
        style["border_color"] = (CARBON_BLACK, TEXT_ON_BLACK)
        style["font"] = ctk.CTkFont(weight="bold")
    return style


APPEARANCE_MODES = ("dark", "light")
DEFAULT_APPEARANCE_MODE = "dark"

# Escala geral da interface (ver ADR-0044) — mesma ideia de "UI scale" do Blender/AutoCAD/
# navegadores: um fator só que a CustomTkinter já aplica em cima de toda largura/altura/fonte de
# widget (`ctk.set_widget_scaling()`), sem precisar reconstruir nada (diferente de trocar de
# perfil de cor, ver ADR-0025) — CTk já registra um callback de reescala por widget construído.
UI_SCALE_OPTIONS = (0.9, 1.0, 1.1, 1.25, 1.5)
DEFAULT_UI_SCALE = 1.0

# Fonte "quadrada" para o logo/título "Iterador" (letras de largura uniforme, visual mais
# geométrico/blocado). Não há uma fonte chamada literalmente "Square" instalada no sistema —
# DejaVu Sans Mono é a opção monoespaçada real disponível que se aproxima disso. Troque aqui se
# quiser instalar uma fonte display mais específica (ex. Bank Gothic, Eurostile, Orbitron).
HEADING_FONT_FAMILY = "DejaVu Sans Mono"


apply_profile()
