"""Global configuration for Kathana Helper Lite."""
import os
import sys
import time


def app_dir():
    """Directory for settings (next to exe when frozen)."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


SETTINGS_FILE = os.path.join(app_dir(), 'settings_lite.json')

bot_running = False
bot_thread = None
selected_window = None
connected_window = None

auto_hp_enabled = False
auto_mp_enabled = False
mp_key = '9'
hp_thresholds = [{'threshold': 70, 'key': '0'}]
mp_threshold = 50

hp_bar_area = {'x': 0, 'y': 0, 'width': 0, 'height': 0}
mp_bar_area = {'x': 0, 'y': 0, 'width': 0, 'height': 0}

current_hp_percentage = 100.0
current_mp_percentage = 100.0
last_hp_capture_time = 0.0
last_mp_capture_time = 0.0

HP_CAPTURE_INTERVAL = 0.3
MP_CAPTURE_INTERVAL = 0.3
BOT_LOOP_SLEEP = 0.12


def default_skill_slots():
    slots = {}
    for i in range(1, 10):
        slots[i] = {'enabled': False, 'interval': 1.0, 'last_used': 0.0}
    slots[0] = {'enabled': False, 'interval': 1.0, 'last_used': 0.0}
    for i in range(1, 11):
        slots[f'f{i}'] = {'enabled': False, 'interval': 1.0, 'last_used': 0.0}
    return slots


skill_slots = default_skill_slots()

action_slots = {
    'target': {'enabled': True, 'interval': 2.0, 'last_used': 0.0, 'key': 'e', 'label': 'Target'},
    'attack': {'enabled': True, 'interval': 1.0, 'last_used': 0.0, 'key': 'r', 'label': 'Attack'},
    'pick': {'enabled': False, 'interval': 1.0, 'last_used': 0.0, 'key': 'f', 'label': 'Loot'},
}

mob_filter_enabled = False
mob_scan_area = {'x': 0, 'y': 0, 'width': 0, 'height': 0}
mob_match_threshold = 0.80
mob_match_margin = 0.03
mob_templates = []
current_mob_match = None
MOB_TEMPLATES_DIR = os.path.join(app_dir(), 'mob_templates')


def bar_area_configured(area):
    return area.get('width', 0) > 0 and area.get('height', 0) > 0


def reset_timers():
    now = time.time()
    for slot in skill_slots:
        skill_slots[slot]['last_used'] = now
    for slot in action_slots.values():
        slot['last_used'] = now


def reset_skill_timers():
    reset_timers()
