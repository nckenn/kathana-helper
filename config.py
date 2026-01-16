"""
Configuration file for Kathana Bot
Contains all global variables, constants, and default settings
"""

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

# HP/MP thresholds and areas
hp_threshold = 70  # Default HP threshold percentage (0-100)
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
mob_target_list = []  # List of mob names to target (only attack mobs in this list)
mob_detection_enabled = False
target_name_area = {'x': 381, 'y': 161, 'width': 0, 'height': 0}
target_hp_bar_area = {'x': 381, 'y': 183, 'width': 0, 'height': 0}
current_target_mob = None
mob_images = {}
MOB_LIST_FILE = "saved_mobs.json"
MOB_IMAGES_FOLDER = "mob_images"

# Auto repair system
system_message_area = {'x': 0, 'y': 0, 'width': 0, 'height': 0}
last_repair_time = 0
REPAIR_COOLDOWN = 5.0
AUTO_REPAIR_CHECK_INTERVAL = 1.0
last_auto_repair_check_time = 0

# Mob detection optimization
mob_detection_lock = None  # Will be initialized in mob_detection module
last_mob_detection_time = 0
MOB_DETECTION_INTERVAL = 1.0

# OCR settings
ocr_reader = None  # EasyOCR reader instance (lazy loaded)
ocr_use_gpu = True  # Try to use GPU if available, fallback to CPU if not
ocr_available = False  # Set to True if OCR check passes on startup
ocr_mode = None  # 'gpu', 'cpu', or None - indicates which mode OCR is using

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
SMART_LOOT_COOLDOWN = 0.2  # Cooldown between loot attempts (reduced for faster looting, allows retry if first fails)
is_looting = False  # Flag to prevent auto-targeting during looting
looting_start_time = 0
LOOTING_DURATION = 2.0  # Duration to prevent auto-targeting after looting starts (increased to allow loot to complete)
unstuck_timeout = 8.0
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

# Skills area (set during calibration) - (x_min, y_min, x_max, y_max)
area_skills = None

# Skill Sequence Manager instance
skill_sequence_manager = None  # Will be initialized in GUI

# Skill Sequence configuration (max 8 skills)
skill_sequence_config = {
    i: {
        'enabled': False,
        'image_path': None,
        'key': ''
    } for i in range(8)
}

# Current HP/MP percentages (updated by bot_logic, read by GUI)
current_hp_percentage = 100.0
current_mp_percentage = 100.0

# Current enemy HP percentage (updated by enemy_bar_detection, read by GUI)
current_enemy_hp_percentage = 0.0

# Current enemy name (updated by enemy_bar_detection/bot_logic, read by GUI)
current_enemy_name = None


def safe_update_gui(update_func):
    """Thread-safe GUI update - queue the update to be processed by GUI thread"""
    try:
        gui_update_queue.put(update_func, block=False)
    except queue.Full:
        pass  # Skip update if queue is full to prevent blocking


def resolve_resource_path(relative_path):
    """
    Resolve a relative resource path that works in both development and PyInstaller builds.
    
    Args:
        relative_path: Relative path string (e.g., "jobs/Nakayuda/1.BMP")
        
    Returns:
        Resolved absolute path, or None if path doesn't exist
    """
    if not relative_path:
        return None
    
    import os
    import sys
    
    # Normalize the path
    relative_path = os.path.normpath(relative_path)
    
    # Determine base path based on execution environment
    if getattr(sys, 'frozen', False):
        # Running as compiled executable (PyInstaller)
        base_path = sys._MEIPASS
    else:
        # Running as script
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    # Join base path with relative path
    resolved_path = os.path.join(base_path, relative_path)
    resolved_path = os.path.normpath(resolved_path)
    
    # Return path if it exists, otherwise None
    return resolved_path if os.path.exists(resolved_path) else None
