"""Mob filter using OpenCV template matching on the enemy name/level bar (no OCR)."""
import cv2
import numpy as np
import config
import window_utils
import mob_template_store
import hp_number_reader

_template_cache = {}
NAME_H = int(hp_number_reader.NAME_AREA_HEIGHT)


def is_active():
    return (
        config.mob_detection_enabled
        and bool(config.mob_templates)
        and scan_area_available()
    )


def invalidate_cache():
    _template_cache.clear()


def _filter_ui_text_blobs(mask):
    """Drop overly wide bright blobs (terrain bleeding into corner ROIs)."""
    if mask is None or not np.any(mask):
        return mask
    h, w = mask.shape[:2]
    max_width = max(28, int(w * 0.36))

    bin_u8 = (mask.astype(np.uint8) * 255)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(bin_u8, connectivity=8)
    kept = np.zeros_like(mask, dtype=bool)
    for i in range(1, n):
        width = stats[i, cv2.CC_STAT_WIDTH]
        if width <= max_width:
            kept[labels == i] = True
    return kept


def _white_ui_text_mask(gray, hsv):
    """Game name/level text: bright and low-saturation (not colored terrain)."""
    sat = hsv[:, :, 1]
    gray_min = int(getattr(config, 'mob_text_gray_min', 140))
    sat_max = int(getattr(config, 'mob_text_sat_max', 90))
    return (gray > gray_min) & (sat < sat_max)


def _crop_name_bar(bgr_or_gray):
    """Mob filter only uses the name/level row (top 18px of target UI)."""
    if bgr_or_gray is None or bgr_or_gray.size == 0:
        return bgr_or_gray
    if bgr_or_gray.shape[0] <= NAME_H:
        return bgr_or_gray
    return bgr_or_gray[:NAME_H, :]


def _level_column_start(width):
    """First column where level digits begin (name identity is left of this)."""
    ratio = getattr(config, 'mob_match_level_start_ratio', None)
    if ratio is None:
        legacy = float(getattr(config, 'mob_match_name_width_ratio', 0.68))
        ratio = 0.68 if legacy <= 0.45 else legacy
    return max(32, min(width - 12, int(width * float(ratio))))


def _looks_like_level_digits(bx, bw, bh, width, level_start):
    """Heuristic: small numeric cluster on the far right of the plate."""
    if bh < 4:
        return True
    if bx + bw < level_start * 0.5:
        return False
    if bx >= int(level_start * 0.62) and bw <= max(28, int(width * 0.22)):
        return True
    return False


def _name_text_for_identity(white):
    """
    Keep the full mob name (all word clusters left of level digits).

    Game UIs often render multi-word names as separate blobs; keeping only the
    first blob matched unrelated mobs that share a short prefix.
    """
    if white is None or not np.any(white):
        return white
    h, w = white.shape[:2]
    level_start = _level_column_start(w)
    plate = np.zeros((h, w), dtype=bool)
    plate[:, :level_start] = white[:, :level_start]

    bin_u8 = (plate.astype(np.uint8) * 255)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(bin_u8, connectivity=8)
    kept = np.zeros((h, w), dtype=bool)
    for i in range(1, n):
        bx = stats[i, cv2.CC_STAT_LEFT]
        bw = stats[i, cv2.CC_STAT_WIDTH]
        bh = stats[i, cv2.CC_STAT_HEIGHT]
        if _looks_like_level_digits(bx, bw, bh, w, level_start):
            continue
        kept[labels == i] = True
    if not np.any(kept):
        return _filter_ui_text_blobs(plate)
    return _filter_ui_text_blobs(kept)


def normalize_for_match(bgr):
    """Background-invariant signature: full mob name (left of level digits)."""
    if bgr is None or bgr.size == 0:
        return None
    bgr = _crop_name_bar(bgr)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    h, w = gray.shape[:2]

    out = np.zeros((h, w), dtype=np.uint8)
    white = _white_ui_text_mask(gray, hsv)
    text = _name_text_for_identity(white)
    out[text] = 255
    return out


def template_to_preview_bgr(gray_or_bgr):
    """BGR image for GUI preview."""
    if gray_or_bgr is None or gray_or_bgr.size == 0:
        return None
    if gray_or_bgr.ndim == 2:
        return cv2.cvtColor(gray_or_bgr, cv2.COLOR_GRAY2BGR)
    return gray_or_bgr.copy()


