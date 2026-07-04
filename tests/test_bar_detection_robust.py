"""Robust HP/MP/enemy strip detection over variable floor colors."""
import os

import cv2
import numpy as np

import bar_color_calibration as bcc
import calibration
import ui_bar_detection as ubd

FIXTURE = os.path.join('tests', 'fixtures', 'new_ui_panels.png')


def _paste_on_stone(canvas, patch, x, y):
    ph, pw = patch.shape[:2]
    canvas[y:y + ph, x:x + pw] = patch


def test_player_bars_on_reddish_stone_background():
    """Floor bleed must not beat the real glossy HP/MP stack."""
    img = cv2.imread(FIXTURE)
    assert img is not None
    stone = np.full((320, 520, 3), (48, 72, 118), dtype=np.uint8)
    for i in range(0, 520, 17):
        cv2.line(stone, (i, 0), (i - 40, 320), (38, 58, 95), 1)
    _paste_on_stone(stone, img, 40, 30)
    hp, mp, _, _, _, _ = ubd.find_player_hp_mp(stone)
    assert hp is not None and mp is not None
    assert mp[1] > hp[1]
    assert 40 <= hp[0] <= 120
    assert hp[2] >= 150


def test_detect_regions_refines_enemy_to_mp_anchor():
    img = cv2.imread(FIXTURE)
    assert img is not None
    ok, areas, _cal = calibration.detect_regions_from_bgr(img)
    assert ok
    mp = areas['mp_bar_area']
    enemy_hp = areas['target_hp_bar_area']
    assert enemy_hp['y'] > mp['y'] + mp['height'] - 4
    assert abs(enemy_hp['x'] - mp['x']) <= 8
    assert abs(enemy_hp['width'] - mp['width']) <= 12
    name = areas['target_name_area']
    assert name['y'] + name['height'] <= enemy_hp['y'] + 2


def test_refine_snaps_loose_hp_box():
    img = cv2.imread(FIXTURE)
    assert img is not None
    ok, areas, _ = calibration.detect_regions_from_bgr(img)
    assert ok
    loose = dict(areas['hp_bar_area'])
    loose['width'] += 40
    loose['height'] += 20
    refined = bcc.refine_detected_bar_areas(img, {'hp_bar_area': loose, 'mp_bar_area': areas['mp_bar_area']})
    tight = refined['hp_bar_area']
    assert tight['width'] < loose['width']
    assert abs(tight['width'] - areas['hp_bar_area']['width']) <= 6
