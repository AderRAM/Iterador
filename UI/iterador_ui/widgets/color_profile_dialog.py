"""Diálogo de criar/editar um perfil de cor "simple" — 4 campos (texto estático, primária,
secundária, terciária), cada um com um botão-amostra que abre `ColorPickerDialog` (seletor de cor
estilizado em CTk, ver ADR-0029 — antes era `tkinter.colorchooser.askcolor()`, o nativo do
sistema, que destoava visualmente do resto do app). Ver
Guide/decisions/0025-color-profile-management.md.

Só perfis "simple" são editáveis por aqui — um perfil "detailed" (`Prizmo_V1`) tem ~30 campos
independentes, fora do escopo desta tela (só dá pra renomear/remover ele, ver `SettingsView`).
"""

import customtkinter as ctk

from iterador_ui import color_profiles, theme
from iterador_ui.widgets.color_picker_dialog import ColorPickerDialog
from iterador_ui.widgets.dialog_utils import make_modal, open_singleton

_FIELDS = [
    ("static_text", "Texto estático (títulos, rótulos)"),
    ("primary", "Primária (fundo do app)"),
    ("secondary", "Secundária (fundo de painel/card)"),
    ("tertiary", "Terciária (borda/separador)"),
]

_DEFAULTS = {
    "static_text": "#EAEAEA",
    "primary": "#1A1A1A",
    "secondary": "#242424",
    "tertiary": "#3B82F6",
}


class ColorProfileDialog(ctk.CTkToplevel):
    def __init__(self, master, on_saved, profile_name: str | None = None):
        super().__init__(master)
        self._on_saved = on_saved
        self._profile_name = profile_name
        is_edit = profile_name is not None

        self.title("Editar perfil" if is_edit else "Novo perfil de cor")
        self.geometry("380x420")
        self.configure(fg_color=theme.BG_APP)
        make_modal(self, master)

        current_fields = {}
        if is_edit:
            profile = color_profiles.get_profile(profile_name)
            current_fields = {k: profile[k] for k in color_profiles.SIMPLE_FIELDS}

        ctk.CTkLabel(self, text="Nome do perfil", text_color=theme.TEXT_PRIMARY).pack(
            anchor="w", padx=20, pady=(20, 4))
        self._name_entry = ctk.CTkEntry(
            self, placeholder_text="ex. Modo calmo", border_width=1,
            border_color=theme.CARBON_BLACK)
        if is_edit:
            self._name_entry.insert(0, profile_name)
        self._name_entry.pack(fill="x", padx=20)

        self._color_values: dict[str, str] = {}
        self._color_buttons: dict[str, ctk.CTkButton] = {}
        for field_key, label in _FIELDS:
            row = ctk.CTkFrame(self, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=(14, 0))
            ctk.CTkLabel(row, text=label, text_color=theme.TEXT_PRIMARY, wraplength=220,
                         justify="left", anchor="w").pack(side="left", fill="x", expand=True)
            initial = current_fields.get(field_key, _DEFAULTS[field_key])
            self._color_values[field_key] = initial
            button = ctk.CTkButton(
                row, text="", width=44, height=24, fg_color=initial, border_width=1,
                border_color=theme.TEXT_PRIMARY,
                command=lambda k=field_key: self._pick_color(k))
            button.pack(side="right")
            self._color_buttons[field_key] = button

        self._error_label = ctk.CTkLabel(self, text="", text_color=theme.ACCENT_EXPENSE)
        self._error_label.pack(anchor="w", padx=20, pady=(12, 0))

        ctk.CTkButton(
            self, text="Salvar", fg_color=theme.ACCENT_EXPENSE, command=self._submit,
        ).pack(fill="x", padx=20, pady=(16, 20))

    def _pick_color(self, field_key: str) -> None:
        open_singleton(self, "_color_picker_dialog", lambda: ColorPickerDialog(
            self, initial_color=self._color_values[field_key],
            on_pick=lambda hex_color: self._apply_picked_color(field_key, hex_color)))

    def _apply_picked_color(self, field_key: str, hex_color: str) -> None:
        self._color_values[field_key] = hex_color
        self._color_buttons[field_key].configure(fg_color=hex_color)

    def _submit(self) -> None:
        name = self._name_entry.get().strip()
        if not name:
            self._error_label.configure(text="Informe um nome pro perfil.")
            return

        try:
            if self._profile_name is not None:
                if name != self._profile_name:
                    color_profiles.rename_profile(self._profile_name, name)
                color_profiles.update_profile(name, self._color_values)
            else:
                color_profiles.create_profile(name, self._color_values)
        except color_profiles.ProfileError as exc:
            self._error_label.configure(text=str(exc))
            return

        self._on_saved(name)
        self.destroy()


class RenameProfileDialog(ctk.CTkToplevel):
    """Renomear funciona pra qualquer perfil (inclusive "detailed" como `Prizmo_V1`) — separado
    de `ColorProfileDialog` porque esse exige os 4 campos de cor, que um perfil "detailed" não
    tem nesse formato."""

    def __init__(self, master, profile_name: str, on_renamed):
        super().__init__(master)
        self._profile_name = profile_name
        self._on_renamed = on_renamed

        self.title("Renomear perfil")
        self.geometry("300x160")
        self.configure(fg_color=theme.BG_APP)
        make_modal(self, master)

        ctk.CTkLabel(self, text="Novo nome", text_color=theme.TEXT_PRIMARY).pack(
            anchor="w", padx=20, pady=(20, 4))
        self._name_entry = ctk.CTkEntry(
            self, border_width=1, border_color=theme.CARBON_BLACK)
        self._name_entry.insert(0, profile_name)
        self._name_entry.pack(fill="x", padx=20)
        self._name_entry.bind("<Return>", lambda _event: self._submit())

        self._error_label = ctk.CTkLabel(self, text="", text_color=theme.ACCENT_EXPENSE)
        self._error_label.pack(anchor="w", padx=20, pady=(8, 0))

        ctk.CTkButton(
            self, text="Renomear", fg_color=theme.ACCENT_EXPENSE, command=self._submit,
        ).pack(fill="x", padx=20, pady=(16, 20))

    def _submit(self) -> None:
        new_name = self._name_entry.get().strip()
        if not new_name:
            self._error_label.configure(text="Informe um nome.")
            return
        try:
            color_profiles.rename_profile(self._profile_name, new_name)
        except color_profiles.ProfileError as exc:
            self._error_label.configure(text=str(exc))
            return
        self._on_renamed(self._profile_name, new_name)
        self.destroy()
