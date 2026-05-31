"""Read enemy max HP from the HP bar number strip (current/max overlay)."""
import cv2
import numpy as np
import config
import frame_cache

# Must match auto_attack.py enemy target strip geometry.
SEARCH_AREA_OFFSET_Y = 19
SEARCH_AREA_WIDTH = 210
SEARCH_AREA_HEIGHT = 35
SEARCH_AREA_OFFSET_X = -1
NAME_AREA_HEIGHT = 18

HP_SIG_HEIGHT = 14
HP_SIG_MATCH_THRESHOLD = 0.82


def _search_origin(mp_x, mp_y):
    return (
        max(0, mp_x + SEARCH_AREA_OFFSET_X),
        max(0, mp_y + SEARCH_AREA_OFFSET_Y),
    )


def capture_enemy_hp_text_area(hwnd, screen=None):
    """Capture the HP bar strip below the enemy name (where HP numbers appear)."""
    if not config.calibrator or config.calibrator.mp_position is None:
        return None
    if screen is None:
        screen = frame_cache.get_frame(hwnd, config.calibrator)
    if screen is None:
        return None

    mp_x, mp_y = config.calibrator.mp_position
    search_x, search_y = _search_origin(mp_x, mp_y)
    y1 = search_y + NAME_AREA_HEIGHT
    y2 = search_y + SEARCH_AREA_HEIGHT
    x2 = search_x + SEARCH_AREA_WIDTH
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
    hsv = cv2.cvtColor(strip_bgr, cv2.COLOR_BGR2HSV)
    red = cv2.bitwise_or(
        cv2.inRange(hsv, np.array([0, 100, 100]), np.array([10, 255, 255])),
        cv2.inRange(hsv, np.array([160, 100, 100]), np.array([180, 255, 255])),
    )
    row_sum = np.sum(red > 0, axis=1)
    min_cols = max(4, strip_bgr.shape[1] // 5)
    rows = np.where(row_sum >= min_cols)[0]
    if len(rows) == 0:
        return strip_bgr
    return strip_bgr[rows.min():rows.max() + 1, :]


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
