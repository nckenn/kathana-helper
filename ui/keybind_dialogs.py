"""
Keybind capture dialogs extracted from gui.py.
"""
from __future__ import annotations

import customtkinter as ctk


def _build_key_string(event) -> str | None:
    key = event.keysym.upper()
    modifiers: list[str] = []
    state = event.state
    keysym = event.keysym.upper()

    if state & 0x0004:
        modifiers.append("Ctrl")
    if state & 0x0001:
        modifiers.append("Shift")
    if state & 0x20000 or keysym in ["ALT_L", "ALT_R", "META"]:
        if "Alt" not in modifiers:
            modifiers.append("Alt")

    def combine(k: str) -> str:
        return "+".join(modifiers + [k]) if modifiers else k

    if key in [str(i) for i in range(10)] or len(key) == 1:
        return combine(key)
    if key in [f"F{i}" for i in range(1, 13)]:
        return combine(key)
    if key in ["SPACE", "TAB", "RETURN", "ESCAPE"]:
        key_map = {"SPACE": "SPACE", "TAB": "TAB", "RETURN": "ENTER", "ESCAPE": "ESC"}
        return combine(key_map.get(key, key))
    return None


def open_keybind_dialog(parent, title: str, prompt: str, on_value) -> None:
    """
    Opens a modal dialog to capture one key combo, calling on_value(value_str).
    """
    popup = ctk.CTkToplevel(parent)
    popup.title(title)
    popup.geometry("300x150")
    popup.transient(parent)
    popup.grab_set()

    try:
        root_x = parent.winfo_x()
        root_y = parent.winfo_y()
        popup.geometry(f"+{root_x + 50}+{root_y + 50}")
    except Exception:
        pass

    label = ctk.CTkLabel(popup, text=prompt, font=ctk.CTkFont(size=12))
    label.pack(pady=30)

    def on_key_press(event):
        value = _build_key_string(event)
        if value:
            on_value(value)
            popup.destroy()

    popup.bind("<Key>", on_key_press)
    popup.focus_set()
    ctk.CTkButton(popup, text="Cancel", command=popup.destroy, width=100).pack(pady=10)

