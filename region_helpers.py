"""Helpers for manually picked screen regions."""
import config

# Enemy name/level row height (matches hp_number_reader.NAME_AREA_HEIGHT)
NAME_H = 18


def region_label(area, default='Pick region'):
    if config.bar_area_configured(area):
        return f"✓ ({area['x']},{area['y']}) {area['width']}×{area['height']}"
    return default


def region_status_text(area):
    """Compact status for the Regions tab (coords live beside a short Pick button)."""
    if config.bar_area_configured(area):
        return f"({area['x']}, {area['y']}) · {area['width']}×{area['height']}"
    return 'Not set'


def bot_regions_ready():
    """Minimum regions required to start the bot."""
    return (
        config.bar_area_configured(config.hp_bar_area)
        and config.bar_area_configured(config.mp_bar_area)
    )


def apply_area_dict(area_dict, x, y, width, height):
    area_dict['x'] = int(x)
    area_dict['y'] = int(y)
    area_dict['width'] = int(width)
    area_dict['height'] = int(height)


def clear_area(area_dict):
    """Reset a region dict to unset (width/height 0)."""
    area_dict['x'] = 0
    area_dict['y'] = 0
    area_dict['width'] = 0
    area_dict['height'] = 0


def sync_mob_scan_from_enemy_name():
    """Copy enemy name pick into mob_scan_area (same size as Regions pick)."""
    if not config.bar_area_configured(config.target_name_area):
        return
    h = int(config.target_name_area.get('height') or 0)
    apply_area_dict(
        config.mob_scan_area,
        config.target_name_area['x'],
        config.target_name_area['y'],
        config.target_name_area['width'],
        h if h > 0 else NAME_H,
    )


def sync_skill_area_tuple():
    """Keep legacy area_skills tuple in sync with skill_area dict."""
    if config.bar_area_configured(config.skill_area):
        a = config.skill_area
        config.area_skills = (
            a['x'], a['y'],
            a['x'] + a['width'], a['y'] + a['height'],
        )
    elif not config.area_skills:
        config.area_skills = None


def migrate_area_skills_to_dict():
    """Load legacy tuple area_skills into skill_area dict."""
    if config.bar_area_configured(config.skill_area):
        return
    legacy = config.area_skills
    if not legacy or not isinstance(legacy, (tuple, list)) or len(legacy) != 4:
        return
    x1, y1, x2, y2 = legacy
    apply_area_dict(config.skill_area, x1, y1, x2 - x1, y2 - y1)


def area_to_rect(area):
    """Return (x, y, w, h) or None."""
    if not config.bar_area_configured(area):
        return None
    return (area['x'], area['y'], area['width'], area['height'])


def combat_detection_ready():
    """True when enemy HP can be monitored (manual regions or legacy calibrator)."""
    if config.bar_area_configured(config.target_hp_bar_area):
        return True
    if config.bar_area_configured(config.target_name_area):
        return True
    if config.bar_area_configured(config.mob_scan_area):
        return True
    cal = config.calibrator
    if cal is not None and cal.mp_position is not None:
        return True
    return False
