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
    last_col = 0
    for i, count in enumerate(red_pixels):
        if count >= min_pixels:
            last_col = i + 1
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
    last_col = 0
    for i, count in enumerate(blue_pixels):
        if count >= min_pixels:
            last_col = i + 1
    if last_col >= w - 2:
        return 100.0
    return round(last_col / w * 100, 1)


def _capture_bar(hwnd, area):
    return window_utils.capture_window_region_bgr(
        hwnd, area['x'], area['y'], area['width'], area['height'],
    )


def read_hp_percent(hwnd):
    if not config.bar_area_configured(config.hp_bar_area):
        return None
    region = _capture_bar(hwnd, config.hp_bar_area)
    if region is None:
        return None
    return hp_percent_from_bgr(region)


def read_mp_percent(hwnd):
    if not config.bar_area_configured(config.mp_bar_area):
        return None
    region = _capture_bar(hwnd, config.mp_bar_area)
    if region is None:
        return None
    return mp_percent_from_bgr(region)


def read_hp_mp(hwnd):
    """Return (hp, mp); each may be None if region not configured."""
    hp = read_hp_percent(hwnd) if config.bar_area_configured(config.hp_bar_area) else None
    mp = read_mp_percent(hwnd) if config.bar_area_configured(config.mp_bar_area) else None
    return hp, mp
