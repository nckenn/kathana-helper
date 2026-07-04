"""System message + buff strip region derivation."""
import os

import cv2
import calibration
import region_helpers

CHAT_FIXTURE = os.path.join('tests', 'fixtures', 'chat_panel_ui.png')


def test_derive_buff_area_above_system_message():
    sys_area = {'x': 100, 'y': 500, 'width': 200, 'height': 80}
    buff = region_helpers.derive_buff_area_from_system_message(sys_area)
    assert buff is not None
    assert buff['y'] == 456
    assert buff['height'] == 40
    assert buff['x'] == 100
    assert buff['width'] == 200


def test_export_includes_buff_when_system_message_found():
    cal = calibration.Calibrator()
    cal.system_message_area = (120, 400, 180, 60)
    areas = cal.export_region_areas()
    assert 'system_message_area' in areas
    assert areas['system_message_area']['y'] == 400
    assert 'buff_area' in areas
    assert areas['buff_area']['y'] == 356
    assert areas['buff_area']['x'] == 120
    assert areas['buff_area']['width'] == 180
    assert areas['buff_area']['y'] + areas['buff_area']['height'] == 396


def test_find_system_message_on_chat_panel_fixture():
    if not os.path.exists(CHAT_FIXTURE):
        return
    img = cv2.imread(CHAT_FIXTURE)
    assert img is not None
    cal = calibration.Calibrator()
    assert cal.find_system_message_area(img) is not None
    areas = cal.export_region_areas()
    sys_area = areas['system_message_area']
    assert 360 <= sys_area['width'] <= 410
    assert 70 <= sys_area['height'] <= 120
    assert 110 <= sys_area['x'] <= 150
    assert 40 <= sys_area['y'] <= 80
    assert sys_area['y'] + sys_area['height'] <= 150
    assert 'buff_area' in areas
    assert areas['buff_area']['y'] + areas['buff_area']['height'] <= sys_area['y']


def test_best_template_match_skips_when_patch_too_small():
    import numpy as np

    screen = np.zeros((40, 40), dtype=np.uint8)
    templ = np.zeros((80, 20), dtype=np.uint8)
    score, loc, tw, th = calibration._best_template_match(screen, templ)
    assert score < 0
