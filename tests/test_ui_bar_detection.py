"""Tests for HP/MP bar detection on the new glossy UI."""
import os
import cv2
import numpy as np
from calibration import Calibrator
import ui_bar_detection


FIXTURE = os.path.join('tests', 'fixtures', 'new_ui_panels.png')
PLAYER_BARS_FIXTURE = os.path.join('tests', 'fixtures', 'player_hp_mp_bars.png')
FULL_GAME_CAPTURE = os.path.join('debug', 'calibrate_original.png')


def test_find_player_bars_on_new_ui_fixture():
    img = cv2.imread(FIXTURE)
    assert img is not None
    hp, mp, _, _, red_bands, blue_bands = ui_bar_detection.find_player_hp_mp(img)
    assert hp is not None and mp is not None
    assert len(red_bands) >= 2
    assert len(blue_bands) >= 1
    assert mp[1] > hp[1]


def test_calibration_find_bars_on_new_ui_fixture():
    img = cv2.imread(FIXTURE)
    cal = Calibrator()
    assert cal.find_bars(img) is True
    assert cal.hp_position is not None
    assert cal.mp_position is not None


def test_find_bars_on_desaturated_red():
    """Glossy bars with lowered saturation should still calibrate via R-dominance."""
    img = cv2.imread(FIXTURE)
    assert img is not None
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 1] *= 0.45
    muted = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    cal = Calibrator()
    assert cal.find_bars(muted) is True


def test_find_player_bars_on_reference_hp_mp_colors():
    """Detect bars using HSV ranges sampled from actual in-game HP/MP colors."""
    img = cv2.imread(PLAYER_BARS_FIXTURE)
    assert img is not None
    hp, mp, _, _, red_bands, blue_bands = ui_bar_detection.find_player_hp_mp(img)
    assert hp is not None and mp is not None
    assert len(red_bands) >= 1 and len(blue_bands) >= 1
    assert mp[1] > hp[1]
    assert hp[2] >= 180
    assert mp[2] >= 180


def test_find_player_bars_on_full_window_capture():
    """Regression: full game window has narrow HP/MP rows, not 42% row fill."""
    if not os.path.exists(FULL_GAME_CAPTURE):
        return
    img = cv2.imread(FULL_GAME_CAPTURE)
    assert img is not None
    hp, mp, _, _, _, _ = ui_bar_detection.find_player_hp_mp(img)
    assert hp is not None and mp is not None
    assert mp[1] > hp[1]
    assert hp[2] >= 200
    assert mp[2] >= 150


def test_find_player_bars_any_screen_position():
    """HP/MP detection is color/geometry based — UI block can sit anywhere on screen."""
    img = cv2.imread(FIXTURE)
    assert img is not None
    canvas = np.zeros((400, 600, 3), dtype=np.uint8)
    canvas[:, :] = (40, 40, 40)
    y_off, x_off = 40, 320
    fh, fw = img.shape[:2]
    canvas[y_off : y_off + fh, x_off : x_off + fw] = img
    hp, mp, _, _, _, _ = ui_bar_detection.find_player_hp_mp(canvas)
    assert hp is not None and mp is not None
    assert hp[0] >= x_off and mp[0] >= x_off
    assert mp[1] > hp[1]
