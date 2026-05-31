"""Tests for CV-based auto repair break warning detection."""
import os

import cv2
import numpy as np
import auto_repair


FIXTURE = os.path.join(
    os.path.dirname(__file__), 'fixtures', 'break_warning_sample.png',
)


def _load_fixture():
    img = cv2.imread(FIXTURE)
    assert img is not None, f'Missing fixture: {FIXTURE}'
    return img


def test_detects_green_break_warning_line():
    detected, info = auto_repair.analyze_break_warning(_load_fixture())
    assert detected is True
    assert info['best_line_width'] >= auto_repair.MIN_WARNING_LINE_WIDTH
    assert info['qualifying_rows'] >= 1


def test_ignores_magenta_only_region():
    img = _load_fixture()
    # Damage-only lines at the top (no green warning row)
    top = img[:18]
    detected, _ = auto_repair.analyze_break_warning(top)
    assert detected is False


def test_black_image_no_detection():
    img = np.zeros((40, 200, 3), dtype=np.uint8)
    detected, _ = auto_repair.analyze_break_warning(img)
    assert detected is False
