import numpy as np
import cv2
from bar_reader import hp_percent_from_bgr, mp_percent_from_bgr


def _solid_hsv_bar(hue, fill_ratio, width=100, height=10):
    """Build a BGR image with a solid HSV bar on the left portion."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    fill_w = int(width * fill_ratio)
    patch = np.full((height, fill_w, 3), [hue, 255, 255], dtype=np.uint8)
    img[:, :fill_w] = cv2.cvtColor(patch, cv2.COLOR_HSV2BGR)
    return img


def test_hp_partial_red_bar():
    img = _solid_hsv_bar(0, 0.6)
    pct = hp_percent_from_bgr(img)
    assert 55 <= pct <= 65


def test_mp_partial_blue_bar():
    img = _solid_hsv_bar(120, 0.5)
    pct = mp_percent_from_bgr(img)
    assert 45 <= pct <= 55
