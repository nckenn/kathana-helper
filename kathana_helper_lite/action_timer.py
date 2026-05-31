"""Interval-based target / attack / loot key presses."""
import time
import config
import input_handler
import mob_filter
import window_utils


def check_action_slots():
    now = time.time()
    hwnd = window_utils.resolve_hwnd()
    filtering = mob_filter.is_active()
    for name, slot in config.action_slots.items():
        if not slot['enabled']:
            continue
        if now - slot['last_used'] < slot['interval']:
            continue
        if filtering and name in ('target', 'attack'):
            if not hwnd or not mob_filter.should_allow_action(name, hwnd):
                continue
        input_handler.send_input(slot['key'])
        slot['last_used'] = now
