"""
Configuration file for Kathana Bot
Contains all global variables, constants, and default settings
"""
import os
import sys

APP_VERSION = "3.1.0"
APP_TITLE = f"Kathana Helper v{APP_VERSION}"


def app_dir():
    """Directory for settings and mob templates (next to exe when frozen)."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


# Bot state
bot_running = False
bot_thread = None
selected_window = None
connected_window = None  # Store the connected window reference
force_initial_target = False  # Flag to force auto-target on bot start

# Auto features flags
auto_attack_enabled = True
auto_hp_enabled = False
auto_mp_enabled = False
auto_change_target_enabled = True
auto_repair_enabled = False
mouse_clicker_enabled = False
is_mage = False  # If enabled, attack action won't be triggered after target

# Auto HP/MP/Repair hotkeys (configurable)
mp_key = '9'  # Default MP potion key
repair_key = 'f10'  # Default repair key

# HP/MP thresholds and areas
# Multiple HP thresholds: list of dicts with 'threshold' (0-100) and 'key' (str)
# Example: [{'threshold': 80, 'key': '0'}, {'threshold': 50, 'key': '3'}]
# Thresholds should be ordered from highest to lowest
hp_thresholds = [{'threshold': 70, 'key': '0'}]  # Default single threshold
hp_bar_area = {'x': 152, 'y': 69, 'width': 0, 'height': 0}
mp_threshold = 50  # Default MP threshold percentage (0-100)
mp_bar_area = {'x': 428, 'y': 139, 'width': 0, 'height': 0}

# Bar detection settings
BAR_DETECTION_DEBUG = False

# Performance / CPU optimization
SAVE_DEBUG_IMAGES = False
low_cpu_mode = True

# Idle + focus optimizations
pause_when_unfocused = False  # If True, pauses vision when game isn't focused (off for multitasking/alt-tab)
unfocused_sleep_seconds = 0.6
idle_mode_enabled = True
idle_after_seconds = 5.0  # Enter idle mode after this many seconds without an enemy
idle_bot_loop_sleep_seconds = 0.45
idle_enemy_hp_capture_interval = 0.75
last_enemy_seen_time = 0.0
last_enemy_name_seen_time = 0.0
enemy_name_missing_streak = 0


def is_idle(now=None) -> bool:
    if not idle_mode_enabled:
        return False
    if now is None:
        import time
        now = time.time()
    # On startup (or after reset), treat unknown as "not idle" so intervals stay stable.
    if last_enemy_seen_time <= 0:
        return False
    return (now - last_enemy_seen_time) >= idle_after_seconds

# Base intervals (normal mode) — use getters for effective values
_BASE_ENEMY_HP_CAPTURE_INTERVAL = 0.2
_BASE_HP_CAPTURE_INTERVAL = 0.3
_BASE_MP_CAPTURE_INTERVAL = 0.3
_BASE_BUFF_CHECK_INTERVAL = 0.5
_BASE_BOT_LOOP_SLEEP = 0.15
_BASE_FRAME_CACHE_TTL = 0.08
_BASE_GUI_STATUS_MS = 200
_BASE_GUI_UPDATES_MS = 100

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

# Mob detection system (CV template matching — no OCR for filter)
mob_detection_enabled = False
mob_scan_area = {'x': 0, 'y': 0, 'width': 0, 'height': 0}
mob_match_threshold = 0.87
mob_match_margin = 0.08
# Columns at/after this x-ratio are level digits (name identity uses the left portion).
mob_match_level_start_ratio = 0.68
mob_match_name_width_ratio = 0.68  # legacy alias; see mob_match_level_start_ratio
# Min fraction of name columns that must agree (works for any shared-prefix names).
mob_match_min_column_agreement = 0.70
mob_match_column_iou_min = 0.62
# Compare-time tolerance (not letter case — visual shape matching, no OCR)
mob_match_min_coverage = 0.55
mob_match_pixel_tolerance = 5
mob_match_dilate_px = 2
mob_text_gray_min = 140
mob_text_sat_max = 90
# Match on extracted UI text, ignoring terrain behind transparent nameplate
mob_normalize_match = True
mob_templates = []
current_mob_match = None
# Skip elite variants: same name template but higher max HP than learned normal mob
mob_elite_skip_enabled = True
mob_elite_sig_threshold = 0.82     # max-HP digit signature match (lower = elite)
# Pixel shift tolerance when comparing templates (UI sub-pixel drift / window move)
mob_match_shift_px = 3
mob_combat_shift_px = 1
mob_match_miss_streak = 0
mob_combat_miss_required = 2
mob_combat_match_grace_seconds = 0.3
mob_verify_attempts = 3
mob_verify_required = 2
mob_verify_delay_s = 0.06
last_mob_scan_time = 0
MOB_TEMPLATES_DIR = os.path.join(app_dir(), 'mob_templates')
target_name_area = {'x': 381, 'y': 161, 'width': 0, 'height': 0}
target_hp_bar_area = {'x': 381, 'y': 183, 'width': 0, 'height': 0}
current_target_mob = None
mob_images = {}
MOB_LIST_FILE = "saved_mobs.json"
MOB_IMAGES_FOLDER = "mob_images"


def bar_area_configured(area):
    return area.get('width', 0) > 0 and area.get('height', 0) > 0


def bot_regions_ready():
    """HP + MP regions picked — required to start the bot."""
    return bar_area_configured(hp_bar_area) and bar_area_configured(mp_bar_area)

# Auto repair system
system_message_area = {'x': 0, 'y': 0, 'width': 0, 'height': 0}
SYSTEM_MESSAGE_HEIGHT_REDUCTION = 100  # Reduce height by this many pixels (0 = no reduction)
last_repair_time = 0
REPAIR_COOLDOWN = 5.0
AUTO_REPAIR_CHECK_INTERVAL = 3.0  # Legacy default; use get_auto_repair_check_interval()
REPAIR_WARNING_CHECK_INTERVAL = 0.3  # Light-green warning text poll (300ms)
BREAK_WARNING_TRIGGER_COUNT = 10  # Detections required before repair triggers
last_auto_repair_check_time = 0

# Mob detection optimization
mob_detection_lock = None  # Will be initialized in mob_detection module
last_mob_detection_time = 0
MOB_DETECTION_INTERVAL = 1.0

# Settings file (next to exe / project root via app_dir())
SETTINGS_FILE = os.path.join(app_dir(), "bot_settings.json")

# HP/MP check optimization
last_hp_log_time = 0
last_mp_log_time = 0
last_enemy_hp_log_time = 0
HP_MP_LOG_INTERVAL = 5.0

# HP/MP capture throttling
last_hp_capture_time = 0
last_mp_capture_time = 0
last_successful_hp_capture_time = 0
last_successful_mp_capture_time = 0
last_enemy_hp_capture_time = 0
last_auto_target_time = 0
enemy_target_time = 0
last_smart_loot_time = 0
SMART_LOOT_COOLDOWN = 0.2  # Cooldown between loot attempts (reduced for faster looting, allows retry if first fails)
is_looting = False  # Flag to prevent auto-targeting during looting
looting_start_time = 0
LOOTING_DURATION = 1  # Duration to prevent auto-targeting after looting starts (reduced for faster retargeting)
unstuck_timeout = 8.0
# Min enemy HP change in percentage points (damage down or heal/bar up vs reference) resets auto-unstuck countdown.
# Lower = slow boss chip damage still refreshes the timer; too low may flutter from bar read noise.
hp_stagnant_noise_epsilon = 0.35
last_damage_detected_time = 0
last_damage_value = None
last_enemy_hp_for_unstuck = None  # Track last enemy HP for unstuck detection (HP-based instead of OCR)

enemy_hp_stagnant_time = 0  # Time when enemy HP became stagnant
last_enemy_hp_before_stagnant = None  # HP value when stagnation started
last_unstuck_check_time = 0
UNSTUCK_CHECK_INTERVAL = 1.0
HP_CAPTURE_INTERVAL = 0.3
MP_CAPTURE_INTERVAL = 0.3
ENEMY_HP_CAPTURE_INTERVAL = 0.2  # Reduced from 0.3 for faster enemy detection
# Target search interval (only used when no enemy found - after kill, bypasses this)
TARGET_SEARCH_INTERVAL = 1.5  # Reduced from 2.0 for faster searching when idle
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

# Calibration
calibrator = None  # Calibrator instance (set after calibration)

# AutoPots instance (shared, created once)
autopots_instance = None  # Will be initialized in bot_logic

# Buffs Manager instance
buffs_manager = None  # Will be initialized in GUI

# Buffs configuration (max 8 buffs)
buffs_config = {
    i: {
        'enabled': False,
        'image_path': None,
        'key': ''
    } for i in range(8)
}

# Manually picked UI regions (window-relative x, y, width, height)
skill_area = {'x': 0, 'y': 0, 'width': 0, 'height': 0}
buff_area = {'x': 0, 'y': 0, 'width': 0, 'height': 0}

# Skills area legacy tuple (x_min, y_min, x_max, y_max) — synced from skill_area
area_skills = None

# Skill Sequence Manager instance
skill_sequence_manager = None  # Will be initialized in GUI

# Skill Sequence configuration (max 8 skills)
skill_sequence_config = {
    i: {
        'enabled': False,
        'image_path': None,
        'key': '',
        'bypass': False  # If True, skip skill if not found (not on cooldown/available)
    } for i in range(8)
}

# Current HP/MP percentages (updated by bot_logic, read by GUI)
current_hp_percentage = 100.0
current_mp_percentage = 100.0

# Current enemy HP percentage (updated by enemy_bar_detection, read by GUI)
current_enemy_hp_percentage = 0.0

# Current enemy name (updated by enemy_bar_detection/bot_logic, read by GUI)
current_enemy_name = None

# Target UI name presence tracking (for stale HP bar cases)
# Some kills leave the red bar pixels visible briefly; name disappears sooner.
enemy_name_missing_streak_threshold = 3
enemy_name_missing_grace_seconds = 0.6

# Enemy HP bar color guardrails (helps on light backgrounds).
# Higher saturation threshold rejects pale/pink highlights that can look "red-ish".
enemy_hp_red_sat_min = 90
# Keep fairly permissive value: the bar can be dark in some scenes, but should not be near-black.
enemy_hp_red_val_min = 70

# Assist Only mode (party leader determines target, only attack when enemy HP decreases)
assist_only_enabled = False
assist_key = 'f9'  # Hotkey for assist mode (no icon clicking)
assist_click_interval_seconds = 1.0  # Min delay between assist presses
enemy_initial_hp = None  # Track initial HP when enemy is first detected (for assist_only mode)
enemy_detected = False  # Track if enemy has been detected (for assist_only mode)
# Store previous state of features that are disabled when assist_only is enabled
_assist_only_previous_auto_attack = None
_assist_only_previous_mob_detection = None
_assist_only_previous_auto_change_target = None


def get_enemy_hp_capture_interval():
    if is_idle():
        return idle_enemy_hp_capture_interval
    return 0.35 if low_cpu_mode else _BASE_ENEMY_HP_CAPTURE_INTERVAL


def get_hp_capture_interval():
    return 0.45 if low_cpu_mode else _BASE_HP_CAPTURE_INTERVAL


def get_mp_capture_interval():
    return 0.45 if low_cpu_mode else _BASE_MP_CAPTURE_INTERVAL


def get_buff_check_interval():
    # Buff icon checks rely on template matching; keep this a bit slower in Low CPU mode.
    return 0.80 if low_cpu_mode else _BASE_BUFF_CHECK_INTERVAL


def get_bot_loop_sleep():
    if is_idle():
        return idle_bot_loop_sleep_seconds
    return 0.20 if low_cpu_mode else _BASE_BOT_LOOP_SLEEP


def get_frame_cache_ttl():
    return 0.12 if low_cpu_mode else _BASE_FRAME_CACHE_TTL


def get_gui_status_interval_ms():
    return 350 if low_cpu_mode else _BASE_GUI_STATUS_MS


def get_gui_updates_interval_ms():
    return 100


def get_auto_repair_check_interval():
    """Poll warning region every 300ms; slightly relaxed in Low CPU mode."""
    return 0.45 if low_cpu_mode else REPAIR_WARNING_CHECK_INTERVAL


def get_mob_scan_interval():
    """Mob name-bar matching during combat (slower than enemy HP ticks)."""
    if is_idle():
        return 0.80
    return 0.65 if low_cpu_mode else 0.50


# Template matching thresholds (buffs, skills, skill bar icons)
buff_match_threshold = 0.7
skill_match_threshold = 0.7
template_match_margin = 0.05


def safe_update_gui(update_func):
    """Thread-safe GUI update - queue the update to be processed by GUI thread"""
    try:
        gui_update_queue.put(update_func, block=False)
    except queue.Full:
        pass  # Skip update if queue is full to prevent blocking


def apply_resource_path(relative_path):
    """Resolve a relative resource path for dev and PyInstaller (may not exist yet)."""
    if not relative_path:
        return None

    import os
    import sys

    relative_path = os.path.normpath(relative_path)
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(base_path, relative_path))


def resolve_resource_path(relative_path):
    """
    Resolve a relative resource path that works in both development and PyInstaller builds.

    Returns:
        Resolved absolute path, or None if path doesn't exist
    """
    import os
    resolved_path = apply_resource_path(relative_path)
    return resolved_path if resolved_path and os.path.exists(resolved_path) else None
