"""Tests for automatic bar fill color calibration."""
import os

import cv2
import numpy as np

import bar_color_calibration as bcc


def _filled_red_bar(width=100, fill_cols=70, height=12):
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:, :fill_cols] = (0, 0, 200)
    return img


def test_auto_calibrate_from_synthetic_hp_bar():
    bar = _filled_red_bar(fill_cols=60)
    cal = bcc.auto_calibrate_from_region(bar, bcc.KIND_HP)
    assert bcc.is_enabled(cal)
    assert cal.get('auto') is True
    pct = bcc.percent_from_region(bar, cal, bcc.KIND_HP)
    assert 50 <= pct <= 70


def test_auto_calibrate_ignores_desaturated_floor_on_enemy_bar():
    path = os.path.join('tests', 'fixtures', 'enemy_hp_transparent_90.png')
    img = cv2.imread(path)
    assert img is not None
    bar = img[27:42]
    cal = bcc.auto_calibrate_from_region(bar, bcc.KIND_ENEMY_HP)
    assert bcc.is_enabled(cal)
    pct = bcc.percent_from_region(bar, cal, bcc.KIND_ENEMY_HP)
    assert pct is not None
    assert 80 <= pct <= 95


def test_auto_calibrate_mp_on_synthetic_bar():
    bar = np.zeros((12, 100, 3), dtype=np.uint8)
    bar[:, :80] = (200, 100, 0)
    cal = bcc.auto_calibrate_from_region(bar, bcc.KIND_MP)
    pct = bcc.percent_from_region(bar, cal, bcc.KIND_MP)
    assert 70 <= pct <= 90


def test_snap_area_to_bar():
    bar = _filled_red_bar(width=120, fill_cols=80, height=14)
    canvas = np.zeros((80, 200, 3), dtype=np.uint8)
    canvas[30:44, 40:160] = bar
    area = {'x': 35, 'y': 25, 'width': 130, 'height': 30}
    snapped = bcc.snap_area_to_bar(canvas, area, bcc.KIND_HP)
    assert snapped is not None
    assert 10 <= snapped['width'] <= 130
    assert 4 <= snapped['height'] <= 20


def test_snap_hp_aligns_with_mp_in_stacked_target_ui():
    """HP snap should match MP horizontal inset in name+HP+MP target panels."""
    for name in ('stacked_target_hp_mp.png', 'enemy_hp_transparent_90.png'):
        path = os.path.join('tests', 'fixtures', name)
        if not os.path.exists(path):
            continue
        img = cv2.imread(path)
        assert img is not None
        h, w = img.shape[:2]
        panel_h = h // 2 if name == 'stacked_target_hp_mp.png' else max(40, h // 2)
        area = {'x': 0, 'y': 0, 'width': w, 'height': panel_h}
        hp = bcc.snap_area_to_bar(img, area, bcc.KIND_HP)
        mp = bcc.snap_area_to_bar(img, area, bcc.KIND_MP)
        assert hp is not None and mp is not None
        assert hp['x'] == mp['x']
        assert abs(hp['width'] - mp['width']) <= 4
        assert hp['y'] + hp['height'] <= mp['y'] + 2


def test_migrate_enables_calibration(monkeypatch):
    import config as cfg

    bar = _filled_red_bar(fill_cols=60)
    cfg.hp_bar_area.update({'x': 0, 'y': 0, 'width': bar.shape[1], 'height': bar.shape[0]})
    cfg.hp_bar_color_cal.clear()
    cfg.hp_bar_color_cal.update({'enabled': False})

    monkeypatch.setattr('window_utils.capture_window_bgr', lambda hwnd: (bar, 'test'))
    migrated = bcc.migrate_saved_calibrations(1)
    assert bcc.KIND_HP in migrated
    assert bcc.is_enabled(cfg.hp_bar_color_cal)
