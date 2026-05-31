"""Background bot thread."""
import time
import threading
import config
import skill_timer
import action_timer
import mob_filter
import window_utils
from auto_pots import AutoPots

_auto_pots = AutoPots()


def _loop():
    while config.bot_running:
        if not config.connected_window:
            time.sleep(0.5)
            continue
        hwnd = window_utils.resolve_hwnd()
        if mob_filter.is_active() and hwnd:
            mob_filter.refresh_scan(hwnd)
        _auto_pots.check()
        action_timer.check_action_slots()
        skill_timer.check_skill_slots()
        time.sleep(config.BOT_LOOP_SLEEP)


def start():
    if config.bot_running:
        return
    config.bot_running = True
    config.reset_skill_timers()
    config.bot_thread = threading.Thread(target=_loop, daemon=True)
    config.bot_thread.start()


def stop():
    config.bot_running = False
