"""Mob filter using OpenCV template matching (no OCR)."""
import cv2
import config
import window_utils
import mob_template_store

_template_cache = {}


def is_active():
    return (
        config.mob_detection_enabled
        and bool(config.mob_templates)
        and scan_area_available()
    )


def invalidate_cache():
    _template_cache.clear()


def sync_scan_area_from_calibration():
    """Copy enemy name area from calibrator into mob_scan_area (top-left rect)."""
    cal = config.calibrator
    if not cal or not cal.enemy_name_area:
        return False
    cx, cy, w, h = cal.enemy_name_area
    w, h = int(w), int(h)
    config.mob_scan_area.update({
        'x': int(cx - w // 2),
        'y': int(cy - h // 2),
        'width': w,
        'height': h,
    })
    config.target_name_area['x'] = int(cx)
    config.target_name_area['y'] = int(cy)
    config.target_name_area['width'] = w
    config.target_name_area['height'] = h
    return True


def get_scan_area():
    """Scan rect for mob templates — live calibrator area, else saved mob_scan_area."""
    if config.calibrator and config.calibrator.enemy_name_area:
        cx, cy, w, h = config.calibrator.enemy_name_area
        w, h = int(w), int(h)
        return {
            'x': int(cx - w // 2),
            'y': int(cy - h // 2),
            'width': w,
            'height': h,
        }
    return dict(config.mob_scan_area)


def scan_area_available():
    """True when calibration (or saved settings) provides a valid scan region."""
    if config.calibrator and config.calibrator.enemy_name_area:
        return True
    return config.bar_area_configured(config.mob_scan_area)


def _get_template(entry):
    key = entry.get('id')
    if key in _template_cache:
        return _template_cache[key]
    img = mob_template_store.load_template_bgr(entry)
    if img is not None:
        _template_cache[key] = img
    return img


def capture_scan_area(hwnd):
    area = get_scan_area()
    return window_utils.capture_window_region_bgr(
        hwnd, area['x'], area['y'], area['width'], area['height'],
    )


def _align_template(template_bgr, scan_shape):
    """Resize template to scan dimensions when they differ (legacy templates)."""
    sh, sw = scan_shape[:2]
    th, tw = template_bgr.shape[:2]
    if th == sh and tw == sw:
        return template_bgr
    return cv2.resize(template_bgr, (sw, sh), interpolation=cv2.INTER_AREA)


def _match_score(scan_bgr, template_bgr):
    """Compare scan to template; equal sizes use a single full-frame score."""
    template_bgr = _align_template(template_bgr, scan_bgr.shape)
    scan_g = cv2.cvtColor(scan_bgr, cv2.COLOR_BGR2GRAY)
    tmpl_g = cv2.cvtColor(template_bgr, cv2.COLOR_BGR2GRAY)
    sh, sw = scan_g.shape[:2]
    th, tw = tmpl_g.shape[:2]
    if sh == th and sw == tw:
        res = cv2.matchTemplate(scan_g, tmpl_g, cv2.TM_CCOEFF_NORMED)
        return float(res[0, 0])
    if sh >= th and sw >= tw:
        res = cv2.matchTemplate(scan_g, tmpl_g, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        return float(max_val)
    return 0.0


def _collect_scores(scan_bgr, templates=None):
    templates = templates if templates is not None else config.mob_templates
    scores = []
    for entry in templates:
        template = _get_template(entry)
        if template is None:
            continue
        confidence = _match_score(scan_bgr, template)
        scores.append((confidence, entry))
    scores.sort(key=lambda item: item[0], reverse=True)
    return scores


def match_in_image(scan_bgr, templates=None):
    """
    Match learned templates against a scan image.
    Returns best match dict: {id, name, file, confidence} or None.
    """
    if scan_bgr is None or scan_bgr.size == 0:
        return None
    templates = templates if templates is not None else config.mob_templates
    if not templates:
        return None

    threshold = config.mob_match_threshold
    margin = config.mob_match_margin
    scores = _collect_scores(scan_bgr, templates)
    if not scores:
        return None

    best_conf, best_entry = scores[0]
    second_conf = scores[1][0] if len(scores) > 1 else 0.0

    if best_conf < threshold:
        return None
    if len(scores) > 1 and (best_conf - second_conf) < margin:
        return None

    return {
        'id': best_entry['id'],
        'name': best_entry.get('name', best_entry['id']),
        'file': best_entry.get('file', ''),
        'confidence': best_conf,
    }


def probe(hwnd):
    """
    Test scan without requiring mob filter to be enabled.
    Returns dict with match info and best score for UI feedback.
    """
    if not scan_area_available():
        return {'error': 'Calibrate first to detect the enemy name scan area'}
    if not config.mob_templates:
        return {'error': 'Learn at least one mob template first'}

    scan_bgr = capture_scan_area(hwnd)
    if scan_bgr is None or scan_bgr.size == 0:
        area = get_scan_area()
        return {
            'error': (
                f'Could not capture scan region '
                f"({area['x']},{area['y']} {area['width']}×{area['height']}). "
                'Focus the game window and try again.'
            ),
        }

    scores = _collect_scores(scan_bgr)
    match = match_in_image(scan_bgr)
    best_conf = scores[0][0] if scores else 0.0
    best_name = scores[0][1].get('name', '?') if scores else '?'
    return {
        'match': match,
        'best_score': best_conf,
        'best_name': best_name,
        'threshold': config.mob_match_threshold,
        'scan_size': (scan_bgr.shape[1], scan_bgr.shape[0]),
    }


def refresh_scan(hwnd):
    """Capture scan region and update config.current_mob_match."""
    if not is_active():
        config.current_mob_match = None
        return None
    if not hwnd:
        config.current_mob_match = None
        return None
    scan_bgr = capture_scan_area(int(hwnd))
    match = match_in_image(scan_bgr)
    config.current_mob_match = match
    if match:
        config.current_target_mob = match['name']
        config.current_enemy_name = match['name']
    return match


def scan(hwnd):
    """Scan the configured region for any learned mob template."""
    if not is_active():
        config.current_mob_match = None
        return None
    return refresh_scan(hwnd)


def should_allow_combat(hwnd):
    """Skills and attack only when a whitelisted mob matches."""
    if not is_active():
        return True
    if not hwnd:
        return False
    return config.current_mob_match is not None


def should_allow_action(action_name, hwnd):
    """
    Gate target/attack when mob filter is active.
    Uses config.current_mob_match (refresh via refresh_scan in bot loop).
    """
    if not is_active():
        return True
    if not hwnd:
        return False

    match = config.current_mob_match
    if action_name == 'target':
        return match is None
    if action_name == 'attack':
        return match is not None
    return True