def preview_bgr_for_entry(entry):
    """Preview of the saved capture (full region, not the processed match mask)."""
    raw = mob_template_store.load_template_bgr(entry)
    return template_to_preview_bgr(raw)


def prepare_template_for_storage(bgr):
    """Save the full captured region; matching normalization runs at compare time."""
    if bgr is None or bgr.size == 0:
        return None
    return bgr.copy()


def _prepare_scan_image(bgr):
    if getattr(config, 'mob_normalize_match', True):
        return normalize_for_match(bgr)
    gray = bgr if bgr.ndim == 2 else cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    return _crop_name_bar(gray)


def _scan_area_dict(area, default_height=NAME_H):
    """Copy a region dict; use default_height only when height is unset."""
    out = dict(area)
    h = int(out.get('height') or 0)
    if h <= 0:
        out['height'] = default_height
    return out


def get_name_bar_area():
    """Screen capture rect for mob Learn/Test/scan (uses the full picked region)."""
    if config.bar_area_configured(config.target_name_area):
        return _scan_area_dict(config.target_name_area)
    if config.bar_area_configured(config.mob_scan_area):
        return _scan_area_dict(config.mob_scan_area)
    rect = hp_number_reader.get_enemy_name_bar_rect(config.calibrator)
    if rect:
        x, y, w, h = rect
        return {'x': x, 'y': y, 'width': w, 'height': h}
    return _scan_area_dict(config.mob_scan_area)


