"""
Auto Rotate Camera - periodic 360° camera sweep.

On a fixed interval, holds right-click and drags the mouse to spin the view. This
overcomes inaccurate nameplate OCR / template matching caused by interfering
environmental backgrounds, and brings mobs occluded by terrain into view.

Deliberately interval-based rather than target-based: a mis-read target can still
register as "have target" (so the bot thinks it's engaged and never rotates), which
is exactly the stuck case we want to break out of. Only looting/buffing (brief,
would be disrupted) and Assist Only (party leader aims) suppress a rotation.

Camera rotation uses real (foreground) mouse input: turning the view is the whole
point of the feature, and most 3D games read camera look from raw mouse motion,
which background window-message input can't drive. It briefly focuses the game for
the ~0.3s rotation, then continues. (Keys/clicks/movement stay background.)
"""
import time
import config
import input_handler
import logger

# Approx horizontal drag pixels for a full 360° spin (used only for sweep logging).
_FULL_TURN_PIXELS = 1600


def reset():
    """Reset rotation timers/accumulator (called on bot start/stop)."""
    config.last_auto_rotate_time = 0
    config._auto_rotate_accum_pixels = 0


def check_auto_rotate():
    """Rotate the camera once every auto_rotate_interval seconds while enabled."""
    if not config.auto_rotate_enabled:
        return
    if not config.connected_window:
        return
    # Party leader aims in Assist Only; don't spin away from their target.
    if config.assist_only_enabled:
        return
    # Looting/buffing are short and would be broken by a camera drag.
    if config.is_looting or config.is_buffing:
        return

    now = time.time()
    if (now - config.last_auto_rotate_time) < config.auto_rotate_interval:
        return

    config.last_auto_rotate_time = now
    ok = input_handler.rotate_camera(
        drag_pixels=config.auto_rotate_drag_pixels,
        step_pixels=config.auto_rotate_step_pixels,
        direction=config.auto_rotate_direction,
        move_delay=config.auto_rotate_move_delay,
        foreground=True,
    )
    if not ok:
        return

    accum = getattr(config, '_auto_rotate_accum_pixels', 0) + abs(config.auto_rotate_drag_pixels)
    if accum >= _FULL_TURN_PIXELS:
        accum = 0
        logger.info("Completed ~360° camera sweep", "AutoRotate")
    config._auto_rotate_accum_pixels = accum
