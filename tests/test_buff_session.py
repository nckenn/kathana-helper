"""Tests for buff session hold (block retarget until buffs finish)."""
import time
from unittest.mock import MagicMock

import config
from buffs_manager import BuffsManager


def test_buff_session_starts_when_buff_missing(monkeypatch):
    mgr = BuffsManager(num_buffs=1)
    mgr.buffs[0] = 'jobs/test.png'
    config.buffs_config[0] = {'enabled': True, 'image_path': 'jobs/test.png', 'key': 'f1'}
    config.mob_detection_enabled = False
    config.is_buffing = False

    monkeypatch.setattr(mgr, '_buff_active_in_area', lambda template, area: False)
    monkeypatch.setattr(mgr, '_buff_template_for_index', lambda idx: ('p', object()))

    area = object()
    assert mgr.manage_buffing_session(area) is True
    assert config.is_buffing is True


def test_buff_session_ends_when_all_active(monkeypatch):
    mgr = BuffsManager(num_buffs=1)
    mgr.buffs[0] = 'jobs/test.png'
    config.buffs_config[0] = {'enabled': True, 'image_path': 'jobs/test.png', 'key': 'f1'}
    config.is_buffing = True
    config.buffing_start_time = time.time()

    monkeypatch.setattr(mgr, '_buff_active_in_area', lambda template, area: True)
    monkeypatch.setattr(mgr, '_buff_template_for_index', lambda idx: ('p', object()))

    area = object()
    assert mgr.manage_buffing_session(area) is False
    assert config.is_buffing is False


def test_buff_session_end_triggers_retarget(monkeypatch):
    mgr = BuffsManager(num_buffs=1)
    mgr.buffs[0] = 'jobs/test.png'
    config.buffs_config[0] = {'enabled': True, 'image_path': 'jobs/test.png', 'key': 'f1'}
    config.is_buffing = True
    config.buffing_start_time = time.time()
    config.auto_attack_enabled = True
    config.assist_only_enabled = False
    config.is_looting = False

    retarget = MagicMock()
    reset_timer = MagicMock()
    monkeypatch.setattr(
        'auto_attack._auto_target_manager.try_auto_target', retarget,
    )
    monkeypatch.setattr(
        'auto_attack._auto_target_manager.reset_search_timer', reset_timer,
    )
    monkeypatch.setattr(mgr, '_buff_active_in_area', lambda template, area: True)
    monkeypatch.setattr(mgr, '_buff_template_for_index', lambda idx: ('p', object()))

    mgr.manage_buffing_session(object())

    reset_timer.assert_called_once()
    retarget.assert_called_once_with('buffs finished')


def test_defer_retarget_when_buffs_pending(monkeypatch):
    import auto_attack

    mgr = BuffsManager(num_buffs=1)
    mgr.buffs[0] = 'jobs/test.png'
    config.buffs_manager = mgr
    config.buffs_config[0] = {'enabled': True, 'image_path': 'jobs/test.png', 'key': 'f1'}
    config.mob_detection_enabled = True
    config.mob_filter_safe_buffs = True
    config.is_looting = False
    config.is_buffing = False

    retarget = MagicMock(return_value=True)
    monkeypatch.setattr(auto_attack._auto_target_manager, 'try_auto_target', retarget)
    monkeypatch.setattr(mgr, 'needs_buff_refresh', lambda area: True)
    monkeypatch.setattr(auto_attack.bot_logic, '_capture_buff_active_area', lambda *a: object())
    monkeypatch.setattr(auto_attack.frame_cache, 'get_frame', lambda *a: object())
    monkeypatch.setattr(auto_attack.frame_cache, 'get_origin', lambda: (0, 0))

    assert auto_attack._try_retarget_unless_buffs_pending('loot finished', 123) is False
    retarget.assert_not_called()
