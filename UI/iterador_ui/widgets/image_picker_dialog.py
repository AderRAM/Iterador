"""Diálogo de escolher imagem modernizado (widgets CTk) — usado por `SettingsView` pra trocar a
imagem da barra lateral (ver ADR-0036/sidebar_image.py). Antes abria o seletor de arquivo nativo
do sistema (`tkinter.filedialog.askopenfilename()`) — visualmente destoava do resto do app
(janela cinza fora do tema claro/escuro, mesmo motivo do `ColorPickerDialog`, ver ADR-0029).

Layout segue de propósito o do seletor nativo: linha
"Diretório" com botão de subir, lista de pastas/imagens da pasta atual, linha "Nome do arquivo"
com campo de texto DE VERDADE editável (dá pra colar/digitar um caminho direto, não só clicar na
lista) + botão "Abrir", e "Cancelar" por baixo. A única coisa que o nativo não tinha e ficou aqui
é a prévia da imagem escolhida antes de confirmar.
"""

from pathlib import Path

import customtkinter as ctk
from PIL import Image, ImageOps, UnidentifiedImageError

from iterador_ui import theme
from iterador_ui.widgets.dialog_utils import make_modal

_PREVIEW_SIZE = (260, 140)
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif"}


def _default_start_dir() -> Path:
    pictures = Path.home() / "Pictures"
    return pictures if pictures.is_dir() else Path.home()


