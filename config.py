"""
Configuration file for Kathana Bot
Contains all global variables, constants, and default settings
"""

# Bot state
bot_running = False
bot_thread = None
selected_window = None
connected_window = None  # Store the connected window reference

# Auto features flags
auto_attack_enabled = True
auto_hp_enabled = False
auto_mp_enabled = False
auto_change_target_enabled = True
auto_repair_enabled = False
mouse_clicker_enabled = False

# HP/MP thresholds and areas
hp_threshold = 50  # Default HP threshold percentage (0-100)
hp_bar_area = {'x': 152, 'y': 69, 'width': 0, 'height': 0}
mp_threshold = 50  # Default MP threshold percentage (0-100)
mp_bar_area = {'x': 428, 'y': 139, 'width': 0, 'height': 0}

# Bar detection settings
BAR_DETECTION_DEBUG = False

# Skill slot system
skill_slots = {
    1: {'enabled': True, 'interval': 1, 'last_used': 0},
    2: {'enabled': True, 'interval': 1, 'last_used': 0},
    3: {'enabled': False, 'interval': 1, 'last_used': 0},
    4: {'enabled': True, 'interval': 1, 'last_used': 0},
    5: {'enabled': False, 'interval': 1, 'last_used': 0},
    6: {'enabled': False, 'interval': 1, 'last_used': 0},
    7: {'enabled': True, 'interval': 10, 'last_used': 0},
    8: {'enabled': True, 'interval': 103, 'last_used': 0},
    'f1': {'enabled': False, 'interval': 1, 'last_used': 0},
    'f2': {'enabled': False, 'interval': 1, 'last_used': 0},
    'f3': {'enabled': False, 'interval': 1, 'last_used': 0},
    'f4': {'enabled': False, 'interval': 1, 'last_used': 0},
    'f5': {'enabled': False, 'interval': 1, 'last_used': 0},
    'f6': {'enabled': False, 'interval': 1, 'last_used': 0},
    'f7': {'enabled': False, 'interval': 1, 'last_used': 0},
    'f8': {'enabled': False, 'interval': 1, 'last_used': 0},
    'f9': {'enabled': False, 'interval': 1, 'last_used': 0},
    'f10': {'enabled': False, 'interval': 1, 'last_used': 0}
}

# Action slot system
action_slots = {
    'target': {'enabled': True, 'interval': 2, 'last_used': 0, 'key': 'e'},
    'attack': {'enabled': True, 'interval': 1, 'last_used': 0, 'key': 'r'},
    'pick': {'enabled': False, 'interval': 1, 'last_used': 0, 'key': 'f'}
}

# Mob detection system
mob_skip_list = []
mob_detection_enabled = False
target_name_area = {'x': 381, 'y': 161, 'width': 0, 'height': 0}
target_hp_bar_area = {'x': 381, 'y': 183, 'width': 0, 'height': 0}
current_target_mob = None
mob_images = {}
MOB_LIST_FILE = "saved_mobs.json"
MOB_IMAGES_FOLDER = "mob_images"

# Auto repair system
system_message_area = {'x': 0, 'y': 0, 'width': 0, 'height': 0}
low_damage_count = 0
low_damage_threshold = 200
low_damage_trigger_count = 5
last_repair_time = 0
REPAIR_COOLDOWN = 5.0
AUTO_REPAIR_CHECK_INTERVAL = 1.0
last_auto_repair_check_time = 0
low_damage_timestamps = []
LOW_DAMAGE_TIME_WINDOW = 10.0

# Mob detection optimization
mob_detection_lock = None  # Will be initialized in mob_detection module
last_mob_detection_time = 0
MOB_DETECTION_INTERVAL = 1.0

# OCR settings
ocr_reader = None  # EasyOCR reader instance (lazy loaded)

# Settings file
SETTINGS_FILE = "bot_settings.json"

# HP/MP check optimization
last_hp_log_time = 0
last_mp_log_time = 0
last_enemy_hp_log_time = 0
HP_MP_LOG_INTERVAL = 5.0

# HP/MP capture throttling
last_hp_capture_time = 0
last_mp_capture_time = 0
last_enemy_hp_capture_time = 0
last_auto_target_time = 0
enemy_target_time = 0
last_smart_loot_time = 0
SMART_LOOT_COOLDOWN = 1.0
unstuck_timeout = 10.0
last_damage_detected_time = 0
last_damage_value = None
last_unstuck_check_time = 0
UNSTUCK_CHECK_INTERVAL = 1.0
HP_CAPTURE_INTERVAL = 0.3
MP_CAPTURE_INTERVAL = 0.3
ENEMY_HP_CAPTURE_INTERVAL = 0.3
AUTO_TARGET_COOLDOWN = 3.0
MOB_VERIFICATION_DELAY = 0.5
last_mob_verification_time = 0

# HP/MP smoothing
hp_readings = []
mp_readings = []
enemy_hp_readings = []
HP_MP_SMOOTHING_WINDOW = 3

# Mouse clicker system
mouse_clicker_interval = 5.0
mouse_clicker_use_cursor = True
mouse_clicker_coords = {'x': 0, 'y': 0}
mouse_clicker_last_used = 0

# Thread-safe GUI update queue
import queue
gui_update_queue = queue.Queue(maxsize=200)


def safe_update_gui(update_func):
    """Thread-safe GUI update - queue the update to be processed by GUI thread"""
    try:
        gui_update_queue.put(update_func, block=False)
    except queue.Full:
        pass  # Skip update if queue is full to prevent blocking
