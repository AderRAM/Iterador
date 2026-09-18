"""Logo customizado da Sidebar — usuário pode enviar uma imagem própria pra aparecer acima do
mosaico "Iterador" (`widgets/triangle_heading.py`). Ver
Guide/decisions/0038-custom-sidebar-logo-size.md.

Processado uma vez, no momento do envio (não a cada exibição): a imagem enviada (PNG/JPEG/BMP/
GIF, qualquer formato que o Pillow lê) é ajustada mantendo proporção pra caber em
`LOGO_SIZE` com uma borda preta ao redor, e sempre salva como PNG em
`~/.iterador/sidebar_logo.png` — arquivo próprio, nunca `~/.iterador/iterador.db` (mesmo padrão
de `preferences.py`/`color_profiles.py`), nunca em `UI/assets/` (aquilo é asset do app, não dado
do usuário). A existência do arquivo já É o estado: existe = usa a imagem custom, não existe =
usa o mosaico padrão — não precisa de nenhum JSON de flag.

Se o usuário nunca enviou uma imagem própria, a Sidebar mostra uma imagem padrão embutida no
instalador: `UI/assets/Atlas.<extensão>` (nome fixo "Atlas", qualquer extensão que o Pillow leia
— busca por `Atlas.*`, sem depender de um formato específico). Ela é emoldurada na hora, a cada
exibição (nunca gravada em disco — `assets/` é read-only, é o pacote do app, não dado do
usuário), com a mesma moldura da imagem custom, pra ficar visualmente idêntica.
"""

from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from iterador_ui import theme

_LOGO_PATH = Path.home() / ".iterador" / "sidebar_logo.png"
_ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
_DEFAULT_LOGO_NAME = "atlas"

# Maior possível sem encostar na borda da Sidebar (ver ADR-0040): Sidebar tem 180px de largura
# TRAVADA (`pack_propagate(False)` em sidebar.py — sem isso a Sidebar crescia sozinha pra caber
# a imagem, e "não encostar na borda" não era uma restrição de verdade) com borda de 1px de cada
# lado (interior = 178px); 2px de respiro de cada lado (o mínimo real pra não encostar) dá
# 178 - 4 = 174px de largura máxima segura. Altura bem maior que os 44px do TriangleHeading
# original — mais espaço pra imagem enviada preservar mais resolução em vez de ficar espremida.
LOGO_SIZE = (174, 130)  # público — sidebar.py usa pra exibir sem duplicar o número
_BORDER_PX = 4


class SidebarImageError(ValueError):
    """Erro de uso da API de logo customizado (arquivo inválido/corrompido, etc.) — mensagem já
    pronta pra mostrar ao usuário num diálogo."""


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    return tuple(int(hex_color[i:i + 2], 16) for i in (1, 3, 5))


def get_logo_path() -> Path | None:
    return _LOGO_PATH if _LOGO_PATH.exists() else None


def has_bundled_default() -> bool:
    """Usado só por `settings_view.py` pra distinguir, no texto de status, se a Sidebar (sem
    imagem custom do usuário) está mostrando a imagem padrão embutida ou só o mosaico."""
    return _find_default_logo_source() is not None


def _find_default_logo_source() -> Path | None:
    if not _ASSETS_DIR.is_dir():
        return None
    for entry in sorted(_ASSETS_DIR.iterdir()):
        if entry.is_file() and entry.stem.lower() == _DEFAULT_LOGO_NAME:
            return entry
    return None


def _frame_logo(source: Image.Image) -> Image.Image:
    border_color = _hex_to_rgb(theme.CARBON_BLACK)
    inner_size = (LOGO_SIZE[0] - 2 * _BORDER_PX, LOGO_SIZE[1] - 2 * _BORDER_PX)
    fitted = ImageOps.contain(source.convert("RGB"), inner_size)
    padded = ImageOps.pad(fitted, inner_size, color=border_color)
    return ImageOps.expand(padded, border=_BORDER_PX, fill=border_color)


def get_display_image() -> Image.Image | None:
    """Imagem pronta pra exibir na Sidebar (`widgets/sidebar.py`): a enviada pelo usuário se
    existir, senão a padrão embutida em assets/ (`Atlas.*`), senão nenhuma (só o mosaico)."""
    if _LOGO_PATH.exists():
        try:
            return Image.open(_LOGO_PATH)
        except (OSError, UnidentifiedImageError):
            return None

    default_source = _find_default_logo_source()
    if default_source is None:
        return None
    try:
        source = Image.open(default_source)
        source.load()
    except (OSError, UnidentifiedImageError):
        return None
    return _frame_logo(source)


def set_custom_logo(source_path: str) -> None:
    try:
        source = Image.open(source_path)
        source.load()
    except (OSError, UnidentifiedImageError) as exc:
        raise SidebarImageError(f"Não foi possível abrir essa imagem: {exc}") from exc

    framed = _frame_logo(source)
    _LOGO_PATH.parent.mkdir(parents=True, exist_ok=True)
    framed.save(_LOGO_PATH, format="PNG")


def remove_custom_logo() -> None:
    _LOGO_PATH.unlink(missing_ok=True)
