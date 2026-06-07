"""Read HP/MP bar fill percentage from user-defined screen regions."""
import cv2
import numpy as np
import config
import ui_bar_detection
import window_utils


def hp_percent_from_bgr(region):
    """Red HP bar: percentage = filled width / total width."""
    if region is None or region.size == 0:
        return 0.0
    h, w = region.shape[:2]
    if w <= 0 or h <= 0:
        return 0.0
    red_mask = ui_bar_detection.build_red_mask(region)
    red_pixels = np.sum(red_mask > 0, axis=0)
    min_pixels = max(1, h * 0.35)
    cols_above = red_pixels >= min_pixels
    if not np.any(cols_above):
        return 0.0
    last_col = int(np.max(np.where(cols_above)[0])) + 1
    if last_col >= w - 2:
        return 100.0
    return round(last_col / w * 100, 1)


def mp_percent_from_bgr(region):
    """Blue MP bar: percentage = filled width / total width."""
    if region is None or region.size == 0:
        return 0.0
    h, w = region.shape[:2]
    if w <= 0 or h <= 0:
        return 0.0
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
