"""Tests for shared template match margin helper."""
import cv2
import numpy as np

import match_utils


def test_template_match_with_margin_accepts_clear_peak():
    template = np.zeros((6, 6, 3), dtype=np.uint8)
    template[1:5, 1:5] = (40, 200, 40)
    area = np.zeros((24, 24, 3), dtype=np.uint8)
    area[8:14, 8:14] = template
    matched, conf, loc = match_utils.template_match_with_margin(area, template, 0.85, 0.05)
    assert matched is True
    assert conf >= 0.85
    assert loc is not None


def test_template_match_with_margin_rejects_ambiguous_peaks():
    template = np.zeros((8, 8, 3), dtype=np.uint8)
    template[:, :] = (0, 200, 0)
    area = np.zeros((40, 40, 3), dtype=np.uint8)
    area[4:12, 4:12] = template
    area[4:12, 20:28] = template
    matched, conf, _ = match_utils.template_match_with_margin(area, template, 0.5, 0.05)
    assert matched is False
    assert conf >= 0.5
