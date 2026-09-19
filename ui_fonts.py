"""App font setup: register the bundled Geist Pixel family and make it the default.

Every ``ctk.CTkFont(size=..., weight=...)`` in the GUI that does not pass an
explicit ``family`` falls back to ``ThemeManager.theme["CTkFont"]["family"]``,
so setting that once here restyles the whole app without touching call sites.
"""
import os
import sys

# Tk matches on the font's family name, not the file name.
APP_FONT_FAMILY = "Geist Pixel Square"
# Windows/Tk fallbacks if the bundled font fails to register for any reason.
_FALLBACK_FAMILY = "Segoe UI"

# Ships Regular only; Tk synthesizes the bold weight the GUI asks for.
_FONT_FILES = ("GeistPixel-Square.ttf",)


def _fonts_dir():
    """Folder holding the bundled .ttf files (next to code, or in a frozen bundle)."""
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "fonts")


def _register_font_files():
    """Load the bundled TTFs into the process. Returns True on success."""
    try:
        from customtkinter import FontManager
    except Exception:
        return False

    fonts_dir = _fonts_dir()
    loaded_any = False
    for name in _FONT_FILES:
        path = os.path.join(fonts_dir, name)
        if not os.path.exists(path):
            continue
        try:
            if FontManager.load_font(path):
                loaded_any = True
        except Exception:
            pass
    return loaded_any


def apply_app_font():
    """
    Register Geist Pixel and set it as the CustomTkinter default font family.

    Call once, after ``set_appearance_mode`` / ``set_default_color_theme`` and
    before creating widgets. Safe to call even if the font is missing (falls back
    to the system UI font).
    """
    try:
        import customtkinter as ctk
    except Exception:
        return _FALLBACK_FAMILY

    family = APP_FONT_FAMILY if _register_font_files() else _FALLBACK_FAMILY
    try:
        ctk.ThemeManager.theme["CTkFont"]["family"] = family
    except Exception:
        pass
    return family
