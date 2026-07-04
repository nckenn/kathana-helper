"""Read HP/MP bar fill percentage from user-defined screen regions."""
import cv2
import numpy as np
import bar_color_calibration
import config
import ui_bar_detection
import window_utils


# Strict red thresholds for player HP over transparent stone floors.
_HP_STRICT_SAT = 85
_HP_STRICT_VAL = 65
_HP_STRICT_HUE = 14


def bar_fill_percent_from_mask(mask_u8, min_row_fraction=0.35, merge_rows=True):
    """
    Fill % from a bar mask across the full bar crop width.

    Row-merge bridges white number overlays. Leading chrome columns (no bar
    pixels) are trimmed; empty bar interior still counts toward the denominator.
    """
    if mask_u8 is None or mask_u8.size == 0:
        return 0.0
    work = mask_u8
    if merge_rows:
        work = ui_bar_detection._row_merged_mask(mask_u8)
    h, w = work.shape[:2]
    if w <= 0 or h <= 0:
        return 0.0
    min_pixels = max(1, int(h * min_row_fraction))
    col_counts = (work > 0).sum(axis=0)
    filled = np.where(col_counts >= min_pixels)[0]
    if filled.size == 0:
        return 0.0
    fill_end = int(filled[-1]) + 1
    x0 = 0
    while x0 < w and col_counts[x0] == 0:
        x0 += 1
    track_w = w - x0
    if track_w <= 0:
        return 0.0
    if fill_end <= x0:
        return 0.0
    if fill_end >= w - 1:
        return 100.0
    return round((fill_end - x0) / track_w * 100, 1)


def _hp_percent_from_mask(region, red_mask, min_row_fraction=0.35):
    """Shared column-scan fill percentage from a boolean/uint8 red mask."""
    if region is None or region.size == 0:
        return 0.0
    return bar_fill_percent_from_mask(red_mask, min_row_fraction=min_row_fraction)


def _strict_hp_mask(bgr, sat_min=None, val_min=None, hue_max=None):
    if sat_min is None:
        sat_min = _HP_STRICT_SAT
    if val_min is None:
        val_min = _HP_STRICT_VAL
    if hue_max is None:
        hue_max = _HP_STRICT_HUE
    return ui_bar_detection.build_enemy_red_mask(
        bgr, sat_min=sat_min, val_min=val_min, hue_max=hue_max,
    )


def _isolate_hp_bar_band(region, sat_min=None, val_min=None, hue_max=None):
    """Crop to the widest saturated-red HP bar row in a capture."""
    if region is None or region.size == 0:
        return region
    strict = _strict_hp_mask(region, sat_min, val_min, hue_max)
    bands, _ = ui_bar_detection.find_bar_bands(strict)
    if bands:
        _bx, by, bw, bh = max(bands, key=lambda item: item[2])
        if bw >= 10 and bh >= 4:
            return region[by:by + bh, :]
    import hp_number_reader
    return hp_number_reader._focus_red_bar(region)


def _blend_hp_with_text(region, red_mask, pixel_pct, weight=None):
    import hp_number_reader

    text_pct = hp_number_reader.hp_percent_from_text_anchor(region, fill_mask=red_mask)
    if text_pct is None:
        return pixel_pct
    if weight is None:
        weight = float(getattr(config, 'hp_text_blend_weight', 0.3))
    blended = (1.0 - weight) * float(pixel_pct) + weight * float(text_pct)
    return round(blended, 1)


def hp_percent_from_bgr(region):
    """Red HP bar: strict saturated fill over transparent backgrounds."""
    if region is None or region.size == 0:
        return 0.0
    cal = getattr(config, 'hp_bar_color_cal', None)
    if bar_color_calibration.is_enabled(cal):
        custom = bar_color_calibration.percent_from_region(
            region, cal, bar_color_calibration.KIND_HP,
        )
        if custom is not None:
            return custom
    bar = _isolate_hp_bar_band(region)
    if bar is None or bar.size == 0:
        return 0.0
    red_mask = _strict_hp_mask(bar)
    pixel_pct = _hp_percent_from_mask(bar, red_mask, min_row_fraction=0.45)
    return _blend_hp_with_text(region, red_mask, pixel_pct)


def enemy_hp_percent_from_bgr(region):
    """
    Enemy/target HP fill — stricter than player bars.

    Transparent empty bar slots show the game floor, which can look reddish under the
    loose player mask. Uses saturated-bar detection and isolates the HP row first.
    User calibration (Region Editor) overrides defaults when enabled.
    """
    if region is None or region.size == 0:
        return 0.0
    cal = getattr(config, 'target_hp_bar_color_cal', None)
    if bar_color_calibration.is_enabled(cal):
        custom = bar_color_calibration.percent_from_region(
            region, cal, bar_color_calibration.KIND_ENEMY_HP,
        )
        if custom is not None:
            return _blend_enemy_hp_with_text(region, None, None, custom)
    sat_min = int(getattr(config, 'enemy_hp_red_sat_min', 90))
    val_min = int(getattr(config, 'enemy_hp_red_val_min', 80))
    hue_max = int(getattr(config, 'enemy_hp_red_hue_max', 12))
    bar = _isolate_enemy_hp_bar(region, sat_min, val_min, hue_max)
    if bar is None or bar.size == 0:
        return 0.0
    red_mask = ui_bar_detection.build_enemy_red_mask(
        bar, sat_min=sat_min, val_min=val_min, hue_max=hue_max,
    )
    pixel_pct = bar_fill_percent_from_mask(red_mask, min_row_fraction=0.5)
    return _blend_enemy_hp_with_text(region, bar, red_mask, pixel_pct)