def sync_scan_area_from_calibration():
    """Sync mob scan from manual enemy name pick or legacy calibrator."""
    import region_helpers
    if config.bar_area_configured(config.target_name_area):
        region_helpers.sync_mob_scan_from_enemy_name()
        return True
    cal = config.calibrator
    if not cal or not cal.enemy_name_area:
        return False
    area = get_name_bar_area()
    config.mob_scan_area.update(area)
    cx, cy, w, h = cal.enemy_name_area
    w, h = int(w), int(h)
    config.target_name_area['x'] = int(cx - w // 2)
    config.target_name_area['y'] = int(cy - h // 2)
    config.target_name_area['width'] = w
    config.target_name_area['height'] = h if h > 0 else NAME_H
    region_helpers.sync_mob_scan_from_enemy_name()
    return True


def get_scan_area():
    """Scan rect for Learn, Test match, and live mob filter (always name bar)."""
    return get_name_bar_area()


def scan_area_available():
    """True when manual or legacy calibration provides a valid scan region."""
    if config.bar_area_configured(config.mob_scan_area):
        return True
    if config.bar_area_configured(config.target_name_area):
        return True
    if config.calibrator and (
            config.calibrator.mp_position is not None
            or config.calibrator.enemy_name_area):
        return True
    return False


def _get_prepared_template(entry):
    key = entry.get('id')
    cache_key = f'prep_{key}'
    if cache_key in _template_cache:
        return _template_cache[cache_key]

    raw = mob_template_store.load_template_bgr(entry)
    if raw is None:
        return None

    # Legacy templates: grayscale corner mask saved on disk.
    if entry.get('normalized') and raw.ndim == 2:
        prep = _crop_name_bar(raw)
    elif getattr(config, 'mob_normalize_match', True):
        prep = normalize_for_match(raw)
        if prep is None:
            prep = cv2.cvtColor(_crop_name_bar(raw), cv2.COLOR_BGR2GRAY)
    else:
        prep = cv2.cvtColor(raw, cv2.COLOR_BGR2GRAY) if raw.ndim == 3 else _crop_name_bar(raw)
    _template_cache[cache_key] = prep
    return prep


def _capture_matches_size(img, width, height):
    if img is None or img.size == 0:
        return False
    ih, iw = img.shape[:2]
    return ih >= max(1, height - 1) and iw >= max(1, width - 1)


def capture_scan_area(hwnd):
    """Capture the configured scan rectangle (frame cache first, then direct crop)."""
    area = get_scan_area()
    x, y, w, h = area['x'], area['y'], area['width'], area['height']
    try:
        import frame_cache
        screen = frame_cache.get_frame(hwnd, config.calibrator)
        if screen is not None:
            crop = frame_cache.crop_rect(
                screen, x, y, x + w, y + h, frame_cache.get_origin(),
            )
            if _capture_matches_size(crop, w, h):
                return crop
    except Exception:
        pass
    img = window_utils.capture_window_region_bgr(hwnd, x, y, w, h)
    if _capture_matches_size(img, w, h):
        return img
    return img


def _align_width(gray, target_width):
    h, w = gray.shape[:2]
    if w == target_width:
        return gray
    return cv2.resize(gray, (target_width, h), interpolation=cv2.INTER_AREA)


def _signature_for_compare(gray):
    """
    Thicken UI strokes before comparing so small brightness/anti-alias shifts still match.
    Matching is visual (pixel shape), not text/OCR.
    """
    if gray is None or gray.size == 0:
        return gray
    dilate_px = int(getattr(config, 'mob_match_dilate_px', 1))
    if dilate_px <= 0:
        return gray
    fg = (gray > 0).astype(np.uint8)
    if not np.any(fg):
        return gray
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    region = cv2.dilate(fg, kernel, iterations=dilate_px)
    out = np.zeros_like(gray)
    out[region > 0] = 255
    return out


def _active_mask(scan_gray, template_gray, mask):
    """Pixels where both scan and template have foreground (tolerates small shifts)."""
    return mask & (scan_gray > 0) & (template_gray > 0)


def _name_region_cols(width):
    """Width of the name columns used for mob identity (excludes level digits)."""
    return _level_column_start(width)


def _bidirectional_name_score_core(scan_cmp, tmpl_cmp, *, cropped=True):
    """Bidirectional masked score on a name strip (no extra penalties)."""
    if cropped:
        le = _name_region_cols(tmpl_cmp.shape[1])
        sl, tl = scan_cmp[:, :le], tmpl_cmp[:, :le]
    else:
        sl, tl = scan_cmp, tmpl_cmp
    if tl.shape[1] != sl.shape[1]:
        tl = _align_width(tl, sl.shape[1])
    tmpl_mask = tl >= 250
    scan_mask = sl >= 250
    if not np.any(tmpl_mask) or not np.any(scan_mask):
        return 0.0
    forward = _masked_ccoeff(sl, tl, tmpl_mask)
    backward = _masked_ccoeff(sl, tl, scan_mask)
    return min(forward, backward)


def _bidirectional_name_score(scan_cmp, tmpl_cmp, raw_scan=None, raw_tmpl=None):
    """
    Score the mob name (left column) only, both directions.

    Pixel agreement uses raw text masks; shape similarity uses dilated signatures
    (tolerates anti-alias). Prefix-agnostic for any shared-prefix mob names.
    """
    le = _name_region_cols(tmpl_cmp.shape[1])
    sl, tl = scan_cmp[:, :le], tmpl_cmp[:, :le]
    if tl.shape[1] != sl.shape[1]:
        tl = _align_width(tl, sl.shape[1])
    base = _bidirectional_name_score_core(scan_cmp, tmpl_cmp)
    if raw_scan is not None and raw_tmpl is not None:
        raw_tl = raw_tmpl[:, :le] if raw_tmpl.shape[1] == le else _align_width(raw_tmpl[:, :le], le)
        raw_sl = raw_scan[:, :le] if raw_scan.shape[1] == le else _align_width(raw_scan[:, :le], le)
        return min(base, _column_shape_penalty(raw_sl, raw_tl, base))
    return min(base, _column_shape_penalty(sl, tl, base))


def _column_agreement_ratio(scan_gray, tmpl_gray):
    """
    Fraction of name columns where both strips agree (prefix-agnostic).

    Works for any shared-prefix mobs (Ban X / Ban Y, Ancient A / Ancient B, etc.)
    by comparing the full name width column-by-column, not a fixed text prefix.
    """
    scan_fg = scan_gray > 0
    tmpl_fg = tmpl_gray > 0
    either = scan_fg.any(axis=0) | tmpl_fg.any(axis=0)
    if not np.any(either):
        return 1.0
    iou_min = float(getattr(config, 'mob_match_column_iou_min', 0.62))
    agrees = 0
    compared = 0
    for c in range(scan_gray.shape[1]):
        if not either[c]:
            continue
        compared += 1
        s_col = scan_fg[:, c]
        t_col = tmpl_fg[:, c]
        union = int((s_col | t_col).sum())
        if union == 0:
            agrees += 1
            continue
        overlap = int((s_col & t_col).sum())
        if overlap / union >= iou_min:
            agrees += 1
    return agrees / compared if compared else 1.0


def _column_shape_penalty(scan_gray, tmpl_gray, base_score):
    """Scale score down when many name columns disagree between scan and template."""
    if base_score < 0.4:
        return base_score
    agreement = _column_agreement_ratio(scan_gray, tmpl_gray)
    min_agreement = float(getattr(config, 'mob_match_min_column_agreement', 0.70))
    if agreement >= min_agreement:
        return base_score
    return base_score * (agreement / min_agreement)


def _masked_ccoeff(scan_gray, template_gray, mask, min_coverage=None):
    """Similarity on masked pixels; uses agreement when template level is uniform."""
    if mask is None or not np.any(mask):
        return 0.0
    if min_coverage is None:
        min_coverage = float(getattr(config, 'mob_match_min_coverage', 0.50))
    pixel_tol = float(getattr(config, 'mob_match_pixel_tolerance', 4))
    use = _active_mask(scan_gray, template_gray, mask)
    coverage = float(use.sum()) / float(max(1, mask.sum()))
    if coverage < min_coverage:
        return 0.0
    s = scan_gray[use].astype(np.float64)
    t = template_gray[use].astype(np.float64)
    if s.size < 12:
        return 0.0
    if np.std(t) < 1e-6:
        target = float(np.median(t))
        raw = float(np.mean(np.abs(s - target) <= pixel_tol))
    elif np.std(s) < 1e-6:
        target = float(np.median(s))
        raw = float(np.mean(np.abs(t - target) <= pixel_tol))
    else:
        s -= s.mean()
        t -= t.mean()
        denom = np.linalg.norm(s) * np.linalg.norm(t)
        if denom < 1e-9:
            return 0.0
        raw = float(np.clip(np.dot(s, t) / denom, -1.0, 1.0))
    return float(raw * (0.55 + 0.45 * coverage))


def _effective_shift_px():
    shift_px = int(getattr(config, 'mob_match_shift_px', 2))
    if config.enemy_target_time > 0:
        shift_px = min(shift_px, int(getattr(config, 'mob_combat_shift_px', 1)))
    return shift_px


def _get_template_shift_variants(tmpl_cmp, tmpl_raw, entry, shift_px):
    """Precomputed template shifts (avoids per-frame scan warping)."""
    if entry is None:
        return [(tmpl_cmp, tmpl_raw)]
    cache_key = f'shifts_{entry.get("id")}_{shift_px}'
    if cache_key in _template_cache:
        return _template_cache[cache_key]

    variants = []
    h, w = tmpl_cmp.shape[:2]
    for dy in range(-shift_px, shift_px + 1):
        for dx in range(-shift_px, shift_px + 1):
            if dx == 0 and dy == 0:
                variants.append((tmpl_cmp, tmpl_raw))
                continue
            M = np.float32([[1, 0, -dx], [0, 1, -dy]])
            shifted_cmp = cv2.warpAffine(
                tmpl_cmp, M, (w, h), borderMode=cv2.BORDER_CONSTANT, borderValue=0,
            )
            shifted_raw = cv2.warpAffine(
                tmpl_raw, M, (w, h), borderMode=cv2.BORDER_CONSTANT, borderValue=0,
            )
            variants.append((shifted_cmp, shifted_raw))
    _template_cache[cache_key] = variants
    return variants


def _match_score_gray(scan_gray, template_gray, hwnd=None, entry=None, screen=None):
    """Compare normalized name-bar signatures (foreground pixels only)."""
    _ = (hwnd, screen)  # elite check runs after match via apply_elite_filter
    if scan_gray is None or template_gray is None:
        return 0.0
    if scan_gray.size == 0 or template_gray.size == 0:
        return 0.0

    scan_name = _crop_name_bar(scan_gray)
    tmpl_name = _align_width(_crop_name_bar(template_gray), scan_name.shape[1])
    shift_px = _effective_shift_px()

    def _combined_score(scan_img, tmpl_img):
        scan_cmp = _signature_for_compare(scan_img)
        tmpl_cmp = _signature_for_compare(tmpl_img)
        if not np.any(tmpl_cmp > 0) or not np.any(scan_cmp > 0):
            return 0.0

        def _score(s_cmp, t_cmp, s_raw, t_raw):
            return _bidirectional_name_score(s_cmp, t_cmp, s_raw, t_raw)

        variants = _get_template_shift_variants(tmpl_cmp, tmpl_img, entry, shift_px)
        best_local = 0.0
        for t_cmp, t_raw in variants:
            best_local = max(best_local, _score(scan_cmp, t_cmp, scan_img, t_raw))
        return float(np.clip(best_local, 0.0, 1.0))

    return _combined_score(scan_name, tmpl_name)


def _collect_scores(scan_bgr, templates=None, hwnd=None, screen=None):
    templates = templates if templates is not None else config.mob_templates
    scan_gray = _prepare_scan_image(scan_bgr)
    if scan_gray is None:
        return []

    scores = []
    for entry in templates:
        template_gray = _get_prepared_template(entry)
        if template_gray is None:
            continue
        confidence = _match_score_gray(
            scan_gray, template_gray, hwnd=hwnd, entry=entry, screen=screen,
        )
        scores.append((confidence, entry))
    scores.sort(key=lambda item: item[0], reverse=True)
    return scores


def match_in_image(scan_bgr, templates=None, hwnd=None, screen=None):
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
    scores = _collect_scores(scan_bgr, templates, hwnd=hwnd, screen=screen)
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


def template_has_hp_profile(entry):
    """True when Learn saved a max-HP signature for elite skip."""
    if not entry:
        return False
    return bool(entry.get('hp_max_file')) or mob_template_store.load_hp_max_sig(entry) is not None


def build_hp_profile(hwnd, screen=None):
    """Capture HP number strip and build reference profile for a learned normal mob."""
    analysis = hp_number_reader.capture_and_analyze(hwnd, screen=screen)
    if not analysis or not analysis.get('has_text'):
        return {}
    profile = {}
    sig = analysis.get('max_hp_sig')
    if sig is not None and sig.size > 0:
        profile['max_hp_sig'] = sig
    return profile


def is_elite_variant(hwnd, entry, screen=None):
    """
    True when the target looks like an elite: same name but different max HP digits.
    Requires a max-HP signature saved at Learn (normal mob at full HP).
    """
    if not config.mob_elite_skip_enabled or not entry:
        return False
    ref_sig = mob_template_store.load_hp_max_sig(entry)
    if ref_sig is None:
        return False
    strip = hp_number_reader.capture_enemy_hp_text_area(hwnd, screen=screen)
    sample_sig = hp_number_reader.build_max_hp_signature(strip)
    if sample_sig is None:
        return False
    matched, score = hp_number_reader.signatures_match(
        ref_sig, sample_sig, threshold=config.mob_elite_sig_threshold,
    )
    if not matched:
        print(
            f"[Mob Filter] Elite skip: max HP signature mismatch "
            f"({score:.0%} < {config.mob_elite_sig_threshold:.0%})"
        )
        return True
    return False


def apply_elite_filter(hwnd, match, screen=None):
    """Drop a name match when the target is an elite variant (higher max HP)."""
    if not match:
        return None
    entry = mob_template_store.find_by_id(match.get('id'))
    if entry and is_elite_variant(hwnd, entry, screen=screen):
        return None
    return match


def probe(hwnd):
    """
    Test scan without requiring mob filter to be enabled.
    Returns dict with match info and best score for UI feedback.
    """
    if not scan_area_available():
        return {'error': 'Set Enemy Name in Region Editor for the mob scan area'}
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

    scores = _collect_scores(scan_bgr, hwnd=hwnd)
    raw_match = match_in_image(scan_bgr, hwnd=hwnd)
    match = apply_elite_filter(hwnd, raw_match)
    best_conf = scores[0][0] if scores else 0.0
    best_name = scores[0][1].get('name', '?') if scores else '?'
    return {
        'match': match,
        'best_score': best_conf,
        'best_name': best_name,
        'threshold': config.mob_match_threshold,
        'scan_size': (scan_bgr.shape[1], scan_bgr.shape[0]),
        'elite_skipped': bool(raw_match and not match),
        'normalized': getattr(config, 'mob_normalize_match', True),
    }


def compare_live_to_entry(hwnd, entry, screen=None):
    """
    Compare current live scan (capture) against one specific template entry.

    Returns a dict suitable for GUI debugging:
      - scan_bgr / template_bgr: raw captures (BGR)
      - scan_norm / template_norm: normalized match masks (grayscale, 0/255)
      - score: final score in [0..1]
      - column_agreement: name-column agreement ratio (0..1)
    """
    if not hwnd:
        return {'error': 'No window handle'}
    if entry is None:
        return {'error': 'No template selected'}
    if not scan_area_available():
        return {'error': 'Set Enemy Name in Region Editor first'}

    scan_bgr = capture_scan_area(hwnd)
    if scan_bgr is None or scan_bgr.size == 0:
        return {'error': 'Could not capture live scan region'}

    template_bgr = mob_template_store.load_template_bgr(entry)
    if template_bgr is None or template_bgr.size == 0:
        return {'error': 'Template image missing (re-learn it)'}

    scan_norm = _prepare_scan_image(scan_bgr)
    template_norm = _get_prepared_template(entry)
    if scan_norm is None or template_norm is None or scan_norm.size == 0 or template_norm.size == 0:
        return {'error': 'Could not prepare images for comparison'}

    score = _match_score_gray(scan_norm, template_norm, hwnd=hwnd, entry=entry, screen=screen)

    # Column agreement is computed on the name region (raw masks, no dilation).
    scan_name = _crop_name_bar(scan_norm)
    tmpl_name = _align_width(_crop_name_bar(template_norm), scan_name.shape[1])
    le = _name_region_cols(tmpl_name.shape[1])
    scan_cols = scan_name[:, :le]
    tmpl_cols = tmpl_name[:, :le] if tmpl_name.shape[1] == le else _align_width(tmpl_name[:, :le], le)
    column_agreement = _column_agreement_ratio(scan_cols, tmpl_cols)

    return {
        'scan_bgr': scan_bgr,
        'template_bgr': template_bgr,
        'scan_norm': scan_norm,
        'template_norm': template_norm,
        'score': float(score),
        'column_agreement': float(column_agreement),
        'threshold': float(config.mob_match_threshold),
        'normalized': getattr(config, 'mob_normalize_match', True),
    }


def clear_match():
    """Clear mob filter match state (e.g. when no enemy is targeted)."""
    lock = getattr(config, 'mob_detection_lock', None)
    if lock is not None:
        with lock:
            _clear_match_unlocked()
        return
    _clear_match_unlocked()


def _clear_match_unlocked():
    config.current_mob_match = None
    config.current_target_mob = None
    config.current_enemy_name = None
    config.mob_match_miss_streak = 0


def _apply_match(match):
    config.current_mob_match = match
    try:
        import time as _time
        config.current_mob_match_time = _time.time() if match else 0.0
    except Exception:
        pass
    if match:
        config.current_target_mob = match['name']
        config.current_enemy_name = match['name']
    else:
        config.current_target_mob = None
        config.current_enemy_name = None


def refresh_scan_stable(hwnd, *, attempts=None, required=None, delay_s=None):
    """
    Conservative mob verification for transparent UI backgrounds.

    Captures multiple scans and requires a stable majority of the same template id.
    This is slower than `refresh_scan()` but avoids false-positive single-frame matches.
    """
    if attempts is None:
        attempts = int(getattr(config, 'mob_verify_attempts', 3))
    if required is None:
        required = int(getattr(config, 'mob_verify_required', 2))
    if delay_s is None:
        delay_s = float(getattr(config, 'mob_verify_delay_s', 0.06))

    if attempts <= 0:
        return refresh_scan(hwnd)

    if not is_active() or not hwnd:
        clear_match()
        return None

    # Collect (id, matchdict) for successful frames.
    hits = []
    for i in range(attempts):
        m = refresh_scan(hwnd)
        if m and m.get('id'):
            hits.append(m)
        if i < attempts - 1 and delay_s > 0:
            import time
            time.sleep(delay_s)

    if not hits:
        clear_match()
        return None

    # Majority vote by template id.
    counts = {}
    best = None
    for m in hits:
        mid = m.get('id')
        counts[mid] = counts.get(mid, 0) + 1
        if best is None or counts[mid] > counts.get(best.get('id'), 0):
            best = m

    best_id = best.get('id') if best else None
    best_count = counts.get(best_id, 0)
    if best_id is None or best_count < required:
        clear_match()
        return None

    # Be conservative: use the lowest confidence among frames that voted for this id.
    confs = [float(m.get('confidence', 0.0)) for m in hits if m.get('id') == best_id]
    best_conf = min(confs) if confs else float(best.get('confidence', 0.0))
    stable = dict(best)
    stable['confidence'] = best_conf
    _apply_match(stable)
    return stable


def _run_scan(hwnd):
    """Capture and match without updating config."""
    if not is_active() or not hwnd:
        return None
    sync_scan_area_from_calibration()
    scan_bgr = capture_scan_area(int(hwnd))
    if scan_bgr is None or scan_bgr.size == 0:
        return None
    raw_match = match_in_image(scan_bgr, hwnd=int(hwnd))
    match = apply_elite_filter(int(hwnd), raw_match)
    if raw_match and not match:
        print("[Mob Filter] Elite mob skipped (higher max HP than learned normal)")
    return match


def _with_mob_lock(fn, hwnd):
    lock = getattr(config, 'mob_detection_lock', None)
    if lock is not None:
        with lock:
            return fn(hwnd)
    return fn(hwnd)


def refresh_scan(hwnd):
    """Capture scan region and update config.current_mob_match."""
    def _do(hwnd):
        if not is_active():
            _clear_match_unlocked()
            return None
        if not hwnd:
            _clear_match_unlocked()
            return None
        match = _run_scan(hwnd)
        if match is None:
            _clear_match_unlocked()
            return None
        config.mob_match_miss_streak = 0
        _apply_match(match)
        return match

    return _with_mob_lock(_do, hwnd)


def refresh_scan_combat(hwnd):
    """
    Combat mob scan: tolerate brief single-frame misses when a match was established.
    """
    import time as _time

    def _do(hwnd):
        if not is_active():
            _clear_match_unlocked()
            return None
        if not hwnd:
            _clear_match_unlocked()
            return None

        prev_match = config.current_mob_match
        had_match = prev_match is not None
        engaged = config.enemy_target_time > 0
        grace_s = float(getattr(config, 'mob_combat_match_grace_seconds', 0.3))
        match_time = float(getattr(config, 'current_mob_match_time', 0) or 0)
        in_grace = (
            engaged and had_match and match_time > 0
            and (_time.time() - match_time) < grace_s
        )

        match = _run_scan(hwnd)
        if match:
            config.mob_match_miss_streak = 0
            _apply_match(match)
            return match

        if in_grace and prev_match:
            return prev_match

        if engaged and had_match:
            required = int(getattr(config, 'mob_combat_miss_required', 2))
            config.mob_match_miss_streak = int(getattr(config, 'mob_match_miss_streak', 0)) + 1
            if config.mob_match_miss_streak < required:
                return prev_match

        config.mob_match_miss_streak = 0
        _apply_match(None)
        return None

    return _with_mob_lock(_do, hwnd)


def scan(hwnd):
    """Scan the configured region for any learned mob template."""
    if not is_active():
        clear_match()
        return None
    return refresh_scan(hwnd)


_COMBAT_ENEMY_HP_MIN = 3.0


def is_engaged_in_combat():
    """True while fighting, looting, or enemy HP bar is still tracked."""
    if config.is_looting:
        return True
    if float(getattr(config, 'enemy_target_time', 0) or 0) > 0:
        return True
    if len(getattr(config, 'enemy_hp_readings', [])) > 0:
        return True
    hp = float(getattr(config, 'current_enemy_hp_percentage', 0) or 0)
    return hp > _COMBAT_ENEMY_HP_MIN


def should_allow_buffs():
    """Buffs when mob filter is on — only between kills / with no target (pots are always allowed)."""
    if not is_active():
        return True
    if not getattr(config, 'mob_filter_safe_buffs', True):
        return True
    return not is_engaged_in_combat()


def _clear_combat_target_state():
    """Drop CV mob match and enemy tracking after focusing self."""
    clear_match()
    config.enemy_target_time = 0
    config.enemy_hp_readings.clear()
    config.current_enemy_hp_percentage = 0.0
    config.current_target_mob = None
    config.current_enemy_name = None
    config.enemy_name_missing_streak = 0


def focus_self_target():
    """Press the self-target key so heals/buffs hit your character, not the mob."""
    if not getattr(config, 'mob_detection_enabled', False):
        return False
    key = (getattr(config, 'self_target_key', '') or '').strip()
    if not key:
        return False
    import input_handler
    import time
    input_handler.send_input(key)
    delay = float(getattr(config, 'SELF_TARGET_DELAY', 0.2))
    if delay > 0:
        time.sleep(delay)
    _clear_combat_target_state()
    return True


def focus_self_before_retarget():
    """Clear mob target before pressing the target key (mob filter)."""
    if not getattr(config, 'mob_detection_enabled', False):
        return False
    if not getattr(config, 'self_target_before_retarget', True):
        return False
    return focus_self_target()


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
