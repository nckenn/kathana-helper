"""Detect player/enemy HP and MP bars in the game UI (glossy bars + number overlay)."""
import cv2
import numpy as np

BAR_MIN_HEIGHT = 6
BAR_MAX_HEIGHT = 22
HP_MP_MAX_GAP = 22
ROW_RUN_GAP = 22
ROW_CLOSE_WIDTH = 19

# Sampled from in-game HP/MP bars (glossy red ~8869/8869, blue ~6702/6702).
# HSV uses OpenCV scale: H 0-180, S/V 0-255.
HP_HSV_LOW1 = np.array([0, 70, 65])
HP_HSV_HIGH1 = np.array([14, 255, 245])
HP_HSV_LOW2 = np.array([165, 70, 65])
HP_HSV_HIGH2 = np.array([180, 255, 245])
MP_HSV_LOW = np.array([108, 65, 85])
MP_HSV_HIGH = np.array([128, 255, 255])


def build_red_mask(bgr):
    """Red HP bar mask — tuned HSV from game bars plus R-dominant fallback for highlights."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, HP_HSV_LOW1, HP_HSV_HIGH1)
    mask = cv2.bitwise_or(mask, cv2.inRange(hsv, HP_HSV_LOW2, HP_HSV_HIGH2))
    b, g, r = cv2.split(bgr)
    r16, g16, b16 = r.astype(np.int16), g.astype(np.int16), b.astype(np.int16)
    dominant = ((r16 - g16) > 30) & ((r16 - b16) > 30) & (r > 90)
    mask = cv2.bitwise_or(mask, dominant.astype(np.uint8) * 255)
    return mask


def build_blue_mask(bgr):
    """Blue MP bar mask — tuned HSV from game bars plus B-dominant fallback."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, MP_HSV_LOW, MP_HSV_HIGH)
    b, g, r = cv2.split(bgr)
    b16, g16, r16 = b.astype(np.int16), g.astype(np.int16), r.astype(np.int16)
    dominant = ((b16 - r16) > 25) & ((b16 - g16) > 15) & (b > 90)
    mask = cv2.bitwise_or(mask, dominant.astype(np.uint8) * 255)
    return mask


def _bar_width_limits(image_width):
    """Scale bar width bounds with capture size (full-window vs small UI crop)."""
    min_w = max(50, int(image_width * 0.055))
    if image_width <= 400:
        max_w = image_width
    else:
        max_w = max(min_w + 1, min(500, int(image_width * 0.45)))
    return min_w, max_w


def _split_row_runs(column_indices, max_gap=ROW_RUN_GAP):
    """Split a row's active columns into contiguous horizontal runs."""
    if column_indices.size == 0:
        return []
    runs = []
    start = int(column_indices[0])
    prev = start
    for col in column_indices[1:]:
        col = int(col)
        if col - prev > max_gap:
            runs.append((start, prev - start + 1))
            start = col
        prev = col
    runs.append((start, prev - start + 1))
    return runs


def _row_merged_mask(mask_u8):
    """Bridge horizontal gaps from white numbers without merging separate bars vertically."""
    h, w = mask_u8.shape[:2]
    close_k = cv2.getStructuringElement(cv2.MORPH_RECT, (ROW_CLOSE_WIDTH, 1))
    out = np.zeros_like(mask_u8)
    for y in range(h):
        row = mask_u8[y : y + 1, :]
        out[y : y + 1, :] = cv2.morphologyEx(row, cv2.MORPH_CLOSE, close_k)
    return out


def _find_row_band_segments(mask_u8):
    """Collect (x, y, w, 1) segments from each row's in-range horizontal runs."""
    merged = _row_merged_mask(mask_u8)
    h, w = merged.shape[:2]
    min_w, max_w = _bar_width_limits(w)
    segments = []
    for y in range(h):
        cols = np.where(merged[y] > 0)[0]
        for x0, run_w in _split_row_runs(cols):
            if min_w <= run_w <= max_w:
                segments.append([x0, y, run_w, 1])
    return segments, merged


def _segments_overlap_x(a, b, ratio=0.45):
    ax, _, aw, _ = a
    bx, _, bw, _ = b
    overlap = min(ax + aw, bx + bw) - max(ax, bx)
    return overlap >= min(aw, bw) * ratio


def _merge_segments_to_bands(segments, image_width):
    """Merge vertically adjacent row segments that share horizontal overlap."""
    if not segments:
        return []
    min_w, max_w = _bar_width_limits(image_width)
    segments = sorted(segments, key=lambda item: (item[1], item[0]))
    bands = []
    for seg in segments:
        sx, sy, sw, _ = seg
        placed = False
        for band in bands:
            bx, by, bw, bh = band
            if sy < by or sy > by + bh + 1:
                continue
            if not _segments_overlap_x(band, seg):
                continue
            new_x = min(bx, sx)
            new_x2 = max(bx + bw, sx + sw)
            band[0] = new_x
            band[1] = by
            band[2] = new_x2 - new_x
            band[3] = max(by + bh, sy + 1) - by
            placed = True
            break
        if not placed:
            bands.append([sx, sy, sw, 1])
    return [
        tuple(band)
        for band in bands
        if BAR_MIN_HEIGHT <= band[3] <= BAR_MAX_HEIGHT and min_w <= band[2] <= max_w
    ]


