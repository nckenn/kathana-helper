"""Tests for buff activation debouncing."""
import time

import numpy as np

import config
from buffs_manager import BuffsManager


class _FakeTemplate:
    shape = (8, 8, 3)


def test_buff_requires_consecutive_misses_before_press(monkeypatch):
    sent = []

    monkeypatch.setattr('buffs_manager.input_handler.send_input', lambda key: sent.append(key))
    monkeypatch.setattr(config, 'buff_inactive_miss_required', 2)
    monkeypatch.setattr(config, 'buff_press_cooldown', 0.0)
    monkeypatch.setattr(config, 'buff_activation_grace_seconds', 10.0)
    monkeypatch.setattr(config, 'buffs_config', {
        0: {'enabled': True, 'image_path': 'jobs/test.png', 'key': 'f1'},
    })
    monkeypatch.setattr(
        'buffs_manager.template_cache.get_template',
        lambda path, _mode: _FakeTemplate(),
    )
    monkeypatch.setattr(
        BuffsManager,
        '_buff_active_in_area',
        lambda self, template, area: False,
    )
    monkeypatch.setattr(config, 'resolve_resource_path', lambda path: path)
    monkeypatch.setattr('buffs_manager.CV2_AVAILABLE', True)

    mgr = BuffsManager(num_buffs=1)
    mgr.buffs[0] = 'jobs/test.png'
    area = np.zeros((20, 80, 3), dtype=np.uint8)

    mgr.update_and_activate_buffs(1, None, None, area, 0, 0)
    assert sent == []

    mgr.update_and_activate_buffs(1, None, None, area, 0, 0)
    assert sent == ['f1']


def test_buff_activation_grace_blocks_repeat_press(monkeypatch):
    sent = []
    clock = {'t': 100.0}

    monkeypatch.setattr(time, 'time', lambda: clock['t'])
    monkeypatch.setattr('buffs_manager.input_handler.send_input', lambda key: sent.append(key))
    monkeypatch.setattr(config, 'buff_inactive_miss_required', 1)
    monkeypatch.setattr(config, 'buff_press_cooldown', 0.0)
    monkeypatch.setattr(config, 'buff_activation_grace_seconds', 5.0)
    monkeypatch.setattr(config, 'buffs_config', {
        0: {'enabled': True, 'image_path': 'jobs/test.png', 'key': 'f1'},
    })
    monkeypatch.setattr(
        'buffs_manager.template_cache.get_template',
        lambda path, _mode: _FakeTemplate(),
    )
    monkeypatch.setattr(
        BuffsManager,
        '_buff_active_in_area',
        lambda self, template, area: False,
    )
    monkeypatch.setattr(config, 'resolve_resource_path', lambda path: path)
    monkeypatch.setattr('buffs_manager.CV2_AVAILABLE', True)

    mgr = BuffsManager(num_buffs=1)
    mgr.buffs[0] = 'jobs/test.png'
    area = np.zeros((20, 80, 3), dtype=np.uint8)

    mgr.update_and_activate_buffs(1, None, None, area, 0, 0)
    assert sent == ['f1']

    clock['t'] += 1.0
    mgr.update_and_activate_buffs(1, None, None, area, 0, 0)
    assert sent == ['f1']
