"""Crisp vector-drawn UI icons (PIL -> CTkImage).

Icons are drawn at 4x supersample and downscaled with LANCZOS for smooth,
anti-aliased edges, so they look sharper and more consistent than the
"Segoe UI Symbol" glyphs the buttons used before. Results are cached and kept
alive here (CTkImage must not be garbage-collected while a button uses it).
"""
import math

import customtkinter as ctk
from PIL import Image, ImageDraw

_SS = 4  # supersample factor
_DEFAULT_COLOR = "#e5e7eb"
_cache = {}


def _canvas(size):
    s = size * _SS
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img), s


def _finish(img, size):
    return img.resize((size, size), Image.LANCZOS)


def _arrowhead(draw, x, y, angle_deg, length, color):
    """Filled triangle whose tip is at (x, y), pointing along angle_deg."""
    a = math.radians(angle_deg)
    tip = (x, y)
    left = (x - length * math.cos(a - math.radians(32)),
            y - length * math.sin(a - math.radians(32)))
    right = (x - length * math.cos(a + math.radians(32)),
             y - length * math.sin(a + math.radians(32)))
    draw.polygon([tip, left, right], fill=color)


def _draw_refresh(size, color, stroke):
    img, d, s = _canvas(size)
    w = max(2, int(stroke * _SS))
    m = int(s * 0.22)
    box = [m, m, s - m, s - m]
    # Clockwise ~300deg arc with a small gap at the top.
    # PIL angles: 0=east, 90=south, 270=north (y grows downward).
    start, end = 300, 240
    d.arc(box, start=start, end=end, fill=color, width=w)
    cx, cy = s / 2.0, s / 2.0
    r = (s - 2 * m) / 2.0
    a = math.radians(end)
    tipx, tipy = cx + r * math.cos(a), cy + r * math.sin(a)
    # Arrowhead at the top-left tip, pointing clockwise (up into the gap).
    _arrowhead(d, tipx, tipy, end + 90, s * 0.26, color)
    return _finish(img, size)


def _draw_minimize(size, color, stroke):
    img, d, s = _canvas(size)
    w = max(2, int(stroke * _SS))
    y = int(s * 0.56)
    x0, x1 = int(s * 0.26), int(s * 0.74)
    d.line([(x0, y), (x1, y)], fill=color, width=w)
    # Rounded caps.
    r = w / 2.0
    d.ellipse([x0 - r, y - r, x0 + r, y + r], fill=color)
    d.ellipse([x1 - r, y - r, x1 + r, y + r], fill=color)
    return _finish(img, size)


def _draw_expand(size, color, stroke):
    """Double-headed diagonal arrow (bottom-left <-> top-right) = restore/expand."""
    img, d, s = _canvas(size)
    w = max(2, int(stroke * _SS))
    m = int(s * 0.28)
    bl = (m, s - m)
    tr = (s - m, m)
    d.line([bl, tr], fill=color, width=w)
    _arrowhead(d, tr[0], tr[1], -45, s * 0.24, color)   # up-right
    _arrowhead(d, bl[0], bl[1], 135, s * 0.24, color)   # down-left
    return _finish(img, size)


def _draw_play(size, color, stroke):
    img, d, s = _canvas(size)
    m = int(s * 0.26)
    # Right-pointing triangle, slightly optically centered.
    d.polygon([(m + int(s * 0.04), m), (m + int(s * 0.04), s - m),
               (s - m, s / 2.0)], fill=color)
    return _finish(img, size)


def _draw_stop(size, color, stroke):
    img, d, s = _canvas(size)
    m = int(s * 0.3)
    radius = int(s * 0.06)
    d.rounded_rectangle([m, m, s - m, s - m], radius=radius, fill=color)
    return _finish(img, size)


def _draw_check(size, color, stroke):
    img, d, s = _canvas(size)
    w = max(2, int((stroke + 0.4) * _SS))
    pts = [(s * 0.22, s * 0.55), (s * 0.42, s * 0.74), (s * 0.80, s * 0.28)]
    d.line(pts, fill=color, width=w, joint="curve")
    # Rounded ends.
    r = w / 2.0
    for px, py in (pts[0], pts[-1]):
        d.ellipse([px - r, py - r, px + r, py + r], fill=color)
    return _finish(img, size)


def _draw_dot(size, color, stroke):
    """Hollow ring (pending/neutral status indicator)."""
    img, d, s = _canvas(size)
    w = max(2, int(stroke * _SS))
    m = int(s * 0.3)
    d.ellipse([m, m, s - m, s - m], outline=color, width=w)
    return _finish(img, size)


def _draw_chevron_down(size, color, stroke):
    img, d, s = _canvas(size)
    w = max(2, int(stroke * _SS))
    d.line([(s * 0.28, s * 0.4), (s * 0.5, s * 0.62), (s * 0.72, s * 0.4)],
           fill=color, width=w, joint="curve")
    return _finish(img, size)


def _draw_chevron_right(size, color, stroke):
    img, d, s = _canvas(size)
    w = max(2, int(stroke * _SS))
    d.line([(s * 0.42, s * 0.28), (s * 0.64, s * 0.5), (s * 0.42, s * 0.72)],
           fill=color, width=w, joint="curve")
    return _finish(img, size)


_DRAWERS = {
    "refresh": _draw_refresh,
    "minimize": _draw_minimize,
    "expand": _draw_expand,
    "play": _draw_play,
    "stop": _draw_stop,
    "check": _draw_check,
    "dot": _draw_dot,
    "chevron_down": _draw_chevron_down,
    "chevron_right": _draw_chevron_right,
}


def get_icon(name, size=16, color=_DEFAULT_COLOR, stroke=1.6):
    """Return a cached CTkImage for an icon name (draws it on first use)."""
    key = (name, size, color, round(stroke, 2))
    if key in _cache:
        return _cache[key]
    drawer = _DRAWERS.get(name)
    if drawer is None:
        return None
    pil = drawer(size, color, stroke)
    image = ctk.CTkImage(light_image=pil, dark_image=pil, size=(size, size))
    _cache[key] = image
    return image


def render_pil(name, size=64, color=_DEFAULT_COLOR, stroke=1.6):
    """PIL image for previewing/testing icons (no Tk root required)."""
    drawer = _DRAWERS.get(name)
    return drawer(size, color, stroke) if drawer else None
