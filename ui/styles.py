"""Shared widget styling for the Kathana GUI.

One place to decide what a control looks like, so importance reads at a glance
instead of every button competing. Four roles, each with one job:

    PRIMARY    the single action that runs the bot (Start / Stop)
    ACCENT     the confirming action in its context (Connect; a dialog's Save)
    SECONDARY  everything else you can click: Refresh, Regions, Save, Load
    CHIP       not an action at all -- a value you can edit, like a hotkey

Before this, hotkey chips were filled blue and looked exactly like Connect, so
a stored value and the app's main action had identical weight.

Each role is a dict of CTkButton kwargs. Apply at construction with **, or to an
existing widget with `apply_role(widget, SECONDARY)`.
"""

# Green: the bot is the point of the app, so running it owns the strongest colour.
PRIMARY = {
    'fg_color': '#16a34a',
    'hover_color': '#15803d',
    'text_color': '#ffffff',
}

# Blue: connecting to the game window, the one thing you must do first.
ACCENT = {
    'fg_color': '#2563eb',
    'hover_color': '#1d4ed8',
    'text_color': '#ffffff',
}

# Neutral fill: available, not shouting. Most buttons are this.
SECONDARY = {
    'fg_color': ('gray78', 'gray26'),
    'hover_color': ('gray70', 'gray34'),
    'text_color': ('gray10', 'gray92'),
}

# Outline only: reads as a field holding a value, not as a button to press.
CHIP = {
    'fg_color': 'transparent',
    'hover_color': ('gray82', 'gray28'),
    'border_width': 1,
    'border_color': ('gray62', 'gray42'),
    'text_color': ('gray15', 'gray85'),
}

# Muted text for secondary information (status line, profile name, hints).
MUTED_TEXT = ('gray40', 'gray60')


def apply_role(widget, role):
    """Restyle an existing widget in place."""
    widget.configure(**role)
    return widget
