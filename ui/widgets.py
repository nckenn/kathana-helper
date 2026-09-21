"""Small shared widgets and helpers for the GUI.

These live outside gui.py so the panel modules in ui/panels/ can use them.
Importing them from gui.py is not possible: gui.py imports the panels, so a
panel importing gui.py back would be a cycle.
"""
import tkinter as tk

import ui_fonts


class ToolTip:
    """Create a tooltip for a given widget"""
    def __init__(self, widget, text='widget info'):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0
        self.widget.bind('<Enter>', self.enter)
        self.widget.bind('<Leave>', self.leave)
        self.widget.bind('<ButtonPress>', self.leave)

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(500, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self, event=None):
        x = y = 0
        x, y, cx, cy = self.widget.bbox("insert") if hasattr(self.widget, 'bbox') else (0, 0, 0, 0)
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        # Creates a toplevel window
        self.tipwindow = tw = tk.Toplevel(self.widget)
        # Leaves only the label and removes the app window
        tw.wm_overrideredirect(True)
        tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                      background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                      font=(ui_fonts.APP_FONT_FAMILY, "8", "normal"), wraplength=250)
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()


def create_tooltip(widget, text):
    """Helper function to create a tooltip for a widget"""
    return ToolTip(widget, text)


KEY_BUTTON_DEFAULT_LABEL = "Set Key"
KEY_BUTTON_TOOLTIP = "Click to set key. Right-click to clear."


def key_button_label(key_value):
    """Uniform label for hotkey assignment buttons (unset vs assigned)."""
    if key_value and str(key_value).strip():
        return str(key_value).strip().upper()
    return KEY_BUTTON_DEFAULT_LABEL


def bind_key_button_clear(button, clear_callback, tooltip=KEY_BUTTON_TOOLTIP):
    """Right-click clears the assigned hotkey."""
    button.bind('<Button-3>', lambda _event: clear_callback())
    create_tooltip(button, tooltip)


def format_license_date(value, fallback=None):
    """Render an ISO timestamp as "January 24, 2027".

    Repeated six times across the licence views, each with a bare `except:`
    that also swallowed KeyboardInterrupt. Returns `fallback` (default: the raw
    value) when the string will not parse, which is what every copy did.
    """
    from datetime import datetime
    try:
        return datetime.fromisoformat(value).strftime('%B %d, %Y')
    except (ValueError, TypeError):
        return value if fallback is None else fallback


def license_days_left(value):
    """Whole days until an ISO timestamp, or None if it will not parse."""
    from datetime import datetime
    try:
        return (datetime.fromisoformat(value) - datetime.now()).days
    except (ValueError, TypeError):
        return None
