"""Bar fill color calibration from user samples (Region Editor)."""
import cv2
import numpy as np

KIND_HP = 'hp'
KIND_MP = 'mp'
KIND_ENEMY_HP = 'enemy_hp'

CONFIG_KEYS = {
    KIND_HP: 'hp_bar_color_cal',
    KIND_MP: 'mp_bar_color_cal',
    KIND_ENEMY_HP: 'target_hp_bar_color_cal',
}

REGION_KEYS = {
    KIND_HP: 'hp_bar_area',
    KIND_MP: 'mp_bar_area',
    KIND_ENEMY_HP: 'target_hp_bar_area',
}


def empty_calibration():
    return {'enabled': False}


def copy_calibration(cal):
    if not cal or not isinstance(cal, dict):
        return empty_calibration()
    return dict(cal)


def is_enabled(cal):
    return bool(cal and cal.get('enabled'))


def median_hsv_at(bgr, x, y, radius=2):
    """Median HSV of a small patch (OpenCV H: 0-180, S/V: 0-255)."""
    if bgr is None or bgr.size == 0:
        return None
    h, w = bgr.shape[:2]
    x0 = max(0, int(x) - radius)
    x1 = min(w, int(x) + radius + 1)
    y0 = max(0, int(y) - radius)
    y1 = min(h, int(y) + radius + 1)
    patch = bgr[y0:y1, x0:x1]
    if patch.size == 0:
        return None
    hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
    med = np.median(hsv.reshape(-1, 3), axis=0)
    return int(med[0]), int(med[1]), int(med[2])


def _region_for_auto_sample(region, kind):
    """Prefer bar rows when the capture includes extra padding or a name row."""
    if region is None or region.size == 0:
        return region
    import ui_bar_detection

    if kind == KIND_ENEMY_HP:
        probe = ui_bar_detection.build_enemy_red_mask(
            region,
            sat_min=70,
            val_min=55,
            hue_max=14,
        )
    elif kind == KIND_MP:
        probe = ui_bar_detection.build_blue_mask(region)
    else:
        probe = ui_bar_detection.build_enemy_red_mask(region, sat_min=85, val_min=65, hue_max=14)

    bands, _ = ui_bar_detection.find_bar_bands(probe)
    if bands:
        _bx, by, bw, bh = max(bands, key=lambda item: item[2])
        if bw >= 10 and bh >= 4:
            return region[by:by + bh, :]
    return region


def _candidate_pixels(hsv, kind, sat_min=None):
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    if kind == KIND_MP:
        if sat_min is None:
            sat_min = 50
        return hsv[(hue >= 95) & (hue <= 140) & (sat >= sat_min) & (val >= 50)]
    if sat_min is None:
        sat_min = 80 if kind == KIND_ENEMY_HP else 60
    mask = ((hue <= 14) | (hue >= 165)) & (sat >= sat_min) & (val >= 55)
    return hsv[mask]