def _blend_enemy_hp_with_text(region, bar, red_mask, pixel_pct):
    """Blend pixel fill % with on-bar number overlay anchor when visible."""
    import hp_number_reader

    text_pct = hp_number_reader.hp_percent_from_text_anchor(region, fill_mask=red_mask)
    if text_pct is None:
        return pixel_pct
    weight = float(getattr(config, 'enemy_hp_text_blend_weight', 0.3))
    blended = (1.0 - weight) * float(pixel_pct) + weight * float(text_pct)
    return round(blended, 1)


def _isolate_enemy_hp_bar(region, sat_min, val_min, hue_max):
    """Crop to the widest saturated-red HP bar band in a capture."""
    strict = ui_bar_detection.build_enemy_red_mask(
        region, sat_min=sat_min, val_min=val_min, hue_max=hue_max,
    )
    bands, _ = ui_bar_detection.find_bar_bands(strict)
    if bands:
        _bx, by, bw, bh = max(bands, key=lambda item: item[2])
        if bw >= 10 and bh >= 4:
            # Keep full bar width — empty transparent slots are part of the denominator.
            return region[by:by + bh, :]
    import hp_number_reader
    return hp_number_reader._focus_red_bar(region)


def mp_percent_from_bgr(region):
    """Blue MP bar: percentage = filled width / total width."""
    if region is None or region.size == 0:
        return 0.0
    h, w = region.shape[:2]
    if w <= 0 or h <= 0:
        return 0.0
    cal = getattr(config, 'mp_bar_color_cal', None)
    if bar_color_calibration.is_enabled(cal):
        custom = bar_color_calibration.percent_from_region(
            region, cal, bar_color_calibration.KIND_MP,
        )
        if custom is not None:
            return custom
    blue_mask = ui_bar_detection.build_blue_mask(region)
    blue_pixels = np.sum(blue_mask > 0, axis=0)
    min_pixels = max(1, h * 0.35)
    cols_above = blue_pixels >= min_pixels
    if not np.any(cols_above):
        return 0.0
    last_col = int(np.max(np.where(cols_above)[0])) + 1
    if last_col >= w - 2:
        return 100.0
    return round(last_col / w * 100, 1)


def _crop_bar_from_frame(frame, area, origin):
    if frame is None or not config.bar_area_configured(area):
        return None
    import frame_cache
    x = area['x']
    y = area['y']
    w = area['width']
    h = area['height']
    return frame_cache.crop_rect(frame, x, y, x + w, y + h, origin)


def _get_cached_frame(hwnd):
    import frame_cache
    frame = frame_cache.get_frame(hwnd, config.calibrator)
    return frame, frame_cache.get_origin()


def read_hp_mp_from_frame(frame, origin):
    """Return (hp, mp) from a cached window frame; each may be None."""
    hp = None
    mp = None
    if config.bar_area_configured(config.hp_bar_area):
        region = _crop_bar_from_frame(frame, config.hp_bar_area, origin)
        if region is not None and region.size > 0:
            hp = hp_percent_from_bgr(region)
    if config.bar_area_configured(config.mp_bar_area):
        region = _crop_bar_from_frame(frame, config.mp_bar_area, origin)
        if region is not None and region.size > 0:
            mp = mp_percent_from_bgr(region)
    return hp, mp


def _capture_bar(hwnd, area):
    return window_utils.capture_window_region_bgr(
        hwnd, area['x'], area['y'], area['width'], area['height'],
    )


def _smooth_reading(readings, value, window=None):
    if value is None:
        return None
    if window is None:
        window = config.HP_MP_SMOOTHING_WINDOW
    readings.append(value)
    if len(readings) > window:
        readings.pop(0)
    if not readings:
        return value
    return round(float(np.median(readings)), 1)


def read_hp_percent(hwnd):
    if not config.bar_area_configured(config.hp_bar_area):
        return None
    frame, origin = _get_cached_frame(hwnd)
    if frame is not None:
        region = _crop_bar_from_frame(frame, config.hp_bar_area, origin)
        if region is not None and region.size > 0:
            raw = hp_percent_from_bgr(region)
            return _smooth_reading(config.hp_readings, raw)
    region = _capture_bar(hwnd, config.hp_bar_area)
    if region is None:
        return None
    raw = hp_percent_from_bgr(region)
    return _smooth_reading(config.hp_readings, raw)


def read_mp_percent(hwnd):
    if not config.bar_area_configured(config.mp_bar_area):
        return None
    frame, origin = _get_cached_frame(hwnd)
    if frame is not None:
        region = _crop_bar_from_frame(frame, config.mp_bar_area, origin)
        if region is not None and region.size > 0:
            raw = mp_percent_from_bgr(region)
            return _smooth_reading(config.mp_readings, raw)
    region = _capture_bar(hwnd, config.mp_bar_area)
    if region is None:
        return None
    raw = mp_percent_from_bgr(region)
    return _smooth_reading(config.mp_readings, raw)


def read_hp_mp(hwnd):
    """Return (hp, mp); each may be None if region not configured."""
    frame, origin = _get_cached_frame(hwnd)
    if frame is not None:
        return read_hp_mp_from_frame(frame, origin)
    hp = read_hp_percent(hwnd) if config.bar_area_configured(config.hp_bar_area) else None
    mp = read_mp_percent(hwnd) if config.bar_area_configured(config.mp_bar_area) else None
    return hp, mp
