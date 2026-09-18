"""Seletor de cor modernizado (widgets CTk) — substitui `tkinter.colorchooser.askcolor()`, o
seletor nativo do sistema, que visualmente destoa do resto do app (janela cinza fora do tema
claro/escuro, ver ADR-0029). Mesmo layout conceitual do nativo — 3 controles R/G/B, campo de hex,
preview, OK/Cancelar — só que estilizado como o resto do Iterador.

Sliders e campo de hex ficam sincronizados nos dois sentidos (`_updating` trava reentrância):
mexer no slider atualiza o campo de hex e o preview; digitar um hex válido (Enter ou perder o
foco) atualiza os sliders e o preview.
"""

import customtkinter as ctk

from iterador_ui import theme
from iterador_ui.widgets.dialog_utils import make_modal

_CHANNELS = [("Vermelho", "r"), ("Verde", "g"), ("Azul", "b")]


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.strip().lstrip("#")
    if len(hex_color) != 6:
        raise ValueError(f"Hex inválido: {hex_color!r}")
    return (int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02X}{g:02X}{b:02X}"


class ColorPickerDialog(ctk.CTkToplevel):
    def __init__(self, master, initial_color: str, on_pick):
        super().__init__(master)
        self._on_pick = on_pick
        self._updating = False

        self.title("Escolher cor")
        self.geometry("320x400")
        self.configure(fg_color=theme.BG_APP)
        make_modal(self, master)

        try:
            initial_rgb = _hex_to_rgb(initial_color)
        except ValueError:
            initial_rgb = (0, 0, 0)

        self._sliders: dict[str, ctk.CTkSlider] = {}
        self._value_labels: dict[str, ctk.CTkLabel] = {}
        for (label, key), value in zip(_CHANNELS, initial_rgb):
            row = ctk.CTkFrame(self, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=(12, 0))
            ctk.CTkLabel(
                row, text=label, text_color=theme.TEXT_PRIMARY, width=70, anchor="w",
            ).pack(side="left")
            slider = ctk.CTkSlider(
                row, from_=0, to=255, number_of_steps=255,
                command=lambda value, k=key: self._on_slider_changed(k, value))
            slider.set(value)
            slider.pack(side="left", fill="x", expand=True, padx=(8, 8))
            value_label = ctk.CTkLabel(
                row, text=str(value), text_color=theme.TEXT_PRIMARY, width=30)
            value_label.pack(side="left")
            self._sliders[key] = slider
            self._value_labels[key] = value_label

        hex_row = ctk.CTkFrame(self, fg_color="transparent")
        hex_row.pack(fill="x", padx=20, pady=(16, 0))
        ctk.CTkLabel(
            hex_row, text="Hex", text_color=theme.TEXT_PRIMARY, width=70, anchor="w",
        ).pack(side="left")
        self._hex_entry = ctk.CTkEntry(hex_row)
        self._hex_entry.insert(0, _rgb_to_hex(*initial_rgb))
        self._hex_entry.pack(side="left", fill="x", expand=True, padx=(8, 8))
        self._hex_entry.bind("<Return>", lambda _event: self._on_hex_changed())
        self._hex_entry.bind("<FocusOut>", lambda _event: self._on_hex_changed())

        self._preview = ctk.CTkFrame(
            self, fg_color=_rgb_to_hex(*initial_rgb), corner_radius=8,
            border_width=1, border_color=theme.TEXT_PRIMARY, height=60)
        self._preview.pack(fill="x", padx=20, pady=(16, 0))

        self._error_label = ctk.CTkLabel(self, text="", text_color=theme.ACCENT_EXPENSE)
        self._error_label.pack(anchor="w", padx=20, pady=(8, 0))

        buttons_row = ctk.CTkFrame(self, fg_color="transparent")
        buttons_row.pack(fill="x", padx=20, pady=(16, 20))
        ctk.CTkButton(
            buttons_row, text="Cancelar", fg_color="transparent", border_width=1,
            border_color=theme.BORDER_ACCENT, text_color=theme.TEXT_PRIMARY,
            command=self.destroy,
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(
            buttons_row, text="OK", fg_color=theme.ACCENT_EXPENSE, command=self._submit,
        ).pack(side="left", fill="x", expand=True)

    def _current_rgb(self) -> tuple[int, int, int]:
        return tuple(round(self._sliders[key].get()) for key in ("r", "g", "b"))

    def _on_slider_changed(self, key: str, value: float) -> None:
        if self._updating:
            return
        self._value_labels[key].configure(text=str(round(value)))
        hex_color = _rgb_to_hex(*self._current_rgb())
        self._updating = True
        self._hex_entry.delete(0, "end")
        self._hex_entry.insert(0, hex_color)
        self._updating = False
        self._preview.configure(fg_color=hex_color)

    def _on_hex_changed(self) -> None:
        if self._updating:
            return
        try:
            r, g, b = _hex_to_rgb(self._hex_entry.get())
        except ValueError:
            self._error_label.configure(text="Hex inválido. Use #RRGGBB.")
            return
        self._error_label.configure(text="")
        self._updating = True
        for key, value in zip(("r", "g", "b"), (r, g, b)):
            self._sliders[key].set(value)
            self._value_labels[key].configure(text=str(value))
        self._updating = False
        self._preview.configure(fg_color=_rgb_to_hex(r, g, b))

    def _submit(self) -> None:
        self._on_pick(_rgb_to_hex(*self._current_rgb()))
        self.destroy()