def auto_sample_hsv(region, kind):
    """
    Pick glossy bar-fill HSV from a configured region (no user click).

    Uses the most saturated in-bar pixels so transparent empty slots / floor bleed
    are ignored.
    """
    work = _region_for_auto_sample(region, kind)
    if work is None or work.size == 0:
        return None
    hsv = cv2.cvtColor(work, cv2.COLOR_BGR2HSV)
    min_count = max(15, work.shape[0] * work.shape[1] // 40)

    pixels = _candidate_pixels(hsv, kind)
    if len(pixels) < min_count:
        pixels = _candidate_pixels(hsv, kind, sat_min=45)
    if len(pixels) < min_count:
        return None

    sat_thresh = float(np.percentile(pixels[:, 1], 60))
    glossy = pixels[pixels[:, 1] >= sat_thresh]
    if len(glossy) < 10:
        glossy = pixels
    med = np.median(glossy, axis=0)
    return int(med[0]), int(med[1]), int(med[2])


def calibrate_from_hsv(hue, sat, val, kind):
    """Build an HSV range profile from a single representative HSV sample."""
    if kind == KIND_MP:
        return {
            'enabled': True,
            'kind': KIND_MP,
            'h_lo': max(90, hue - 12),
            'h_hi': min(140, hue + 12),
            's_lo': max(50, sat - 55),
            's_hi': 255,
            'v_lo': max(55, val - 65),
            'v_hi': 255,
            'sample_h': hue,
            'sample_s': sat,
            'sample_v': val,
            'min_row_fraction': 0.35,
        }

    enemy = kind == KIND_ENEMY_HP
    h_tol = 10
    s_tol = 45 if enemy else 55
    v_tol = 65
    s_floor = 90 if enemy else 50

    cal = {
        'enabled': True,
        'kind': kind,
        's_lo': max(s_floor, sat - s_tol),
        's_hi': 255,
        'v_lo': max(55, val - v_tol),
        'v_hi': 255,
        'sample_h': hue,
        'sample_s': sat,
        'sample_v': val,
        'min_row_fraction': 0.5 if enemy else 0.45,
    }

    if hue >= 165:
        cal['hue_wrap'] = True
        cal['h_lo'] = max(165, hue - h_tol)
        cal['h_hi'] = 180
        cal['h_lo2'] = 0
        cal['h_hi2'] = min(14, hue - 165 + h_tol)
    else:
        cal['hue_wrap'] = hue <= 14
        cal['h_lo'] = max(0, hue - h_tol)
        cal['h_hi'] = min(14, hue + h_tol)
        if cal['hue_wrap']:
            cal['h_lo2'] = 165
            cal['h_hi2'] = 180

    return cal


def calibrate_from_click(bgr, x, y, kind):
    """Build an HSV range from a click on the filled portion of a bar."""
    sample = median_hsv_at(bgr, x, y)
    if sample is None:
        return empty_calibration()
    return calibrate_from_hsv(*sample, kind)


def auto_calibrate_from_region(region, kind):
    """Derive bar color profile automatically from a configured region capture."""
    sample = auto_sample_hsv(region, kind)
    if sample is None:
        return empty_calibration()
    cal = calibrate_from_hsv(*sample, kind)
    cal['auto'] = True
    return cal


def build_mask(bgr, cal):
    """Binary mask of pixels matching a calibration profile."""
    if not is_enabled(cal) or bgr is None or bgr.size == 0:
        return None

    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    h_ch = hsv[:, :, 0]
    s_ch = hsv[:, :, 1]
    v_ch = hsv[:, :, 2]

    s_lo = int(cal['s_lo'])
    s_hi = int(cal.get('s_hi', 255))
    v_lo = int(cal['v_lo'])
    v_hi = int(cal.get('v_hi', 255))
    sat_ok = (s_ch >= s_lo) & (s_ch <= s_hi) & (v_ch >= v_lo) & (v_ch <= v_hi)

    kind = cal.get('kind', KIND_HP)
    if kind == KIND_MP:
        h_lo = int(cal['h_lo'])
        h_hi = int(cal['h_hi'])
        mask = (h_ch >= h_lo) & (h_ch <= h_hi) & sat_ok
    else:
        h_lo = int(cal['h_lo'])
        h_hi = int(cal['h_hi'])
        mask = (h_ch >= h_lo) & (h_ch <= h_hi) & sat_ok
        if cal.get('hue_wrap') and 'h_lo2' in cal:
            h_lo2 = int(cal['h_lo2'])
            h_hi2 = int(cal['h_hi2'])
            mask = mask | ((h_ch >= h_lo2) & (h_ch <= h_hi2) & sat_ok)

    return mask.astype(np.uint8) * 255


def _isolate_bar_rows(region, cal, kind):
    """Crop to HP bar rows; keep full width for fill denominator."""
    import bar_reader
    import ui_bar_detection

    if is_enabled(cal):
        strict = build_mask(region, cal)
        if strict is not None:
            bands, _ = ui_bar_detection.find_bar_bands(strict)
            if bands:
                _bx, by, bw, bh = max(bands, key=lambda item: item[2])
                if bw >= 10 and bh >= 4:
                    return region[by:by + bh, :]
    if kind == KIND_ENEMY_HP:
        sat_min = int(getattr(__import__('config'), 'enemy_hp_red_sat_min', 90))
        val_min = int(getattr(__import__('config'), 'enemy_hp_red_val_min', 80))
        hue_max = int(getattr(__import__('config'), 'enemy_hp_red_hue_max', 12))
        return bar_reader._isolate_hp_bar_band(region, sat_min, val_min, hue_max)
    return bar_reader._isolate_hp_bar_band(region)


def _isolate_enemy_rows(region, cal):
    return _isolate_bar_rows(region, cal, KIND_ENEMY_HP)


def percent_from_region(region, cal, kind):
    """Return fill percentage using a calibration profile, or None if disabled."""
    if region is None or region.size == 0 or not is_enabled(cal):
        return None

    import bar_reader

    work = region
    if kind in (KIND_ENEMY_HP, KIND_HP):
        work = _isolate_bar_rows(region, cal, kind)
        if work is None or work.size == 0:
            return 0.0

    mask = build_mask(work, cal)
    if mask is None:
        return None
    min_frac = float(cal.get('min_row_fraction', 0.35))
    pct = bar_reader.bar_fill_percent_from_mask(mask, min_row_fraction=min_frac)
    if kind == KIND_HP:
        return bar_reader._blend_hp_with_text(region, mask, pct)
    if kind == KIND_ENEMY_HP:
        return bar_reader._blend_enemy_hp_with_text(region, work, mask, pct)
    return pct


def calibration_summary(cal):
    """Short status string for the Region Editor sidebar."""
    if not is_enabled(cal):
        return 'Color: not calibrated'
    h, s, v = cal.get('sample_h', 0), cal.get('sample_s', 0), cal.get('sample_v', 0)
    prefix = 'auto' if cal.get('auto') else 'custom'
    return f'Color: {prefix} H{h} S{s} V{v}'


def _probe_mask_for_kind(bgr, kind):
    import ui_bar_detection

    if kind in (KIND_HP, KIND_ENEMY_HP):
        sat = 70 if kind == KIND_ENEMY_HP else 85
        val = 55 if kind == KIND_ENEMY_HP else 65
        return ui_bar_detection.build_enemy_red_mask(bgr, sat_min=sat, val_min=val, hue_max=14)
    if kind == KIND_MP:
        return ui_bar_detection.build_blue_mask(bgr)
    return ui_bar_detection.build_red_mask(bgr)


def _snap_probe_mask(bgr, kind):
    """Strict masks for snap — loose player red mask false-positives floor in empty MP slots."""
    import ui_bar_detection

    if kind == KIND_MP:
        return ui_bar_detection.build_blue_mask(bgr)
    return ui_bar_detection.build_enemy_red_mask(bgr, sat_min=80, val_min=60, hue_max=14)


def _band_mean_saturation(bgr, band):
    bx, by, bw, bh = band
    crop = bgr[by:by + bh, bx:bx + bw]
    if crop.size == 0:
        return 0.0
    return float(cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)[:, :, 1].mean())


