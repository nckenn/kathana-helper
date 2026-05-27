"""
Debug image I/O helpers — gate disk writes to avoid CPU/disk overhead during normal play.
"""
import os

import config


def should_save_debug_images():
    """True when debug mode or explicit SAVE_DEBUG_IMAGES is enabled."""
    import debug_utils
    return debug_utils.get_debug_enabled() or getattr(config, 'SAVE_DEBUG_IMAGES', False)


def save_cv2_image(path, image):
    """Write an image with cv2.imwrite only when debug saves are enabled."""
    if not should_save_debug_images():
        return False
    try:
        import cv2
        dirpath = os.path.dirname(path)
        if dirpath:
            os.makedirs(dirpath, exist_ok=True)
        cv2.imwrite(path, image)
        return True
    except Exception:
        return False
