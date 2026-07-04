"""Read enemy max HP from the HP bar number strip (current/max overlay)."""
import cv2
import numpy as np
import config
import frame_cache
import ui_bar_detection

# Enemy target UI geometry (name row + HP bar below player MP).
SEARCH_AREA_OFFSET_Y = 19  # fallback only when strip cannot be detected
SEARCH_AREA_WIDTH = 210
SEARCH_AREA_HEIGHT = 35
SEARCH_AREA_OFFSET_X = -1
NAME_AREA_HEIGHT = 18
PLAYER_MP_BAR_HEIGHT = 15
ENEMY_STRIP_SCAN_BELOW_MP = 56

HP_SIG_HEIGHT = 14
HP_SIG_MATCH_THRESHOLD = 0.82


def _search_origin(mp_x, mp_y):
    return (
        max(0, mp_x + SEARCH_AREA_OFFSET_X),
        max(0, mp_y + SEARCH_AREA_OFFSET_Y),
    )


def locate_enemy_target_strip(screen_bgr, mp_x, mp_y, mp_bar_h=None, mp_bar_w=None):
    """
    Detect the enemy target strip (name row + red HP bar) below the player's MP bar.

    Anchors horizontally to the player MP bar and uses strict red detection so
    floor color behind transparent bars does not shift the search window.
    """
    if screen_bgr is None or screen_bgr.size == 0:
        return None
    if mp_bar_h is None:
        mp_bar_h = PLAYER_MP_BAR_HEIGHT
    if mp_bar_w is None or mp_bar_w <= 0:
        mp_bar_w = SEARCH_AREA_WIDTH

    screen_h, screen_w = screen_bgr.shape[:2]
    mp_bottom = int(mp_y + mp_bar_h)
    scan_y1 = max(0, mp_bottom)
    scan_y2 = min(screen_h, scan_y1 + ENEMY_STRIP_SCAN_BELOW_MP)
    if scan_y2 <= scan_y1 + NAME_AREA_HEIGHT:
        return None

    strip_x = max(0, int(mp_x + SEARCH_AREA_OFFSET_X))
    if mp_bar_w >= 80:
        strip_x = max(0, int(mp_x))
        strip_w = min(int(mp_bar_w), screen_w - strip_x)
    else:
        strip_w = min(SEARCH_AREA_WIDTH, screen_w - strip_x)
    if strip_w <= 0:
        return None

    crop = screen_bgr[scan_y1:scan_y2, strip_x:strip_x + strip_w]
    if crop.size == 0:
        return None

    red_bands, _ = ui_bar_detection.probe_red_bands(crop, strict_sat=78, strict_val=55)
    mp_band = (0, 0, strip_w, mp_bar_h)
    best = None
    best_key = None
    for bx, by, bw, bh in red_bands:
        local = (bx, by, bw, bh)
        overlap = ui_bar_detection._x_overlap_ratio(mp_band, local)
        if overlap < 0.35:
            continue
        gap = by
        key = (overlap, -gap, bw)
        if best_key is None or key > best_key:
            best_key, best = key, (bx, by, bw, bh)

    if best is not None:
        bx, by, bw, bh = best
        hp_y = scan_y1 + by
        name_y = max(0, hp_y - NAME_AREA_HEIGHT)
        bar_left = strip_x + bx
        return {
            'name_area': (
                bar_left + bw // 2,
                name_y + NAME_AREA_HEIGHT // 2,
                bw,
                NAME_AREA_HEIGHT,
            ),
            'hp_area': (bar_left + bw // 2, hp_y + bh // 2, bw, bh),
            'search_origin': (bar_left, name_y),
        }

    name_y = max(0, int(mp_y + mp_bar_h + 5))
    return {
        'name_area': (
            strip_x + strip_w // 2,
            name_y + NAME_AREA_HEIGHT // 2,
            strip_w,
            NAME_AREA_HEIGHT,
        ),
        'hp_area': None,
        'search_origin': (strip_x, name_y),
    }


def get_enemy_name_bar_rect(calibrator=None):
    """Screen rect (x, y, width, height) for the enemy name/level row."""
    # If the caller passed a calibrator explicitly and it has an enemy name area,
    # prefer it over any global/manual picks. This keeps calibration + tests stable
    # even if other parts of the app previously configured manual regions.
    if calibrator is not None:
        enemy_name = getattr(calibrator, 'enemy_name_area', None)
        if enemy_name:
            cx, cy, w, _h = enemy_name
            w = int(w)
            return (
                int(cx - w // 2),
                int(cy - NAME_AREA_HEIGHT // 2),
                w,
                NAME_AREA_HEIGHT,
            )

    if config.bar_area_configured(config.target_name_area):
        a = config.target_name_area
        h = min(int(a.get('height') or NAME_AREA_HEIGHT), NAME_AREA_HEIGHT)
        return (int(a['x']), int(a['y']), int(a['width']), h)
    if config.bar_area_configured(config.mob_scan_area):
        a = config.mob_scan_area
        h = min(int(a.get('height') or NAME_AREA_HEIGHT), NAME_AREA_HEIGHT)
        return (int(a['x']), int(a['y']), int(a['width']), h)

    calibrator = calibrator or config.calibrator
    enemy_name = getattr(calibrator, 'enemy_name_area', None) if calibrator else None
    if enemy_name:
        cx, cy, w, _h = enemy_name
        w = int(w)
        return (
            int(cx - w // 2),
            int(cy - NAME_AREA_HEIGHT // 2),
            w,
            NAME_AREA_HEIGHT,
        )
    if calibrator and calibrator.mp_position is not None:
        mp_x, mp_y = calibrator.mp_position
        sx, sy = _search_origin(mp_x, mp_y)
        return (sx, sy, SEARCH_AREA_WIDTH, NAME_AREA_HEIGHT)
    return None


def get_enemy_target_strip_rect(calibrator=None):
    """Screen rect (x, y, width, height) for name row + HP bar."""
    if config.bar_area_configured(config.target_hp_bar_area):
        a = config.target_hp_bar_area
        return (int(a['x']), int(a['y']), int(a['width']), int(a['height']))
    name = get_enemy_name_bar_rect(calibrator)
    if name is None:
        return None
    x, y, w, _h = name
    return (x, y, w, SEARCH_AREA_HEIGHT)


def capture_enemy_hp_text_area(hwnd, screen=None):
    """Capture the HP bar strip below the enemy name (where HP numbers appear)."""
    if config.bar_area_configured(config.target_hp_bar_area):
        import window_utils
        a = config.target_hp_bar_area
        strip = window_utils.capture_window_region_bgr(
            hwnd, a['x'], a['y'], a['width'], a['height'],
        )
        if strip is None or strip.size == 0:
            return None
        return _focus_red_bar(strip)

    if not config.calibrator or config.calibrator.mp_position is None:
        return None
    if screen is None:
        screen = frame_cache.get_frame(hwnd, config.calibrator)
    if screen is None:
        return None

    cal = config.calibrator
    name_rect = get_enemy_name_bar_rect(cal)
    if name_rect is None:
        return None
    search_x, search_y, search_w, _ = name_rect
    y1 = search_y + NAME_AREA_HEIGHT
    y2 = search_y + SEARCH_AREA_HEIGHT
    x2 = search_x + search_w
    strip = frame_cache.crop_rect(
        screen, search_x, y1, x2, y2, frame_cache.get_origin(),
    )
    if strip is None or strip.size == 0:
        return None
    return _focus_red_bar(strip)


def _focus_red_bar(strip_bgr):
    """Crop to the red HP bar rows when the capture includes extra padding."""
    if strip_bgr is None or strip_bgr.size == 0:
        return strip_bgr
    red = ui_bar_detection.build_red_mask(strip_bgr)
    row_sum = np.sum(red > 0, axis=1)
    min_cols = max(4, strip_bgr.shape[1] // 5)
    rows = np.where(row_sum >= min_cols)[0]
    if len(rows) == 0:
        return strip_bgr
    return strip_bgr[rows.min():rows.max() + 1, :]


def hp_percent_from_text_anchor(strip_bgr, fill_mask=None):
    """
    Estimate HP% using the on-bar number overlay as the width anchor.

    The right edge of the max-HP digits marks ~100%; fill mask end is current HP.
    Returns None when overlay text is not visible.
    """
    if strip_bgr is None or strip_bgr.size == 0:
        return None
    hp_text = extract_hp_text_gray(strip_bgr)
    if hp_text is None:
        return None
    bright_cols = (hp_text > 170).sum(axis=0)
    active = np.where(bright_cols > 0)[0]
    if len(active) < 4:
        return None
    anchor_right = int(active[-1]) + 1
    if anchor_right < 8:
        return None

    bar = _focus_red_bar(strip_bgr)
    if bar is None or bar.size == 0:
        return None
    h, w = bar.shape[:2]
    if fill_mask is None:
        fill_mask = ui_bar_detection.build_enemy_red_mask(bar, sat_min=90, val_min=80, hue_max=12)
    if fill_mask.shape[:2] != bar.shape[:2]:
        return None
    min_px = max(1, int(h * 0.5))
    col_counts = (fill_mask > 0).sum(axis=0)
    filled = np.where(col_counts >= min_px)[0]
    if len(filled) == 0:
        return 0.0
    fill_end = int(filled[-1]) + 1
    scale = w / float(max(anchor_right, w))
    effective_anchor = max(anchor_right, int(w * 0.85))
    pct = fill_end / effective_anchor * 100.0 * scale
    return round(float(max(0.0, min(100.0, pct))), 1)


def extract_hp_text_gray(strip_bgr):
    """Grayscale crop of the bright HP number text (e.g. 18000/18000)."""
    if strip_bgr is None or strip_bgr.size == 0:
        return None
    bar = _focus_red_bar(strip_bgr)
    gray = cv2.cvtColor(bar, cv2.COLOR_BGR2GRAY)
    bright = gray > 170
    col_sum = bright.sum(axis=0)
    active = np.where(col_sum > 0)[0]
    if len(active) < 2:
        return None
    return gray[:, active[0]:active[-1] + 1]


def split_max_hp_gray(hp_text_gray):
    """Return grayscale crop of max HP digits (right side of the slash)."""
    if hp_text_gray is None or hp_text_gray.size == 0:
        return None
    width = hp_text_gray.shape[1]
    bright_cols = (hp_text_gray > 170).sum(axis=0)
    lo = width // 3
    hi = max(lo + 1, (2 * width) // 3)
    slash = lo + int(np.argmin(bright_cols[lo:hi]))
    max_part = hp_text_gray[:, slash + 1:]
    if max_part.size == 0 or not np.any(max_part > 150):
        return None
    return max_part


def normalize_hp_signature(gray):
    """Normalize max-HP crop for template storage/comparison."""
    if gray is None or gray.size == 0:
        return None
    height = HP_SIG_HEIGHT
    width = max(1, int(round(gray.shape[1] * height / max(1, gray.shape[0]))))
    return cv2.resize(gray, (width, height), interpolation=cv2.INTER_AREA)


def match_hp_signatures(reference_gray, sample_gray):
    """Compare max-HP signatures. Returns 0..1 (1 = identical max HP digits)."""
    ref = normalize_hp_signature(reference_gray)
    sample = normalize_hp_signature(sample_gray)
    if ref is None or sample is None:
        return 0.0
    if ref.shape == sample.shape:
        res = cv2.matchTemplate(ref, sample, cv2.TM_CCOEFF_NORMED)
        return float(res[0, 0])
    sample = cv2.resize(
        sample, (ref.shape[1], ref.shape[0]), interpolation=cv2.INTER_AREA,
    )
    res = cv2.matchTemplate(ref, sample, cv2.TM_CCOEFF_NORMED)
    return float(res[0, 0])


def build_max_hp_signature(strip_bgr):
    """Build normalized max-HP signature from an HP bar strip capture."""
    hp_text = extract_hp_text_gray(strip_bgr)
    max_part = split_max_hp_gray(hp_text)
    return normalize_hp_signature(max_part)


def analyze_hp_text(strip_bgr):
    """
    Analyze HP numbers on the enemy bar strip.
    Returns max_hp_sig (grayscale), sig-ready fields, and legacy span/digit hints.
    """
    empty = {
        'text_span': 0,
        'digit_count': 0,
        'max_hp_estimate': None,
        'max_hp_sig': None,
        'has_text': False,
        'sig_match_ready': False,
    }
    if strip_bgr is None or strip_bgr.size == 0:
        return empty

    hp_text = extract_hp_text_gray(strip_bgr)
    max_part = split_max_hp_gray(hp_text)
    max_sig = normalize_hp_signature(max_part)
    if max_sig is None:
        return empty

    text_span = int(max_sig.shape[1])
    digit_count = max(1, text_span // 7)

    return {
        'text_span': text_span,
        'digit_count': digit_count,
        'max_hp_estimate': None,
        'max_hp_sig': max_sig,
        'has_text': True,
        'sig_match_ready': True,
    }


def capture_and_analyze(hwnd, screen=None):
    """Capture HP text strip and return analysis dict."""
    strip = capture_enemy_hp_text_area(hwnd, screen)
    if strip is None:
        return None
    result = analyze_hp_text(strip)
    result['strip'] = strip
    return result


def signatures_match(reference_gray, sample_gray, threshold=None):
    """True when max-HP signatures match within threshold."""
    if threshold is None:
        threshold = getattr(config, 'mob_elite_sig_threshold', HP_SIG_MATCH_THRESHOLD)
    score = match_hp_signatures(reference_gray, sample_gray)
    return score >= threshold, score
