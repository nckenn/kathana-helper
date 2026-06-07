"""Shared OpenCV template matching helpers."""
import numpy as np


def template_match_with_margin(area, template, threshold, margin=0.05):
    """
    Return (matched: bool, confidence: float, top_left or None).
    Rejects ambiguous matches when the second-best peak is within margin of the best.
    """
    import cv2

    if area is None or template is None or area.size == 0:
        return False, 0.0, None
    if area.shape[0] < template.shape[0] or area.shape[1] < template.shape[1]:
        return False, 0.0, None

    res = cv2.matchTemplate(area, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    confidence = float(max_val)
    if confidence < threshold:
        return False, confidence, None

    flat = res.ravel()
    if flat.size >= 2:
        idx = np.argpartition(flat, -2)[-2:]
        top2 = np.sort(flat[idx])[::-1]
        if top2[0] - top2[1] < margin:
            return False, confidence, None

    return True, confidence, max_loc