class ImagePickerDialog(ctk.CTkToplevel):
    def __init__(self, master, on_pick, title: str = "Escolher imagem",
                 start_dir: str | None = None):
        super().__init__(master)
        self._on_pick = on_pick
        self._path: str | None = None
        self._preview_image: ctk.CTkImage | None = None
        self._current_dir = Path(start_dir) if start_dir else _default_start_dir()

        self.title(title)
        self.geometry("420x580")
        self.configure(fg_color=theme.BG_APP)
        make_modal(self, master)

        nav_row = ctk.CTkFrame(self, fg_color="transparent")
        nav_row.pack(fill="x", padx=20, pady=(20, 0))
        ctk.CTkButton(
            nav_row, text="⬆", width=32, command=self._go_up,
            **theme.outline_button_style(),
        ).pack(side="left")
        self._dir_label = ctk.CTkLabel(
            nav_row, text="", text_color=theme.TEXT_PRIMARY, anchor="w")
        self._dir_label.pack(side="left", fill="x", expand=True, padx=(8, 0))

        # Lista de pastas (entra ao clicar) + imagens (seleciona ao clicar) da pasta atual —
        # substitui a árvore de navegação do seletor nativo, mais simples mas o bastante pra
        # achar um arquivo (mesmo raciocínio de escopo do `ColorPickerDialog`: não reimplementar
        # o seletor nativo inteiro, só a parte usada de verdade).
        self._list_frame = ctk.CTkScrollableFrame(
            self, fg_color=theme.BG_SURFACE, corner_radius=8, border_width=1,
            border_color=theme.CARBON_BLACK, height=170)
        self._list_frame.pack(fill="both", expand=True, padx=20, pady=(10, 0))

        # "Nome do arquivo" — campo de texto DE VERDADE (editável, não só um display do que foi
        # clicado na lista) + "Abrir": digitar/colar um caminho e apertar Enter (ou clicar
        # "Abrir") funciona sem precisar navegar a lista, igual o nativo.
        filename_row = ctk.CTkFrame(self, fg_color="transparent")
        filename_row.pack(fill="x", padx=20, pady=(12, 0))
        ctk.CTkLabel(
            filename_row, text="Nome do arquivo:", text_color=theme.TEXT_PRIMARY,
        ).pack(side="left")
        self._path_entry = ctk.CTkEntry(filename_row, placeholder_text="ex. foto.png")
        self._path_entry.pack(side="left", fill="x", expand=True, padx=(8, 8))
        self._path_entry.bind("<Return>", self._on_entry_confirm)
        ctk.CTkButton(
            filename_row, text="Abrir", width=72, command=self._submit,
            **theme.outline_button_style(strong_border=True),
        ).pack(side="left")

        self._preview_frame = ctk.CTkFrame(
            self, fg_color=theme.BG_SURFACE, corner_radius=8, border_width=1,
            border_color=theme.CARBON_BLACK, height=_PREVIEW_SIZE[1] + 24)
        self._preview_frame.pack(fill="x", padx=20, pady=(12, 0))
        self._preview_frame.pack_propagate(False)
        self._preview_label = ctk.CTkLabel(
            self._preview_frame, text="Prévia aparece aqui depois de escolher um arquivo",
            text_color=theme.TEXT_PRIMARY, wraplength=260)
        self._preview_label.pack(expand=True)

        self._error_label = ctk.CTkLabel(self, text="", text_color=theme.ACCENT_EXPENSE)
        self._error_label.pack(anchor="w", padx=20, pady=(8, 0))

        ctk.CTkButton(
            self, text="Cancelar", fg_color="transparent", border_width=1,
            border_color=theme.BORDER_ACCENT, text_color=theme.TEXT_PRIMARY,
            command=self.destroy,
        ).pack(fill="x", padx=20, pady=(16, 20))

        self._refresh_listing()

    def _go_up(self) -> None:
        parent = self._current_dir.parent
        if parent != self._current_dir:
            self._current_dir = parent
            self._refresh_listing()

    def _enter_dir(self, path: Path) -> None:
        self._current_dir = path
        self._error_label.configure(text="")
        self._refresh_listing()

    def _refresh_listing(self) -> None:
        for child in self._list_frame.winfo_children():
            child.destroy()
        self._dir_label.configure(text=str(self._current_dir))

        try:
            # Pastas primeiro, depois imagens, cada grupo em ordem alfabética (case-insensitive)
            # — ordem previsível, igual qualquer navegador de arquivo.
            entries = sorted(
                self._current_dir.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except OSError as exc:
            ctk.CTkLabel(
                self._list_frame, text=f"Não foi possível abrir essa pasta: {exc}",
                text_color=theme.ACCENT_EXPENSE, wraplength=340,
            ).pack(anchor="w", pady=4, padx=4)
            return

        shown = 0
        for entry in entries:
            if entry.name.startswith("."):
                continue  # oculta arquivos/pastas ocultos, igual navegador nativo por padrão
            if entry.is_dir():
                self._add_row("\U0001F4C1", entry.name, lambda e=entry: self._enter_dir(e))
                shown += 1
            elif entry.suffix.lower() in _IMAGE_EXTENSIONS:
                self._add_row("\U0001F5BC", entry.name, lambda e=entry: self._select_file(e))
                shown += 1

        if shown == 0:
            ctk.CTkLabel(
                self._list_frame, text="Pasta vazia (sem subpastas ou imagens).",
                text_color=theme.TEXT_PRIMARY,
            ).pack(anchor="w", pady=4, padx=4)

    def _add_row(self, icon: str, name: str, command) -> None:
        ctk.CTkButton(
            self._list_frame, text=f"{icon}  {name}", anchor="w", fg_color="transparent",
            hover_color=theme.BG_APP, text_color=theme.TEXT_PRIMARY, command=command,
        ).pack(fill="x", pady=1)

    def _select_file(self, path: Path) -> None:
        # Clicar um item da lista só seleciona/mostra prévia (mesmo comportamento de clique
        # único no seletor nativo) — só fecha o diálogo quando "Abrir"/Enter confirma de vez.
        self._path_entry.delete(0, "end")
        self._path_entry.insert(0, path.name)
        self._load_preview(str(path))

    def _resolve_entry_path(self) -> Path | None:
        raw = self._path_entry.get().strip()
        if not raw:
            return None
        candidate = Path(raw).expanduser()
        if not candidate.is_absolute():
            candidate = self._current_dir / candidate
        return candidate

    def _on_entry_confirm(self, _event=None) -> None:
        """Enter no campo "Nome do arquivo" — navega se for pasta, senão só seleciona/mostra
        prévia (não fecha o diálogo sozinho, mesma semântica de clicar um item da lista)."""
        candidate = self._resolve_entry_path()
        if candidate is None:
            return
        if candidate.is_dir():
            self._enter_dir(candidate)
            return
        self._load_preview(str(candidate))

    def _load_preview(self, path: str) -> bool:
        try:
            source = Image.open(path)
            source.load()
        except (OSError, UnidentifiedImageError) as exc:
            self._error_label.configure(text=f"Não foi possível abrir essa imagem: {exc}")
            return False

        self._error_label.configure(text="")
        self._path = path

        fitted = ImageOps.contain(source.convert("RGB"), _PREVIEW_SIZE)
        self._preview_image = ctk.CTkImage(fitted, size=fitted.size)
        self._preview_label.configure(image=self._preview_image, text="")
        return True

    def _submit(self) -> None:
        """Botão "Abrir" — resolve o que estiver no campo "Nome do arquivo" primeiro (cobre
        digitar um caminho e clicar "Abrir" direto, sem passar por Enter/clique na lista antes),
        depois confirma e fecha só se sobrar um arquivo de imagem válido selecionado. Se o
        caminho digitado for inválido, para aqui (erro já mostrado por `_load_preview`) — nunca
        cai pra confirmar uma seleção antiga/desatualizada em silêncio."""
        candidate = self._resolve_entry_path()
        if candidate is not None and str(candidate) != self._path:
            if candidate.is_dir():
                self._enter_dir(candidate)
                return
            if not candidate.exists():
                self._error_label.configure(text="Arquivo não encontrado.")
                return
            if not self._load_preview(str(candidate)):
                return

        if self._path is None:
            self._error_label.configure(text="Escolha um arquivo de imagem.")
            return
        self._on_pick(self._path)
        self.destroy()
