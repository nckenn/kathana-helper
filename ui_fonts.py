"""App font setup: register the bundled JetBrains Mono family and make it the default.

Every ``ctk.CTkFont(size=..., weight=...)`` in the GUI that does not pass an
explicit ``family`` falls back to ``ThemeManager.theme["CTkFont"]["family"]``,
so setting that once here restyles the whole app without touching call sites.
"""
import os
import sys

# Two faces, each doing what it is good at.
#
# Monospace used to be the default for everything, which made prose harder to
# read and gave labels and data the same texture. The UI face now carries
# labels, headings and sentences; monospace is kept for values whose characters
# matter individually: hotkeys, percentages, filenames, coordinates.
#
# Tk matches on the font's family name, not the file name.
MONO_FONT_FAMILY = "JetBrains Mono"
UI_FONT_FAMILY = "Segoe UI"

# Back-compat: this name meant "the family the app uses everywhere".
APP_FONT_FAMILY = MONO_FONT_FAMILY
# Windows/Tk fallbacks if the bundled font fails to register for any reason.
_FALLBACK_FAMILY = "Segoe UI"

_FONT_FILES = ("JetBrainsMono-Regular.ttf", "JetBrainsMono-Bold.ttf")


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
    Register JetBrains Mono and set it as the CustomTkinter default font family.

    Call once, after ``set_appearance_mode`` / ``set_default_color_theme`` and
    before creating widgets. Safe to call even if the font is missing (falls back
    to the system UI font).
    """
    try:
        import customtkinter as ctk
    except Exception:
        return _FALLBACK_FAMILY

    global MONO_FONT_FAMILY, APP_FONT_FAMILY
    if not _register_font_files():
        MONO_FONT_FAMILY = _FALLBACK_FAMILY
        APP_FONT_FAMILY = _FALLBACK_FAMILY

    # The default family is the UI face: a widget that does not ask for one is
    # a label or a sentence. Values opt into monospace via mono().
    try:
        ctk.ThemeManager.theme["CTkFont"]["family"] = UI_FONT_FAMILY
    except Exception:
        pass
    return UI_FONT_FAMILY


def mono(size=11, weight="normal"):
    """A font for values whose individual characters matter.

    Hotkeys, percentages, filenames, coordinates -- anything read character by
    character, or compared down a column.
    """
    import customtkinter as ctk
    return ctk.CTkFont(family=MONO_FONT_FAMILY, size=size, weight=weight)
