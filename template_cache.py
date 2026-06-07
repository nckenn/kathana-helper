"""
Template cache for cv2.imread results.

Avoid repeated disk reads in hot loops (buffs/skills).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass
class _Entry:
    mtime_ns: int
    img: object


_cache: Dict[Tuple[str, int], _Entry] = {}
_MAX_CACHE_ENTRIES = 64


def get_template(path: str, flags: int):
    """Return cached cv2.imread(path, flags) result (or load and cache it)."""
    import os

    try:
        st = os.stat(path)
        mtime_ns = int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9)))
    except Exception:
        mtime_ns = -1

    key = (path, int(flags))
    entry = _cache.get(key)
    if entry is not None and entry.mtime_ns == mtime_ns:
        return entry.img

    import cv2

    img = cv2.imread(path, flags)
    if len(_cache) >= _MAX_CACHE_ENTRIES:
        oldest = next(iter(_cache))
        _cache.pop(oldest, None)
    _cache[key] = _Entry(mtime_ns=mtime_ns, img=img)
    return img


def clear() -> None:
    _cache.clear()

