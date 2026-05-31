"""Interval-based skill key presses for slots 1-0 and F1-F10."""
import time
import config
import input_handler
import mob_filter
import window_utils


def _slot_key(slot_num):
    if isinstance(slot_num, int):
        return str(slot_num)
    if isinstance(slot_num, str) and slot_num.lower().startswith('f'):
        return slot_num.lower()
    return str(slot_num)


def trigger_skill(slot_num):
    input_handler.send_input(_slot_key(slot_num))


def check_skill_slots():
    hwnd = window_utils.resolve_hwnd()
    if mob_filter.is_active() and (not hwnd or not mob_filter.should_allow_combat(hwnd)):
        return

    now = time.time()
    for slot_num, slot_data in config.skill_slots.items():
        if not slot_data['enabled']:
            continue
        if now - slot_data['last_used'] >= slot_data['interval']:
            trigger_skill(slot_num)
            config.skill_slots[slot_num]['last_used'] = now
