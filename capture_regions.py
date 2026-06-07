"""
Compute union capture regions for bot vision (Tier 4 — region-only BitBlt).
"""
import config
import hp_number_reader
import region_helpers


def _rect(x, y, w, h):
    if w <= 0 or h <= 0:
        return None
    return (int(x), int(y), int(w), int(h))


def _append_area_dict(rects, area):
    r = region_helpers.area_to_rect(area)
    if r:
        rects.append(r)


def compute_capture_rects_from_config():
    """Return capture rectangles from manually saved config regions."""
    rects = []
    _append_area_dict(rects, config.hp_bar_area)
    _append_area_dict(rects, config.mp_bar_area)
    _append_area_dict(rects, config.target_name_area)
    _append_area_dict(rects, config.target_hp_bar_area)
    _append_area_dict(rects, config.skill_area)
    _append_area_dict(rects, config.buff_area)
    _append_area_dict(rects, config.system_message_area)
    _append_area_dict(rects, config.mob_scan_area)
    return rects


def compute_capture_rects(calibrator):
    """Return capture rectangles for HP/MP, enemy strip, skill bar, and buff strip."""
    if calibrator is None:
        return compute_capture_rects_from_config()

    rects = []
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
        strip = hp_number_reader.get_enemy_target_strip_rect(calibrator)
        if strip:
            sx, sy, sw, sh = strip
            r = _rect(sx, sy, sw, sh)
            if r:
                rects.append(r)

    if config.area_skills:
        x1, y1, x2, y2 = config.area_skills
        r = _rect(x1, y1, x2 - x1, y2 - y1)
        if r:
            rects.append(r)

    _append_area_dict(rects, config.buff_area)
    _append_area_dict(rects, config.system_message_area)

    manual = compute_capture_rects_from_config()
    for r in manual:
        if r not in rects:
            rects.append(r)
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