def _bands_overlap_x(a, b, ratio=0.35):
    ax, _, aw, _ = a
    bx, _, bw, _ = b
    overlap = min(ax + aw, bx + bw) - max(ax, bx)
    if overlap <= 0:
        return False
    return overlap / float(min(aw, bw)) >= ratio


def _filter_snap_bands(bands, bgr, kind):
    """Drop floor-bleed strips and tiny artifacts before picking a snap target."""
    import ui_bar_detection

    if not bands:
        return []
    ew = bgr.shape[1]
    min_sat = 70 if kind in (KIND_HP, KIND_ENEMY_HP) else 45
    filtered = []
    for band in bands:
        _bx, _by, bw, bh = band
        if bw < 35 or bh < 4 or bh > ui_bar_detection.BAR_MAX_HEIGHT + 8:
            continue
        sat = _band_mean_saturation(bgr, band)
        if sat < min_sat:
            continue
        if bw >= int(ew * 0.94) and sat < 120:
            continue
        filtered.append(band)
    return filtered


def _trim_band_width_from_mask(bgr, band, mask):
    """Tighten band width using actual mask columns (bars inset in the UI frame)."""
    bx, by, bw, bh = band
    strip = mask[by:by + bh, bx:bx + bw]
    if strip.size == 0:
        return band
    col_fill = (strip > 0).sum(axis=0)
    min_px = max(1, int(bh * 0.45))
    cols = np.where(col_fill >= min_px)[0]
    if len(cols) < 4:
        return band
    x0 = bx + int(cols[0])
    x1 = bx + int(cols[-1]) + 1
    return (x0, by, x1 - x0, bh)


