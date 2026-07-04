"""Tests for mob-filter self-target and safe buff/pot gating."""
import time

import config
import mob_filter


def _enable_mob_filter(monkeypatch):
    monkeypatch.setattr(config, 'mob_detection_enabled', True)
    monkeypatch.setattr(config, 'mob_templates', [{'id': 'a', 'file': 'mob_a.png'}])
    monkeypatch.setattr(config, 'mob_scan_area', {'x': 1, 'y': 2, 'width': 10, 'height': 8})
    monkeypatch.setattr(config, 'target_name_area', {'x': 1, 'y': 2, 'width': 10, 'height': 8})


def test_should_allow_buffs_when_idle(monkeypatch):
    _enable_mob_filter(monkeypatch)
    config.enemy_target_time = 0
    config.enemy_hp_readings = []
    config.current_enemy_hp_percentage = 0
    config.is_looting = False
    assert mob_filter.should_allow_buffs() is True


def test_should_block_buffs_during_combat(monkeypatch):
    _enable_mob_filter(monkeypatch)
    config.enemy_target_time = time.time()
    config.enemy_hp_readings = [50.0]
    config.current_enemy_hp_percentage = 40
    config.is_looting = False
    assert mob_filter.should_allow_buffs() is False


def test_focus_self_before_retarget_sends_key(monkeypatch):
    _enable_mob_filter(monkeypatch)
    config.mob_detection_enabled = True
    config.self_target_key = '`'
    sent = []
    monkeypatch.setattr('input_handler.send_input', lambda k: sent.append(k))
    monkeypatch.setattr(config, 'SELF_TARGET_DELAY', 0)
    assert mob_filter.focus_self_before_retarget() is True
    assert sent == ['`']
    assert config.current_mob_match is None
