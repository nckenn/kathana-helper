"""Tests for shared frame cache TTL and invalidation."""
import time

import config
import frame_cache


def test_frame_cache_ttl_reuses_frame(monkeypatch):
    calls = {'n': 0}

    def fake_capture(hwnd, calibrator):
        calls['n'] += 1
        import numpy as np
        return np.zeros((10, 10, 3), dtype=np.uint8), (0, 0)

    monkeypatch.setattr(frame_cache._frame_cache, '_capture', fake_capture)
    monkeypatch.setattr(config, 'get_frame_cache_ttl', lambda: 1.0)

    frame_cache.invalidate()
    f1 = frame_cache.get_frame(99, None)
    f2 = frame_cache.get_frame(99, None)
    assert f1 is not None
    assert f2 is f1
    assert calls['n'] == 1


def test_frame_cache_expires_after_ttl(monkeypatch):
    clock = {'t': 100.0}

    monkeypatch.setattr(time, 'time', lambda: clock['t'])
    monkeypatch.setattr(config, 'get_frame_cache_ttl', lambda: 0.05)

    calls = {'n': 0}

    def fake_capture(hwnd, calibrator):
        calls['n'] += 1
        import numpy as np
        return np.ones((8, 8, 3), dtype=np.uint8), (1, 2)

    monkeypatch.setattr(frame_cache._frame_cache, '_capture', fake_capture)
    frame_cache.invalidate()

    frame_cache.get_frame(7, None)
    clock['t'] += 0.1
    frame_cache.get_frame(7, None)
    assert calls['n'] == 2


def test_invalidate_clears_cached_frame(monkeypatch):
    import numpy as np

    monkeypatch.setattr(
        frame_cache._frame_cache,
        '_capture',
        lambda hwnd, calibrator: (np.zeros((4, 4, 3), dtype=np.uint8), (0, 0)),
    )
    frame_cache.get_frame(1, None)
    frame_cache.invalidate()
    assert frame_cache._frame_cache._frame is None