def find_bar_bands(mask_u8):
    """Return sorted list of (x, y, w, h) wide horizontal bars."""
    h, w = mask_u8.shape[:2]
    segments, merged = _find_row_band_segments(mask_u8)
    bands = _merge_segments_to_bands(segments, w)
    bands.sort(key=lambda item: item[1])
    return bands, merged


def _x_overlap_ratio(red, blue):
    rx, _, rw, _ = red
    bx, _, bw, _ = blue
    overlap = min(rx + rw, bx + bw) - max(rx, bx)
    if overlap <= 0:
        return 0.0
    return overlap / float(min(rw, bw))


def _valid_hp_mp_pair(red, blue):
    """True when blue sits directly under red with enough horizontal overlap."""
    rx, ry, rw, rh = red
    bx, by, bw, bh = blue
    gap = by - (ry + rh)
    if gap < 0 or gap > HP_MP_MAX_GAP:
        return False
    return _x_overlap_ratio(red, blue) >= 0.35


def _has_enemy_hp_below(mp_rect, red_bands, min_gap=12, max_gap=55):
    """Player panel in this UI has a second red HP bar below MP (target/enemy row)."""
    _, my, mw, mh = mp_rect
    mp_bottom = my + mh
    for red in red_bands:
        rx, ry, rw, rh = red
        if ry <= mp_bottom + min_gap or ry > mp_bottom + max_gap:
            continue
        if _x_overlap_ratio(mp_rect, red) >= 0.35:
            return True
    return False


def _pair_quality(red, blue):
    """Score a valid pair by alignment only — no fixed screen position."""
    rx, ry, rw, rh = red
    bx, by, bw, bh = blue
    gap = by - (ry + rh)
    overlap = _x_overlap_ratio(red, blue)
    gap_score = max(0.0, float(HP_MP_MAX_GAP - gap) / float(HP_MP_MAX_GAP))
    width_score = min(rw, bw) / float(max(rw, bw))
    return overlap * 0.75 + gap_score * 0.15 + width_score * 0.1


def pair_player_hp_mp(red_bands, blue_bands, image_h=None, image_w=None):
    """
    Match player HP (red) with MP (blue) directly below using color bands only.
    When several stacks qualify, prefer the one with enemy HP below MP (player UI stack).
    Otherwise pick the best-aligned pair (any screen position).
    """
    del image_h, image_w
    candidates = []
    for red in red_bands:
        for blue in blue_bands:
            if not _valid_hp_mp_pair(red, blue):
                continue
            rx, ry, _, _ = red
            has_enemy = _has_enemy_hp_below(blue, red_bands)
            candidates.append(
                (has_enemy, _pair_quality(red, blue), ry, rx, red, blue)
            )
    if not candidates:
        return None, None
    candidates.sort(key=lambda item: (-int(item[0]), -item[1], item[2], item[3]))
    return candidates[0][4], candidates[0][5]


def find_player_hp_mp(bgr):
    """
    Locate player HP and MP bar bounding boxes.
    Returns (hp_rect, mp_rect) as (x, y, w, h) or (None, None).
    """
    h, w = bgr.shape[:2]
    red_mask = build_red_mask(bgr)
    blue_mask = build_blue_mask(bgr)
    red_bands, red_merged = find_bar_bands(red_mask)
    blue_bands, blue_merged = find_bar_bands(blue_mask)

    hp, mp = pair_player_hp_mp(red_bands, blue_bands, h, w)
    if hp and mp:
        return hp, mp, red_merged, blue_merged, red_bands, blue_bands

    if blue_bands:
        best_red = None
        best_mp = None
        best_key = None
        for blue in blue_bands:
            for red in red_bands:
                if not _valid_hp_mp_pair(red, blue):
                    continue
                key = (
                    _has_enemy_hp_below(blue, red_bands),
                    _pair_quality(red, blue),
                    red[1],
                    red[0],
                )
                if best_key is None or key > best_key:
                    best_key, best_red, best_mp = key, red, blue
        if best_red and best_mp:
            return best_red, best_mp, red_merged, blue_merged, red_bands, blue_bands
        mp = blue_bands[0]
        bx, by, bw, bh = mp
        est_h = 14
        hp = (bx, max(0, by - est_h - 4), bw, est_h)
        return hp, mp, red_merged, blue_merged, red_bands, blue_bands

    if red_bands:
        hp = red_bands[0]
        rx, ry, rw, rh = hp
        for blue in blue_bands:
            if _valid_hp_mp_pair(hp, blue):
                return hp, blue, red_merged, blue_merged, red_bands, blue_bands
        mp = (rx, ry + rh + 4, rw, 15)
        return hp, mp, red_merged, blue_merged, red_bands, blue_bands

    return None, None, red_merged, blue_merged, red_bands, blue_bands