def _pick_hp_snap_band(bands, expanded, cx, cy, ex1, ey1):
    """
    Pick the HP row in stacked target UI (name + red HP + blue MP).

    When MP is visible, HP is the saturated red band directly above it.
    When MP is hidden, pick the topmost qualifying band near the box center.
    """
    import ui_bar_detection

    blue_bands = _filter_snap_bands(
        ui_bar_detection.find_bar_bands(ui_bar_detection.build_blue_mask(expanded))[0],
        expanded,
        KIND_MP,
    )
    if blue_bands:
        mp = min(blue_bands, key=lambda item: item[1])
        mp_top = mp[1]
        candidates = []
        for red in bands:
            _rx, ry, _rw, rh = red
            gap = mp_top - (ry + rh)
            if gap < -3 or gap > ui_bar_detection.HP_MP_MAX_GAP + 4:
                continue
            if _bands_overlap_x(red, mp):
                candidates.append(red)
        if candidates:
            red = min(
                candidates,
                key=lambda b: (
                    abs((ey1 + b[1] + b[3] // 2) - cy)
                    + abs((ex1 + b[0] + b[2] // 2) - cx),
                ),
            )
            # Target UI: HP and MP share the same horizontal inset — use MP width.
            return (mp[0], red[1], mp[2], red[3])

    def _score(band):
        _bx, by, _bw, bh = band
        dist = abs((ey1 + by + bh // 2) - cy) + abs((ex1 + _bx) - cx)
        return (by, dist)

    return min(bands, key=_score)


def snap_area_to_bar(bgr, area, kind, padding=1, search_pad=12):
    """
    Shrink a region rectangle onto the detected bar band (image coordinates).

    Returns a new area dict or None when no bar is found.
    """
    if bgr is None or bgr.size == 0 or not area:
        return None
    x = int(area.get('x', 0))
    y = int(area.get('y', 0))
    w = int(area.get('width', 0))
    h = int(area.get('height', 0))
    if w <= 0 or h <= 0:
        return None

    img_h, img_w = bgr.shape[:2]
    cx, cy = x + w // 2, y + h // 2
    ex1 = max(0, x - search_pad)
    ey1 = max(0, y - search_pad)
    ex2 = min(img_w, x + w + search_pad)
    ey2 = min(img_h, y + h + search_pad)
    expanded = bgr[ey1:ey2, ex1:ex2]
    if expanded.size == 0:
        return None

    import ui_bar_detection

    bands, _ = ui_bar_detection.find_bar_bands(_snap_probe_mask(expanded, kind))
    bands = _filter_snap_bands(bands, expanded, kind)
    if not bands:
        return None

    snap_mask = _snap_probe_mask(expanded, kind)
    if kind in (KIND_HP, KIND_ENEMY_HP):
        bx, by, bw, bh = _pick_hp_snap_band(bands, expanded, cx, cy, ex1, ey1)
        blue_present = bool(
            _filter_snap_bands(
                ui_bar_detection.find_bar_bands(
                    ui_bar_detection.build_blue_mask(expanded),
                )[0],
                expanded,
                KIND_MP,
            )
        )
        if not blue_present:
            bx, by, bw, bh = _trim_band_width_from_mask(
                expanded, (bx, by, bw, bh), snap_mask,
            )
    else:
        def _dist(band):
            _bx, _by, _bw, _bh = band
            bcx = ex1 + _bx + _bw // 2
            bcy = ey1 + _by + _bh // 2
            return abs(bcx - cx) + abs(bcy - cy)

        bx, by, bw, bh = min(bands, key=_dist)
    nx = ex1 + bx
    ny = max(0, ey1 + by - padding)
    nw = min(img_w - nx, bw)
    nh = min(img_h - ny, bh + padding * 2)
    if nw < 10 or nh < 4:
        return None
    return {'x': nx, 'y': ny, 'width': nw, 'height': nh}


def fill_mask_overlay(bgr, cal, kind):
    """BGR preview with green tint on pixels counted as bar fill."""
    if bgr is None or bgr.size == 0:
        return bgr
    out = bgr.copy()
    work = bgr
    y_off = 0
    if kind in (KIND_HP, KIND_ENEMY_HP) and is_enabled(cal):
        work = _isolate_bar_rows(bgr, cal, kind)
        import ui_bar_detection
        bands, _ = ui_bar_detection.find_bar_bands(_probe_mask_for_kind(bgr, kind))
        y_off = bands[0][1] if bands else 0
    mask = build_mask(work, cal) if is_enabled(cal) else _probe_mask_for_kind(work, kind)
    if mask is None:
        return out
    h = min(work.shape[0], mask.shape[0], out.shape[0] - y_off)
    w = min(bgr.shape[1], mask.shape[1])
    roi = out[y_off:y_off + h, :w]
    m = mask[:h, :w] > 0
    green = np.zeros_like(roi)
    green[:, :, 1] = 180
    roi[m] = cv2.addWeighted(roi, 0.5, green, 0.5, 0)[m]
    out[y_off:y_off + h, :w] = roi
    return out


def preview_percent_for_area(bgr, area, cal, kind):
    """Fill % for a screen area using calibration or defaults."""
    if bgr is None or area is None or int(area.get('width', 0)) <= 0:
        return None
    crop = bgr[
        int(area['y']):int(area['y']) + int(area['height']),
        int(area['x']):int(area['x']) + int(area['width']),
    ]
    if crop.size == 0:
        return None
    if is_enabled(cal):
        return percent_from_region(crop, cal, kind)
    import bar_reader
    if kind == KIND_MP:
        return bar_reader.mp_percent_from_bgr(crop)
    if kind == KIND_ENEMY_HP:
        return bar_reader.enemy_hp_percent_from_bgr(crop)
    return bar_reader.hp_percent_from_bgr(crop)


def collect_region_warnings(areas, bgr, color_cals, label_for):
    """Return human-readable warnings before saving bar regions."""
    warnings = []
    if bgr is None:
        return warnings
    for kind, area_key in REGION_KEYS.items():
        if area_key not in areas:
            continue
        area = areas[area_key]
        if int(area.get('width', 0)) <= 0:
            continue
        cal = color_cals.get(kind) if color_cals else None
        pct = preview_percent_for_area(bgr, area, cal, kind)
        label = label_for(area_key) if label_for else area_key
        if pct is None:
            warnings.append(f'{label}: could not read fill % — check capture and box placement.')
        elif pct <= 0.5:
            warnings.append(f'{label}: reads 0% — box may be off the bar or capture is too dark.')
        elif pct >= 99.5:
            warnings.append(
                f'{label}: reads 100% — if the bar is partially empty, widen the box to '
                f'include the empty transparent slot.',
            )
        elif not is_enabled(cal):
            warnings.append(f'{label}: using default colors — save again after capture refreshes.')
    return warnings


def _center_to_area(cx, cy, width, height):
    w, h = int(width), int(height)
    return {
        'x': int(cx) - w // 2,
        'y': int(cy) - h // 2,
        'width': w,
        'height': h,
    }


def relocate_enemy_strip_from_mp(bgr, areas):
    """Re-find enemy name/HP from the calibrated player MP bar position."""
    import hp_number_reader as hr

    mp = areas.get('mp_bar_area')
    if not mp or int(mp.get('width', 0)) <= 0:
        return
    found = hr.locate_enemy_target_strip(
        bgr,
        int(mp['x']),
        int(mp['y']),
        int(mp.get('height') or 0) or None,
        int(mp.get('width') or 0) or None,
    )
    if not found:
        return
    ncx, ncy, nw, nh = found['name_area']
    areas['target_name_area'] = _center_to_area(ncx, ncy, nw, nh)
    hp_area = found.get('hp_area')
    if hp_area:
        hcx, hcy, hw, hh = hp_area
        areas['target_hp_bar_area'] = _center_to_area(hcx, hcy, hw, hh)


def sync_enemy_name_above_hp(areas):
    """Keep name row directly above the enemy HP bar strip."""
    import hp_number_reader as hr

    hp = areas.get('target_hp_bar_area')
    if not hp or int(hp.get('width', 0)) <= 0:
        return
    nh = hr.NAME_AREA_HEIGHT
    areas['target_name_area'] = {
        'x': int(hp['x']),
        'y': max(0, int(hp['y']) - nh),
        'width': int(hp['width']),
        'height': nh,
    }


def refine_detected_bar_areas(bgr, areas):
    """
    Tighten auto-detected HP/MP/enemy boxes and re-anchor enemy UI to player MP.

    Call after color-based region detection on a capture.
    """
    if not areas or bgr is None or bgr.size == 0:
        return areas
    out = {key: dict(val) for key, val in areas.items()}
    for kind in (KIND_HP, KIND_MP):
        key = REGION_KEYS[kind]
        if key not in out:
            continue
        snapped = snap_area_to_bar(bgr, out[key], kind)
        if snapped:
            out[key] = snapped
    relocate_enemy_strip_from_mp(bgr, out)
    enemy_key = REGION_KEYS[KIND_ENEMY_HP]
    if enemy_key in out:
        snapped = snap_area_to_bar(bgr, out[enemy_key], KIND_ENEMY_HP)
        if snapped:
            out[enemy_key] = snapped
        sync_enemy_name_above_hp(out)
    return out


def migrate_saved_calibrations(hwnd):
    """
    One-shot: auto-calibrate bar colors from a live capture when regions exist
  but profiles still have enabled=False (pre-migration saves).
    """
    import config
    import window_utils

    if not hwnd:
        return []

    bgr, _method = window_utils.capture_window_bgr(hwnd)
    if bgr is None or bgr.size == 0:
        return []

    migrated = []
    for kind, area_key in REGION_KEYS.items():
        area = getattr(config, area_key)
        cal = getattr(config, CONFIG_KEYS[kind])
        if not config.bar_area_configured(area):
            continue
        if is_enabled(cal):
            continue
        x, y, w, h = int(area['x']), int(area['y']), int(area['width']), int(area['height'])
        crop = bgr[y:y + h, x:x + w]
        if crop.size == 0:
            continue
        new_cal = auto_calibrate_from_region(crop, kind)
        if is_enabled(new_cal):
            cal.clear()
            cal.update(new_cal)
            migrated.append(kind)
    return migrated


def bars_status_text(hp_pct=None, mp_pct=None):
    """One-line HP/MP calibration status for the main window."""
    import config

    parts = []
    if config.bar_area_configured(config.hp_bar_area):
        tag = 'cal' if is_enabled(config.hp_bar_color_cal) else 'default'
        txt = f'HP {hp_pct:.0f}%' if hp_pct is not None else 'HP'
        parts.append(f'{txt} ({tag})')
    if config.bar_area_configured(config.mp_bar_area):
        tag = 'cal' if is_enabled(config.mp_bar_color_cal) else 'default'
        txt = f'MP {mp_pct:.0f}%' if mp_pct is not None else 'MP'
        parts.append(f'{txt} ({tag})')
    if config.bar_area_configured(config.target_hp_bar_area):
        tag = 'cal' if is_enabled(config.target_hp_bar_color_cal) else 'default'
        parts.append(f'Enemy ({tag})')
    return ' · '.join(parts) if parts else ''
