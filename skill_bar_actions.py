"""Find and click built-in skill bar icons (hammer, assist) via template matching."""
import config
import frame_cache
import input_handler
import template_cache
import match_utils

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

SKILL_ICON_FILES = {
    'hammer': 'hammer.bmp',
    'assist': 'assist.bmp',
}
def _match_threshold():
    return float(getattr(config, 'skill_match_threshold', 0.7))


def _match_margin():
    return float(getattr(config, 'template_match_margin', 0.05))
_loc_cache = {}


def resolve_icon_path(icon_name):
    filename = SKILL_ICON_FILES.get(icon_name)
    if not filename:
        return None
    return config.resolve_resource_path(filename) or config.apply_resource_path(filename)


def _match_in_skills(area_skills, template, resolved_path, threshold=None):
    if threshold is None:
        threshold = _match_threshold()
    margin = _match_margin()
    if not CV2_AVAILABLE or area_skills is None or template is None or area_skills.size == 0:
        return False, None, 0.0
    if area_skills.shape[0] < template.shape[0] or area_skills.shape[1] < template.shape[1]:
        return False, None, 0.0

    hint = _loc_cache.get(resolved_path)
    if hint is not None:
        hx, hy = hint
        pad = 30
        x0 = max(0, hx - pad)
        y0 = max(0, hy - pad)
        x1 = min(area_skills.shape[1], hx + template.shape[1] + pad)
        y1 = min(area_skills.shape[0], hy + template.shape[0] + pad)
        roi = area_skills[y0:y1, x0:x1]
        if roi.shape[0] >= template.shape[0] and roi.shape[1] >= template.shape[1]:
            matched, conf, max_loc = match_utils.template_match_with_margin(
                roi, template, threshold, margin,
            )
            if matched and max_loc is not None:
                loc = (x0 + max_loc[0], y0 + max_loc[1])
                _loc_cache[resolved_path] = loc
                return True, loc, conf

    matched, conf, max_loc = match_utils.template_match_with_margin(
        area_skills, template, threshold, margin,
    )
    if matched and max_loc is not None:
        _loc_cache[resolved_path] = max_loc
        return True, max_loc, conf
    return False, None, conf


def click_skill_icon(hwnd, icon_name, threshold=None):
    """Find icon in calibrated skill bar area and click it. Returns True on success."""
    if not CV2_AVAILABLE or not hwnd or not config.area_skills or not config.calibrator:
        return False

    path = resolve_icon_path(icon_name)
    if not path:
        print(f'[SkillBar] Missing template for {icon_name}')
        return False

    template = template_cache.get_template(path, cv2.IMREAD_COLOR)
    if template is None:
        print(f'[SkillBar] Could not load template: {path}')
        return False

    screen = frame_cache.get_frame(hwnd, config.calibrator)
    if screen is None:
        return False

    x1, y1, x2, y2 = config.area_skills
    area_skills = frame_cache.crop_rect(screen, x1, y1, x2, y2, frame_cache.get_origin())
    if area_skills is None or area_skills.size == 0:
        return False

    found, loc, confidence = _match_in_skills(area_skills, template, path, threshold)
    if not found or loc is None:
        return False

    th, tw = template.shape[:2]
    click_x = x1 + loc[0] + tw // 2
    click_y = y1 + loc[1] + th // 2
    ok = input_handler.perform_mouse_click_window_image(hwnd, click_x, click_y)
    if ok:
        print(f'[SkillBar] Clicked {icon_name} at ({click_x}, {click_y}) conf={confidence:.2f}')
    return ok
