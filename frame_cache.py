"""
Shared window frame cache — union region BitBlt when possible (Tier 4).
"""
import time

import config
import capture_regions
import window_utils


class FrameCache:
    def __init__(self):
        self._frame = None
        self._hwnd = None
        self._timestamp = 0.0
        self._origin = (0, 0)

    @property
    def origin(self):
        return self._origin

    def invalidate(self):
        self._frame = None
        self._hwnd = None
        self._timestamp = 0.0
        self._origin = (0, 0)

    def get_frame(self, hwnd, calibrator):
        """Return a cached BGR frame (full window or union region)."""
        if hwnd is None or calibrator is None:
            return None

        ttl = config.get_frame_cache_ttl()
        now = time.time()
        if (
            self._frame is not None
            and self._hwnd == hwnd
            and (now - self._timestamp) < ttl
        ):
            return self._frame

        frame, origin = self._capture(hwnd, calibrator)
        if frame is None:
            return None

        self._frame = frame
        self._hwnd = hwnd
        self._timestamp = now
        self._origin = origin
        return self._frame

    def _capture(self, hwnd, calibrator):
        rects = capture_regions.compute_capture_rects(calibrator)
        union = capture_regions.union_rect(rects)
        if union is None:
            try:
                screen = calibrator.capture_window(hwnd)
                return screen, (0, 0)
            except Exception:
                return None, (0, 0)

        x, y, w, h = union
        region = window_utils.capture_window_region_bgr(hwnd, x, y, w, h)
        if region is not None:
            return region, (x, y)

        try:
            screen = calibrator.capture_window(hwnd)
            return screen, (0, 0)
        except Exception:
            return None, (0, 0)


_frame_cache = FrameCache()


def get_frame(hwnd, calibrator):
    return _frame_cache.get_frame(hwnd, calibrator)


def get_origin():
    return _frame_cache.origin


def crop_rect(frame, x1, y1, x2, y2, origin=None):
    """Crop using window-image coordinates from a union or full frame."""
    if frame is None:
        return None
    if origin is None:
        origin = _frame_cache.origin
    ox, oy = origin
    return frame[y1 - oy:y2 - oy, x1 - ox:x2 - ox]


def invalidate():
    _frame_cache.invalidate()
