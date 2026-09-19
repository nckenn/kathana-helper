"""Shared OpenCV template matching helpers."""


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

    # Reject only when a *spatially distinct* peak scores nearly as high (a
    # genuinely ambiguous match). The pixels immediately around the best peak
    # are near-identical to it — they belong to the same match blob — so we
    # suppress a template-sized neighborhood before looking for the runner-up.
    # Without this suppression, the runner-up is always an adjacent pixel and
    # every real match gets falsely rejected.
    th, tw = template.shape[:2]
    x, y = max_loc
    suppressed = res.copy()
    x0, y0 = max(0, x - tw), max(0, y - th)
    x1, y1 = min(res.shape[1], x + tw + 1), min(res.shape[0], y + th + 1)
    suppressed[y0:y1, x0:x1] = -1.0

    _, second_val, _, _ = cv2.minMaxLoc(suppressed)
    if second_val >= 0.0 and (confidence - second_val) < margin:
        return False, confidence, None

    return True, confidence, max_loc
