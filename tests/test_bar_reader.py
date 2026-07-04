"""Tests for HP/MP bar fill percentage reading."""
import os

import cv2
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


def test_enemy_hp_on_transparent_bar_fixture():
    """Enemy reader should track ~90% on transparent-bar fixture."""
    path = os.path.join('tests', 'fixtures', 'enemy_hp_transparent_90.png')
    img = cv2.imread(path)
    assert img is not None
    bar = img[27:42]
    strict = bar_reader.enemy_hp_percent_from_bgr(bar)
    assert 82 <= strict <= 96


def test_enemy_hp_partial_fill_on_transparent_bar():
    path = os.path.join('tests', 'fixtures', 'enemy_hp_transparent_76.png')
    img = cv2.imread(path)
    assert img is not None
    bar = img[30:46]
    strict = bar_reader.enemy_hp_percent_from_bgr(bar)
    assert 70 <= strict <= 80


def test_player_hp_ignores_floor_bleed_on_transparent_bar():
    """Player HP must not read ~99% when the bar is ~76% over stone floor."""
    path = os.path.join('tests', 'fixtures', 'enemy_hp_transparent_76.png')
    img = cv2.imread(path)
    assert img is not None
    bar = img[30:46]
    pct = bar_reader.hp_percent_from_bgr(bar)
    assert 70 <= pct <= 82


def test_enemy_hp_empty_bar_slot_reads_zero():
    path = os.path.join('tests', 'fixtures', 'enemy_hp_transparent_90.png')
    img = cv2.imread(path)
    bar = img[27:42]
    empty = bar[:, int(bar.shape[1] * 0.88):]
    assert bar_reader.enemy_hp_percent_from_bgr(empty) == 0.0
