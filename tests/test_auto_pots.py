"""Tests for auto-pots stale capture guard."""
import os
import sys

# Allow `python tests/test_auto_pots.py` (IDE run) without pytest loading conftest first.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import time

import config
import auto_pots


def test_is_capture_stale_after_double_interval():
    pots = auto_pots.AutoPots()
    now = 1000.0
    assert pots._is_capture_stale(now, 990.0, 5.0) is False
    assert pots._is_capture_stale(now, 989.9, 5.0) is True
    assert pots._is_capture_stale(now, 0, 5.0) is False


def test_skips_pots_when_hp_capture_stale(monkeypatch):
    config.bot_regions_ready = lambda: True
    config.connected_window = type('W', (), {'handle': 1})()
    config.auto_hp_enabled = True
    config.auto_mp_enabled = False
    config.hp_thresholds = [{'threshold': 70, 'key': '0'}]
    config.last_hp_capture_time = 0
    config.last_successful_hp_capture_time = 100.0
    config.current_hp_percentage = 30.0

    monkeypatch.setattr(config, 'get_hp_capture_interval', lambda: 0.3)
    monkeypatch.setattr(config, 'get_mp_capture_interval', lambda: 0.3)

    sent = []

    def fake_send(key):
        sent.append(key)

    import bar_reader
    import input_handler
    monkeypatch.setattr(input_handler, 'send_input', fake_send)
    monkeypatch.setattr(bar_reader, 'read_hp_percent', lambda hwnd: None)

    pots = auto_pots.AutoPots()
    pots.check_auto_pots()

    assert sent == []


if __name__ == '__main__':
    import pytest
    raise SystemExit(pytest.main([__file__, '-v']))
