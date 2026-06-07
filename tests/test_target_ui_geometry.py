"""Tests for enemy target strip detection (new stacked HP/MP UI)."""
import os
import cv2
from calibration import Calibrator
import hp_number_reader as hr


FIXTURE = os.path.join('tests', 'fixtures', 'new_ui_panels.png')


def test_locate_enemy_strip_below_player_mp():
    img = cv2.imread(FIXTURE)
    assert img is not None
    cal = Calibrator()
    assert cal.find_bars(img) is True
    mp_x, mp_y = cal.mp_position
    found = hr.locate_enemy_target_strip(img, mp_x, mp_y, mp_bar_h=15)
    assert found is not None
    search_x, search_y = found['search_origin']
    # Enemy name row sits just above the lower red HP bar (~row 60 in fixture).
    assert 58 <= search_y <= 64
    assert search_x == max(0, mp_x + hr.SEARCH_AREA_OFFSET_X)


def test_calibration_sets_enemy_name_on_new_ui():
    img = cv2.imread(FIXTURE)
    assert img is not None
    cal = Calibrator()
    assert cal.find_bars(img) is True
    enemy_hp, enemy_name = cal.find_enemy_hp_and_name_area(img)
    assert enemy_name is not None
    ncx, ncy, nw, nh = enemy_name
    assert nh == hr.NAME_AREA_HEIGHT
    assert nw >= 200
    rect = hr.get_enemy_name_bar_rect(cal)
    assert rect is not None
    x, y, w, h = rect
    assert h == hr.NAME_AREA_HEIGHT
    assert y == ncy - nh // 2
