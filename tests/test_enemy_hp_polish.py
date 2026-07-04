"""Tests for enemy HP polish: temporal filter, stale bar kill, text anchor."""
import time

import config
from auto_attack import EnemyHpProcessor


def test_temporal_filter_rejects_spike():
    config.enemy_hp_raw_recent = []
    config.enemy_hp_temporal_tolerance = 2.0
    assert EnemyHpProcessor.temporal_filter_raw(80.0) == 80.0
    assert EnemyHpProcessor.temporal_filter_raw(81.0) == 81.0
    spike = EnemyHpProcessor.temporal_filter_raw(99.0)
    assert spike < 99.0


def test_stale_bar_kill_when_name_missing():
    config.enemy_target_time = time.time() - 2.0
    config.enemy_name_missing_streak = 3
    config.enemy_name_missing_streak_threshold = 3
    config.enemy_name_missing_grace_seconds = 0.6
    config.enemy_stale_bar_hp_max = 40.0
    assert EnemyHpProcessor.should_treat_stale_bar_as_kill(False, 35.0, time.time())
    assert not EnemyHpProcessor.should_treat_stale_bar_as_kill(True, 35.0, time.time())


def test_median_smoothing():
    readings = []
    assert EnemyHpProcessor.update_hp_readings(80.0, readings) == 80.0
    assert EnemyHpProcessor.update_hp_readings(82.0, readings) == 81.0
    assert EnemyHpProcessor.update_hp_readings(100.0, readings) == 82.0
