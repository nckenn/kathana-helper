"""
Compute union capture regions for bot vision (Tier 4 — region-only BitBlt).
"""
import config

# Enemy HP search strip relative to MP bar (matches auto_attack constants)
ENEMY_SEARCH_OFFSET_Y = 19
ENEMY_SEARCH_OFFSET_X = -1
ENEMY_SEARCH_WIDTH = 210
ENEMY_SEARCH_HEIGHT = 35


def _rect(x, y, w, h):
    if w <= 0 or h <= 0:
        return None
    return (int(x), int(y), int(w), int(h))


def _system_message_buff_strip_rect():
    """Active buff icons strip above the system message area."""
    sys = config.system_message_area
    sw = sys.get('width', 0)
    sh = sys.get('height', 0)
    if sw <= 0 or sh <= 0:
        return None
    cx = sys.get('x', 0)
    cy = sys.get('y', 0)
    half_w = sw // 2
    half_h = sh // 2
    left = cx - half_w - 14
    right = cx + half_w + 10
    top = cy - half_h - 44
    bottom = cy - half_h - 4
    return _rect(left, top, right - left, bottom - top)


def compute_capture_rects(calibrator):
    """Return capture rectangles for HP/MP, enemy strip, skill bar, and buff strip."""
    rects = []
    if calibrator is None:
        return rects

    if calibrator.hp_position and calibrator.hp_dimensions:
        x, y = calibrator.hp_position
        w, h = calibrator.hp_dimensions
        r = _rect(x, y, w, h)
        if r:
            rects.append(r)

    if calibrator.mp_position and calibrator.mp_dimensions:
        x, y = calibrator.mp_position
        w, h = calibrator.mp_dimensions
        r = _rect(x, y, w, h)
        if r:
            rects.append(r)

    if calibrator.mp_position:
        mp_x, mp_y = calibrator.mp_position
        sx = mp_x + ENEMY_SEARCH_OFFSET_X
        sy = mp_y + ENEMY_SEARCH_OFFSET_Y
        r = _rect(sx, sy, ENEMY_SEARCH_WIDTH, ENEMY_SEARCH_HEIGHT)
        if r:
            rects.append(r)

    if config.area_skills:
        x1, y1, x2, y2 = config.area_skills
        r = _rect(x1, y1, x2 - x1, y2 - y1)
        if r:
            rects.append(r)

    buff_strip = _system_message_buff_strip_rect()
    if buff_strip:
        rects.append(buff_strip)

    return rects


def union_rect(rects):
    """Merge rectangles into one bounding box (x, y, w, h)."""
    if not rects:
        return None
    x1 = min(r[0] for r in rects)
    y1 = min(r[1] for r in rects)
    x2 = max(r[0] + r[2] for r in rects)
    y2 = max(r[1] + r[3] for r in rects)
    return (x1, y1, x2 - x1, y2 - y1)
