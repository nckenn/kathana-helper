"""Tests for CV-based auto repair break warning detection."""
import os

import cv2
import numpy as np
import auto_repair


FIXTURE = os.path.join(
    os.path.dirname(__file__), 'fixtures', 'break_warning_sample.png',
)


def _load_fixture():
    img = cv2.imread(FIXTURE)
    assert img is not None, f'Missing fixture: {FIXTURE}'
    return img


def test_detects_green_break_warning_line():
    detected, info = auto_repair.analyze_break_warning(_load_fixture())
    assert detected is True
    assert info['best_line_width'] >= auto_repair.MIN_WARNING_LINE_WIDTH
    assert info['qualifying_rows'] >= 1


def test_ignores_magenta_only_region():
    img = _load_fixture()
    # Damage-only lines at the top (no green warning row)
    top = img[:18]
    detected, _ = auto_repair.analyze_break_warning(top)
    assert detected is False


def test_black_image_no_detection():
    img = np.zeros((40, 200, 3), dtype=np.uint8)
    detected, _ = auto_repair.analyze_break_warning(img)
    assert detected is False


def test_rejects_short_green_line():
    img = np.zeros((40, 200, 3), dtype=np.uint8)
    img[25, 50:130] = (100, 220, 120)
    detected, info = auto_repair.analyze_break_warning(img)
    assert detected is False
    assert info.get('qualifying_rows', 0) < auto_repair.MIN_QUALIFYING_ROWS


def test_rejects_sparse_green_scatter():
    """Wide span with few pixels must not count (old false-positive path)."""
    mask = np.zeros((40, 200), dtype=np.uint8)
    mask[25, 40] = 255
    mask[25, 160] = 255
    mask[25, 90] = 255
    mask[25, 100] = 255
    assert not auto_repair._row_qualifies_break_warning(mask[25])


def test_accepts_dense_break_warning_row():
    fixture = _load_fixture()
    mask = auto_repair.build_warning_green_mask(fixture)
    assert auto_repair._row_qualifies_break_warning(mask[24])


def test_break_warning_tracker_counts_each_poll():
    tracker = auto_repair.BreakWarningTracker()
    t = 1000.0
    for i in range(10):
        tracker.add_detection(t + i * 0.3)
    assert tracker.get_count() == 10
    assert tracker.should_trigger_repair()


def test_break_warning_tracker_clears_after_repair():
    tracker = auto_repair.BreakWarningTracker()
    for i in range(10):
        tracker.add_detection(float(i))
    tracker.clear()
    assert tracker.get_count() == 0
    assert not tracker.should_trigger_repair()


def test_reset_repair_count_clears_tracker_and_visibility(monkeypatch):
    monkeypatch.setattr(auto_repair, 'update_repair_count_display', lambda: None)
    tracker = auto_repair.BreakWarningTracker()
    detector = auto_repair.WarningTextDetector()
    tracker.add_detection(1.0)
    detector._warning_visible = True
    auto_repair._break_warning_tracker = tracker
    auto_repair._warning_detector = detector
    auto_repair.reset_repair_count()
    assert tracker.get_count() == 0
    assert detector._warning_visible is False
    auto_repair._break_warning_tracker = auto_repair.BreakWarningTracker()
    auto_repair._warning_detector = auto_repair.WarningTextDetector()


def test_warning_detector_counts_new_appearances_only(monkeypatch):
    detector = auto_repair.WarningTextDetector()
    fixture = _load_fixture()

    monkeypatch.setattr(detector, 'capture_warning_region', lambda _hwnd: fixture)

    assert detector.detect_break_warning(1) is True
    assert detector.detect_break_warning(1) is False
    assert detector.detect_break_warning(1) is False

    monkeypatch.setattr(
        detector,
        'capture_warning_region',
        lambda _hwnd: np.zeros((40, 200, 3), dtype=np.uint8),
    )
    assert detector.detect_break_warning(1) is False

    monkeypatch.setattr(detector, 'capture_warning_region', lambda _hwnd: fixture)
    assert detector.detect_break_warning(1) is True
