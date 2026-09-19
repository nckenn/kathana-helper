"""Tests for shared template match margin helper."""
import cv2
import numpy as np

import match_utils


def test_template_match_with_margin_accepts_clear_peak():
    template = np.zeros((6, 6, 3), dtype=np.uint8)
    template[1:5, 1:5] = (40, 200, 40)
    area = np.zeros((24, 24, 3), dtype=np.uint8)
    area[8:14, 8:14] = template
    matched, conf, loc = match_utils.template_match_with_margin(area, template, 0.85, 0.05)
    assert matched is True
    assert conf >= 0.85
    assert loc is not None


def test_template_match_with_margin_rejects_ambiguous_peaks():
    template = np.zeros((8, 8, 3), dtype=np.uint8)
    template[:, :] = (0, 200, 0)
    area = np.zeros((40, 40, 3), dtype=np.uint8)
    area[4:12, 4:12] = template
    area[4:12, 20:28] = template
    matched, conf, _ = match_utils.template_match_with_margin(area, template, 0.5, 0.05)
    assert matched is False
    assert conf >= 0.5


def test_template_match_accepts_smooth_low_contrast_single_match():
    """A single clean match on a smooth icon must not be rejected as ambiguous.

    Real buff icons are smooth gradients: a 1px shift barely changes the
    correlation, so the runner-up pixel sits within `margin` of the peak. This
    is the exact case the old top-2-raw-pixels check falsely rejected, causing
    active buffs to never be detected and the key to be re-pressed forever.
    """
    grad = np.linspace(20, 220, 16, dtype=np.uint8)
    template = np.repeat(grad[None, :], 16, axis=0)
    template = np.stack([template] * 3, axis=-1)
    area = np.zeros((48, 48, 3), dtype=np.uint8)
    area[10:26, 10:26] = template

    matched, conf, loc = match_utils.template_match_with_margin(area, template, 0.7, 0.05)
    assert matched is True
    assert conf >= 0.7
    assert loc is not None
