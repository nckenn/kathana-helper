"""Tests for CV mob template matching."""
import numpy as np
import cv2
import config
import mob_filter


def test_match_in_image_finds_embedded_template():
    template = np.zeros((20, 80, 3), dtype=np.uint8)
    template[:, :, 2] = 200
    scan = np.zeros((20, 80, 3), dtype=np.uint8)
    scan[:, :, 2] = 200
    entry = {'id': 't1', 'name': 'Monster 1', 'file': 'unused.png'}
    config.mob_match_threshold = 0.9
    mob_filter._template_cache['t1'] = template
    match = mob_filter.match_in_image(scan, templates=[entry])
    assert match is not None
    assert match['confidence'] >= 0.9
    mob_filter.invalidate_cache()


def test_match_rejects_different_image():
    rng = np.random.default_rng(0)
    template = rng.integers(0, 255, (20, 80, 3), dtype=np.uint8)
    scan = template.copy()
    scan[5:15, 20:60] = rng.integers(0, 255, (10, 40, 3), dtype=np.uint8)
    entry = {'id': 't1', 'name': 'Monster 1', 'file': 'unused.png'}
    config.mob_match_threshold = 0.88
    mob_filter._template_cache['t1'] = template
    match = mob_filter.match_in_image(scan, templates=[entry])
    assert match is None
    mob_filter.invalidate_cache()


def test_should_allow_attack_only_when_matched():
    config.mob_filter_enabled = True
    config.mob_scan_area = {'x': 0, 'y': 0, 'width': 10, 'height': 10}
    config.mob_templates = [{'id': 'a', 'name': 'M1', 'file': 'a.png'}]

    config.current_mob_match = {'id': 'a', 'name': 'M1', 'confidence': 0.95}
    assert mob_filter.should_allow_action('attack', 123) is True
    assert mob_filter.should_allow_action('target', 123) is False
    assert mob_filter.should_allow_combat(123) is True

    config.current_mob_match = None
    assert mob_filter.should_allow_action('attack', 123) is False
    assert mob_filter.should_allow_action('target', 123) is True
    assert mob_filter.should_allow_combat(123) is False
    assert mob_filter.should_allow_action('pick', 123) is True

    config.mob_filter_enabled = False
    config.current_mob_match = None


def test_probe_aligns_mismatched_template_size():
    template = np.zeros((19, 94, 3), dtype=np.uint8)
    template[:, 20:60, 2] = 200
    scan = cv2.resize(template, (76, 21))
    entry = {'id': 't1', 'name': 'Monster 1', 'file': 'unused.png'}
    config.mob_match_threshold = 0.5
    mob_filter._template_cache['t1'] = template
    scores = mob_filter._collect_scores(scan, [entry])
    assert scores[0][0] > 0.5
    mob_filter.invalidate_cache()


def test_skill_timer_blocked_without_mob_match(monkeypatch):
    import skill_timer
    sent = []
    config.mob_filter_enabled = True
    config.mob_scan_area = {'x': 0, 'y': 0, 'width': 10, 'height': 10}
    config.mob_templates = [{'id': 'a', 'name': 'M1', 'file': 'a.png'}]
    config.current_mob_match = None
    config.skill_slots[1]['enabled'] = True
    config.skill_slots[1]['interval'] = 0.1
    config.skill_slots[1]['last_used'] = 0.0

    monkeypatch.setattr('skill_timer.window_utils.resolve_hwnd', lambda: 123)
    monkeypatch.setattr('skill_timer.input_handler.send_input', lambda k: sent.append(k))

    skill_timer.check_skill_slots()
    assert sent == []

    config.current_mob_match = {'id': 'a', 'name': 'M1', 'confidence': 0.9}
    skill_timer.check_skill_slots()
    assert sent == ['1']

    config.mob_filter_enabled = False
    config.current_mob_match = None
    config.skill_slots[1]['enabled'] = False


def test_action_timer_blocks_attack_without_match(monkeypatch):
    import action_timer
    sent = []
    config.mob_filter_enabled = True
    config.mob_scan_area = {'x': 0, 'y': 0, 'width': 10, 'height': 10}
    config.mob_templates = [{'id': 'a', 'name': 'M1', 'file': 'a.png'}]
    for name in config.action_slots:
        config.action_slots[name]['enabled'] = False
    config.action_slots['attack']['enabled'] = True
    config.action_slots['attack']['interval'] = 0.1
    config.action_slots['attack']['last_used'] = 0.0

    monkeypatch.setattr('action_timer.window_utils.resolve_hwnd', lambda: 123)
    monkeypatch.setattr('action_timer.input_handler.send_input', lambda k: sent.append(k))
    config.current_mob_match = None
    monkeypatch.setattr('action_timer.mob_filter.is_active', lambda: True)
    monkeypatch.setattr('action_timer.mob_filter.should_allow_action', lambda n, _h: n != 'attack')

    action_timer.check_action_slots()
    assert sent == []

    config.mob_filter_enabled = False
