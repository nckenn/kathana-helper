"""Tests for HP/MP bar fill percentage reading."""
import numpy as np

import bar_reader


def _red_bar_image(width=100, fill_cols=80, height=12):
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:, :fill_cols] = (0, 0, 200)
    return img


def test_hp_percent_near_full_bar():
    region = _red_bar_image(width=100, fill_cols=99)
    assert bar_reader.hp_percent_from_bgr(region) == 100.0


def test_hp_percent_partial_fill():
    region = _red_bar_image(width=100, fill_cols=50)
    pct = bar_reader.hp_percent_from_bgr(region)
    assert 45 <= pct <= 55


def test_hp_percent_empty_region():
    assert bar_reader.hp_percent_from_bgr(None) == 0.0
    assert bar_reader.hp_percent_from_bgr(np.zeros((0, 0, 3), dtype=np.uint8)) == 0.0
