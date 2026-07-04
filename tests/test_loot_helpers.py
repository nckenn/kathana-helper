"""Tests for smart-loot lockout and retarget timing."""
import time

import config
import loot_helpers


def test_should_skip_during_active_lockout():
    config.is_looting = True
    config.looting_start_time = time.time()
    config.LOOTING_DURATION = 1.0
    config.last_smart_loot_time = config.looting_start_time
    assert loot_helpers.should_skip_loot() is True


def test_clear_expired_loot_lockout():
    config.is_looting = True
    config.looting_start_time = time.time() - 2.0
    config.LOOTING_DURATION = 1.0
    assert loot_helpers.clear_expired_loot_lockout() is True
    assert config.is_looting is False


def test_should_skip_after_recent_loot_start():
    config.is_looting = False
    config.last_smart_loot_time = time.time()
    config.SMART_LOOT_COOLDOWN = 0.5
    assert loot_helpers.should_skip_loot() is True
