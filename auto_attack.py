"""
Auto-attack system for enemy detection and targeting
Detects enemy HP bar position and percentage relative to player MP bar
Uses CV template matching for mob filtering
"""
import numpy as np
import cv2
import time
import os
import threading
import config
import input_handler
import bot_logic
import mob_filter
import debug_utils
import skill_bar_actions
import debug_io
import frame_cache
import hp_number_reader
import region_helpers
import ui_bar_detection


# Initialize lock for thread-safe mob detection
if config.mob_detection_lock is None:
    config.mob_detection_lock = threading.Lock()


# ============================================================================
# Constants
# ============================================================================

# Search area dimensions relative to MP position
SEARCH_AREA_OFFSET_Y = 19  # Pixels below MP position
SEARCH_AREA_WIDTH = 210    # Width of search area (updated to match new UI)
SEARCH_AREA_HEIGHT = 35    # Height of search area
SEARCH_AREA_OFFSET_X = -1  # X offset from MP position

# Enemy name area dimensions
NAME_AREA_HEIGHT = 18      # Height of name area (first 18 pixels)

# HP bar detection parameters
HP_BAR_HEIGHT = 18         # Height of HP bar strip to search
MIN_RED_PIXELS_PER_COLUMN = 6  # Minimum red pixels per column to be valid
HP_BAR_CENTER_OFFSET = 9   # Y offset to center of HP bar
MIN_HP_BAR_WIDTH = 10     # Minimum HP bar width to consider valid (avoid false positives from small red artifacts)

MOB_VERIFICATION_INTERVAL = 2.0  # Seconds between mob verifications during combat

# HP detection thresholds
HP_JUMP_THRESHOLD_LOW = 50   # If last avg < this and new >= 95, enemy died
HP_JUMP_THRESHOLD_HIGH = 95
HP_DEATH_THRESHOLD = 3.0     # HP percentage below which enemy is considered dead
HP_PREVIOUS_READING_MIN = 10.0  # Minimum previous reading to trigger death detection

# Targeting parameters - optimized for fast retargeting after kill
MAX_RETARGET_RECURSION = 5
RETARGET_DELAY_INITIAL = 0.05  # Reduced from 0.1 for faster initial targeting
RETARGET_DELAY_RECURSIVE = 0.08  # Reduced from 0.15 for faster retries
RETARGET_DELAY_BETWEEN = 0.12  # Reduced from 0.25 for faster retargeting when skipping
MOB_VERIFICATION_DELAY = 0.1  # Reduced from 0.2 for faster verification


# ============================================================================
# Mob Filtering Functions
# ============================================================================

def should_target_current_mob():
    """True when CV mob filter is off, or current target matches a learned template."""
    if mob_filter.is_active():
        return config.current_mob_match is not None
    return True


def detect_and_verify_mob_after_target(delay=0.05, retry_delay=0.08):
    """
    Detect and verify mob after retargeting (reusable function)
    Uses calibration-based detection to get enemy name and verify if it should be targeted
    
    Args:
        delay: Initial delay before detection (default: 0.15s)
        retry_delay: Delay before retry if first detection fails (default: 0.1s)
        
    Returns:
        dict: {
            'detected': bool,
            'name': str or None,
            'should_target': bool,
            'needs_retarget': bool  # True if mob detected but not in target list
        }
    """
    if not config.connected_window:
        return {'detected': False, 'name': None, 'should_target': False, 'needs_retarget': False}

    hwnd = config.connected_window.handle

    if mob_filter.is_active():
        if not mob_filter.scan_area_available():
            return {'detected': False, 'name': None, 'should_target': False, 'needs_retarget': False}
        # Slow-but-safe: require stable match across multiple frames.
        # Transparent UI backgrounds can cause single-frame false positives.
        match = mob_filter.refresh_scan_stable(hwnd)
        if not match and retry_delay > 0:
            time.sleep(retry_delay)
            match = mob_filter.refresh_scan_stable(hwnd)
        detected_mob = match['name'] if match else None
        should_target = match is not None
        needs_retarget = match is None
        if detected_mob:
            config.last_mob_detection_time = time.time()
        return {
            'detected': bool(detected_mob),
            'name': detected_mob,
            'should_target': should_target,
            'needs_retarget': needs_retarget,
        }

    if not region_helpers.combat_detection_ready():
        return {'detected': False, 'name': None, 'should_target': False, 'needs_retarget': False}

    # Minimal delay to allow mob name to appear after targeting (optimized for speed)
    if delay > 0:
        time.sleep(delay)

    return {
        'detected': False,
        'name': None,
        'should_target': True,
        'needs_retarget': False,
    }


def _detect_enemy_from_target_strip(hwnd, screen=None):
    """Detect enemy HP from manual/calibrated target strip (name + HP bar area)."""
    strip = hp_number_reader.get_enemy_target_strip_rect(config.calibrator)
    if strip is None:
        return EnemyDetectionResult().to_dict()

    try:
        if screen is None:
            screen = frame_cache.get_frame(hwnd, config.calibrator)
        if screen is None:
            return EnemyDetectionResult().to_dict()

        search_x, search_y, strip_w, strip_h = strip
        search_x2 = search_x + strip_w
        search_y2 = search_y + strip_h
        search_area = frame_cache.crop_rect(
            screen,
            search_x, search_y,
            search_x2, search_y2,
            frame_cache.get_origin(),
        )

        if search_area.size == 0:
            return EnemyDetectionResult(screen=screen).to_dict()

        hp_only = (
            config.bar_area_configured(config.target_hp_bar_area)
            and search_area.shape[0] < NAME_AREA_HEIGHT
        )
        if hp_only:
            import bar_reader
            hp_percentage = bar_reader.hp_percent_from_bgr(search_area)
            found = hp_percentage > 0.5
            cx = search_x + search_area.shape[1] // 2
            cy = search_y + search_area.shape[0] // 2
            return EnemyDetectionResult(
                found=found,
                hp=float(hp_percentage),
                position=(cx, cy),
                screen=screen,
            ).to_dict()

        if search_area.shape[0] < NAME_AREA_HEIGHT:
            return EnemyDetectionResult(screen=screen).to_dict()

        # Prefer band detection (wide horizontal bar) over "red pixels per column".
        # Light backgrounds can produce false-positive red-ish pixels, but rarely form a valid bar band.
        mask = _enemy_hp_red_mask(search_area)
        bands, _ = ui_bar_detection.find_bar_bands(mask)
        min_y = max(0, NAME_AREA_HEIGHT - 2)
        hp_bands = [b for b in bands if b[1] >= min_y]
        if not hp_bands:
            return EnemyDetectionResult(found=False, screen=screen).to_dict()

        bx, by, bw, bh = max(hp_bands, key=lambda b: b[2])
        if bw < MIN_HP_BAR_WIDTH:
            return EnemyDetectionResult(found=False, screen=screen).to_dict()

        enemy_x = search_x + int(bx)
        enemy_y = search_y + int(by) + int(bh // 2)
        bar_width = max(strip_w, 1)
        hp_percentage = float(max(0, min(100, (bw / bar_width) * 100)))
        return EnemyDetectionResult(
            found=True,
            hp=hp_percentage,
            position=(enemy_x, enemy_y),
            screen=screen,
        ).to_dict()
    except Exception as e:
        print(f"[Enemy HP Detection] Strip scan error: {e}")
        return EnemyDetectionResult().to_dict()


# ============================================================================
# Helper Classes
# ============================================================================

class EnemyDetectionResult:
    """Container for enemy detection results"""
    def __init__(self, found=False, hp=0.0, position=None, screen=None):
        self.found = found
        self.hp = hp
        self.position = position
        self.screen = screen

    def to_dict(self):
        result = {
            'found': self.found,
            'hp': self.hp,
            'position': self.position,
        }
        if self.screen is not None:
            result['screen'] = self.screen
        return result


class EnemyStateManager:
    """Manages enemy state and tracking"""
    
    @staticmethod
    def reset_enemy_state():
        """Reset all enemy-related state variables"""
        config.enemy_target_time = 0
        config.enemy_hp_readings.clear()
        config.last_damage_value = None
        config.last_enemy_hp_for_unstuck = None
        config.enemy_hp_stagnant_time = 0
        config.last_enemy_hp_before_stagnant = None
        config.last_mob_verification_time = 0
        config.current_enemy_hp_percentage = 0.0
        config.current_target_mob = None
        config.current_enemy_name = None
        config.last_enemy_name_seen_time = 0.0
        config.enemy_name_missing_streak = 0
        # Reset assist_only enemy tracking when enemy state is reset
        reset_enemy_tracking()
    
    @staticmethod
    def initialize_new_enemy(current_time, hp_percentage):
        """Initialize tracking for a new enemy target"""
        config.enemy_target_time = current_time
        config.last_unstuck_check_time = 0
        config.last_enemy_hp_for_unstuck = None
        config.last_damage_detected_time = current_time
        config.enemy_hp_stagnant_time = current_time
        config.last_enemy_hp_before_stagnant = hp_percentage


class EnemyHpBarDetector:
    """Handles HP bar detection logic"""
    
    def __init__(self, debug_dir=None):
        self.debug_dir = debug_dir or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'debug'
        )
        self._ensure_debug_dir()
    
    def _ensure_debug_dir(self):
        """Ensure debug directory exists"""
        if not os.path.exists(self.debug_dir):
            os.makedirs(self.debug_dir)
    
    def extract_search_area(self, screen, mp_x, mp_y):
        """Extract the search area for enemy HP bar"""
        search_y = mp_y + SEARCH_AREA_OFFSET_Y
        search_x = mp_x + SEARCH_AREA_OFFSET_X
        search_area = screen[
            search_y:search_y + SEARCH_AREA_HEIGHT,
            search_x:search_x + SEARCH_AREA_WIDTH
        ]
        return search_area, search_x, search_y
    
    def extract_name_area(self, search_area):
        """Extract the enemy name area from search area"""
        return search_area[0:NAME_AREA_HEIGHT, :]
    
    def create_red_mask(self, search_area):
        """Create a mask for red HP bar detection"""
        # Keep enemy HP detection consistent with `ui_bar_detection` (player bars).
        return _enemy_hp_red_mask(search_area)
    
    def find_hp_bar(self, mask, search_area):
        """Find the widest HP bar in the mask (vectorized strip scan)."""
        h, w = mask.shape
        bar_h = HP_BAR_HEIGHT
        num_strips = h - bar_h + 1
        if num_strips <= 0:
            return None, 0, 0, 0

        try:
            strips = np.lib.stride_tricks.sliding_window_view(
                mask, (bar_h, w), axis=(0, 1))[:, 0, :, :]
            col_counts = (strips == 255).sum(axis=1)
        except Exception:
            col_counts = None

        best_y = None
        best_width = 0
        best_first = 0
        best_last = 0

        if col_counts is not None:
            for y in range(num_strips):
                cols = np.where(col_counts[y] >= MIN_RED_PIXELS_PER_COLUMN)[0]
                if len(cols) == 0:
                    continue
                first = int(cols[0])
                last = int(cols[-1])
                width = last - first + 1
                if width > best_width:
                    best_width = width
                    best_y = y
                    best_first = first
                    best_last = last
            return best_y, best_width, best_first, best_last

        for y in range(num_strips):
            strip = mask[y:y + bar_h, :]
            column_sum = np.sum(strip == 255, axis=0)
            valid_columns = np.where(column_sum >= MIN_RED_PIXELS_PER_COLUMN)[0]
            if len(valid_columns) > 0:
                first = int(valid_columns[0])
                last = int(valid_columns[-1])
                width = last - first + 1
                if width > best_width:
                    best_width = width
                    best_y = y
                    best_first = first
                    best_last = last

        return best_y, best_width, best_first, best_last
    
    def calculate_hp_percentage(self, bar_width):
        """Calculate HP percentage from bar width"""
        hp_percentage = bar_width / SEARCH_AREA_WIDTH * 100
        return float(max(0, min(100, hp_percentage)))
    
    def save_debug_images(self, search_area, mask, name_area,
                          hp_bar_found=None, enemy_x=None, enemy_y=None):
        """Save debug images for troubleshooting"""
        if not debug_io.should_save_debug_images():
            return
        debug_io.save_cv2_image(
            os.path.join(self.debug_dir, 'enemy_hp_search_area.png'), search_area)
        debug_io.save_cv2_image(
            os.path.join(self.debug_dir, 'enemy_hp_mask_red.png'), mask)
        debug_io.save_cv2_image(
            os.path.join(self.debug_dir, 'enemy_name_area_debug.png'), name_area)
        if hp_bar_found is not None and enemy_x is not None and enemy_y is not None:
            debug_io.save_cv2_image(
                os.path.join(self.debug_dir, f'enemy_hp_bar_found_{enemy_x}_{enemy_y}.png'),
                hp_bar_found)


class EnemyHpProcessor:
    """Processes and smooths enemy HP readings"""
    
    @staticmethod
    def detect_enemy_death(raw_hp, hp_readings):
        """Detect if enemy died based on HP jump or low HP"""
        if not hp_readings:
            return False
        
        # Check for HP jump (enemy respawned or new enemy)
        last_avg = sum(hp_readings) / len(hp_readings)
        if last_avg < HP_JUMP_THRESHOLD_LOW and raw_hp >= HP_JUMP_THRESHOLD_HIGH:
            return True
        
        # Check for death (HP dropped from high to very low)
        if (raw_hp <= HP_DEATH_THRESHOLD and len(hp_readings) > 1):
            previous_readings = hp_readings[:-1]
            if previous_readings and max(previous_readings) > HP_PREVIOUS_READING_MIN:
                return True
        
        return False
    
    @staticmethod
    def update_hp_readings(raw_hp, hp_readings):
        """Update HP readings with smoothing"""
        hp_readings.append(raw_hp)
        if len(hp_readings) > config.HP_MP_SMOOTHING_WINDOW:
            hp_readings.pop(0)
        return sum(hp_readings) / len(hp_readings)
    
    @staticmethod
    def update_stagnant_tracking(current_time, hp_percentage):
        """Update HP stagnant tracking for unstuck detection (slow boss DPS resets timer)."""
        eps = getattr(config, "hp_stagnant_noise_epsilon", 0.35)
        if config.last_enemy_hp_before_stagnant is None:
            config.enemy_hp_stagnant_time = current_time
            config.last_enemy_hp_before_stagnant = hp_percentage
            return

        ref = config.last_enemy_hp_before_stagnant
        if hp_percentage < ref - eps:
            config.enemy_hp_stagnant_time = current_time
            config.last_enemy_hp_before_stagnant = hp_percentage
        elif hp_percentage > ref + eps:
            config.enemy_hp_stagnant_time = current_time
            config.last_enemy_hp_before_stagnant = hp_percentage


# ============================================================================
# Main Detection Function
# ============================================================================

def detect_enemy_for_auto_attack(hwnd, screen=None):
    """
    Detect enemy HP percentage for auto-attack.
    Uses manually picked enemy HP region when configured, else calibration fallback.
    """
    if config.bar_area_configured(config.target_hp_bar_area):
        try:
            import bar_reader
            import frame_cache
            area = config.target_hp_bar_area
            if screen is None:
                screen = frame_cache.get_frame(hwnd, config.calibrator)
            if screen is not None:
                region = frame_cache.crop_rect(
                    screen,
                    area['x'], area['y'],
                    area['x'] + area['width'], area['y'] + area['height'],
                    frame_cache.get_origin(),
                )
            else:
                import window_utils
                region = window_utils.capture_window_region_bgr(
                    hwnd, area['x'], area['y'], area['width'], area['height'],
                )
            if region is not None and region.size > 0:
                hp_percentage = bar_reader.hp_percent_from_bgr(region)
                found = hp_percentage > 0.5
                cx = area['x'] + area['width'] // 2
                cy = area['y'] + area['height'] // 2
                out = EnemyDetectionResult(
                    found=found,
                    hp=float(hp_percentage),
                    position=(cx, cy),
                    screen=screen,
                ).to_dict()
                # Even when HP is manually picked, try to detect if the target name row is present.
                out.update(_detect_enemy_name_presence(hwnd, screen=screen))
                return out
        except Exception as e:
            print(f"[Enemy HP Detection] Manual region error: {e}")

    out = _detect_enemy_from_target_strip(hwnd, screen)
    out.update(_detect_enemy_name_presence(hwnd, screen=out.get('screen')))
    return out


def _detect_enemy_name_presence(hwnd, screen=None):
    """
    Lightweight presence check: does the enemy name/level row contain UI text?
    Helps retarget when HP bar pixels linger after a kill.
    """
    # Prefer manually picked regions when available; fallback to calibrator.
    rect = hp_number_reader.get_enemy_name_bar_rect(None)
    if rect is None:
        return {'name_present': None, 'name_text_pixels': 0}
    x, y, w, h = rect
    if w <= 0 or h <= 0:
        return {'name_present': None, 'name_text_pixels': 0}

    if screen is None:
        try:
            screen = frame_cache.get_frame(hwnd, config.calibrator)
        except Exception:
            screen = None

    if screen is not None:
        try:
            crop = frame_cache.crop_rect(
                screen, x, y, x + w, y + h, frame_cache.get_origin(),
            )
        except Exception:
            crop = None
    else:
        try:
            import window_utils
            crop = window_utils.capture_window_region_bgr(hwnd, x, y, w, h)
        except Exception:
            crop = None

    if crop is None or crop.size == 0:
        return {'name_present': None, 'name_text_pixels': 0}

    try:
        # Reuse the mob-filter normalization (bright/low-sat UI text) for robustness.
        # This avoids tying "name present" to a single exact color profile.
        import mob_filter
        norm = mob_filter.normalize_for_match(crop)
        if norm is None or norm.size == 0:
            return {'name_present': None, 'name_text_pixels': 0}
        pixels = int((norm > 0).sum())
        # Threshold is intentionally small: we only need to know if the row is "alive".
        min_pixels = int(getattr(config, 'enemy_name_present_min_pixels', 45))
        return {'name_present': pixels >= min_pixels, 'name_text_pixels': pixels}
    except Exception:
        return {'name_present': None, 'name_text_pixels': 0}


def _enemy_hp_red_mask(bgr):
    """
    Red mask for enemy HP bar detection.

    Uses the general red mask but suppresses low-saturation bright pixels that show up
    as "pink/red-ish" on light backgrounds and can linger after kills.
    """
    if bgr is None or bgr.size == 0:
        return np.zeros((0, 0), dtype=np.uint8)
    base = ui_bar_detection.build_red_mask(bgr)
    try:
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        sat = hsv[:, :, 1]
        val = hsv[:, :, 2]
        sat_min = int(getattr(config, 'enemy_hp_red_sat_min', 55))
        val_min = int(getattr(config, 'enemy_hp_red_val_min', 70))
        # Keep pixels that are sufficiently saturated and not too dim.
        keep = (sat >= sat_min) & (val >= val_min)
        return cv2.bitwise_and(base, keep.astype(np.uint8) * 255)
    except Exception:
        return base

# ============================================================================
# Assist Only Mode Logic
# ============================================================================

def should_attack_basic(enemy_hp=None):
    """
    Determines if basic attack (R key) should be executed based on assist_only mode.
    In assist_only mode, only attacks when enemy HP decreases (indicating leader has started attacking).
    
    Args:
        enemy_hp: Current enemy HP percentage (0-100), or None if not available
        
    Returns:
        bool: True if should attack, False if not
    """
    if not config.assist_only_enabled:
        return True  # Normal mode: always attack
    
    # Assist only mode: don't use basic attack (assist button handles attacking)
    return False


def should_use_skills(enemy_hp=None):
    """
    Determines if skills should be used based on assist_only mode.
    In assist_only mode, skills are always used (no HP decrease check needed since assist button handles targeting).
    
    Args:
        enemy_hp: Current enemy HP percentage (0-100), or None if not available (unused in assist_only mode)
        
    Returns:
        bool: True if should use skills, False if not
    """
    if not config.assist_only_enabled:
        return True  # Normal mode: always use skills
    
    # Assist only mode: always use skills (assist button already handles targeting/attacking)
    return True


def reset_enemy_tracking():
    """Reset enemy tracking when target is lost (for assist_only mode)"""
    config.enemy_initial_hp = None
    config.enemy_detected = False
    print('[Assist Only] Enemy tracking reset')


def check_assist_key():
    """Assist mode: press configured assist hotkey on interval."""
    if not config.assist_only_enabled:
        return

    if not config.connected_window:
        return

    key = (config.assist_key or '').strip()
    if not key:
        return

    interval = getattr(config, "assist_click_interval_seconds", 1.0)
    current_time = time.time()
    if not hasattr(check_assist_key, 'last_click_time'):
        check_assist_key.last_click_time = 0

    if current_time - check_assist_key.last_click_time < interval:
        return

    try:
        import input_handler
        input_handler.send_input(key)
        check_assist_key.last_click_time = current_time
        debug_utils.debug_print(f'Assist key pressed: {key!r}', 'AssistOnly')
    except Exception as e:
        print(f'[Assist Only] Error pressing assist key: {e}')


# ============================================================================
# Retargeting Logic
# ============================================================================

class RetargetManager:
    """Unified retargeting manager - handles all retargeting logic"""
    
    @staticmethod
    def retarget_with_mob_check(
        recursion_depth=0,
        max_recursion=MAX_RETARGET_RECURSION,
        reset_state_on_skip=True,
        context=""
    ):
        """
        Unified retargeting method with mob verification and recursive retry
        
        Used everywhere: auto-targeting, after unstuck, after enemy death, etc.
        
        Args:
            recursion_depth: Current recursion depth (for internal use)
            max_recursion: Maximum recursion depth (default: MAX_RETARGET_RECURSION)
            reset_state_on_skip: If True, reset enemy state when skipping mob
            context: Context string for logging (e.g., "after unstuck", "auto-target")
            
        Returns:
            dict: {
                'success': bool,
                'mob_name': str or None,
                'needs_retarget': bool,
                'max_recursion_reached': bool
            }
        """
        # Don't auto-target if assist_only is enabled (party leader determines target)
        if config.assist_only_enabled:
            return {
                'success': False,
                'mob_name': None,
                'needs_retarget': False,
                'max_recursion_reached': False
            }
        
        if not config.auto_attack_enabled:
            return {
                'success': False,
                'mob_name': None,
                'needs_retarget': False,
                'max_recursion_reached': False
            }

        if config.is_looting:
            return {
                'success': False,
                'mob_name': None,
                'needs_retarget': False,
                'max_recursion_reached': False
            }
        
        if recursion_depth >= max_recursion:
            print(f"[Retarget] Max retries reached ({max_recursion}), stopping retarget loop")
            return {
                'success': False,
                'mob_name': None,
                'needs_retarget': True,
                'max_recursion_reached': True
            }
        
        target_key = config.action_slots['target']['key']
        input_handler.send_input(target_key)
        
        mob_filter_enabled = mob_filter.is_active()
        
        # Trigger attack action after target action (sequence: target -> attack)
        # Only if mob filter is NOT enabled (if enabled, attack will be triggered after mob filter check)
        # Skip attack if mage mode is enabled
        # Check assist_only mode: only attack if should_attack_basic returns True
        if not mob_filter_enabled and not config.is_mage:
            # Get current enemy HP for assist_only check
            enemy_hp_for_check = None
            if config.assist_only_enabled and config.current_enemy_hp_percentage > 0:
                enemy_hp_for_check = config.current_enemy_hp_percentage
            
            if should_attack_basic(enemy_hp_for_check):
                attack_key = config.action_slots['attack']['key']
                # Small delay to ensure target action completes before attack
                time.sleep(0.1)
                input_handler.send_input(attack_key)
        
        # Minimal delay to ensure mob name appears after targeting (optimized for speed)
        delay = (RETARGET_DELAY_RECURSIVE if recursion_depth > 0 
                 else RETARGET_DELAY_INITIAL)
        if delay > 0:
            time.sleep(delay)
        
        # Detect and verify mob after retarget (no additional delay, already delayed above)
        mob_result = detect_and_verify_mob_after_target(
            delay=0,  # Already delayed above
            retry_delay=RETARGET_DELAY_RECURSIVE
        )
        detected_mob = mob_result['name']
        
        # Check if mob needs retargeting (not in target list)
        if mob_result['needs_retarget']:
            context_str = f" ({context})" if context else ""
            print(
                f"[Retarget] Skipping mob: {detected_mob} "
                f"(no CV template match, retry {recursion_depth + 1}/{max_recursion}){context_str}"
            )
            
            if reset_state_on_skip:
                EnemyStateManager.reset_enemy_state()
                config.current_target_mob = None
                config.current_enemy_name = None
            
            # Minimal delay before retrying (optimized for speed)
            if RETARGET_DELAY_BETWEEN > 0:
                time.sleep(RETARGET_DELAY_BETWEEN)
            
            # Recursively retarget
            return RetargetManager.retarget_with_mob_check(
                recursion_depth=recursion_depth + 1,
                max_recursion=max_recursion,
                reset_state_on_skip=reset_state_on_skip,
                context=context
            )
        
        # Trigger attack action after mob filter check (if mob filter is enabled)
        # Skip attack if mage mode is enabled
        # Check assist_only mode: only attack if should_attack_basic returns True
        if mob_filter_enabled and not config.is_mage:
            # Get current enemy HP for assist_only check
            enemy_hp_for_check = None
            if config.assist_only_enabled and config.current_enemy_hp_percentage > 0:
                enemy_hp_for_check = config.current_enemy_hp_percentage
            
            if should_attack_basic(enemy_hp_for_check):
                attack_key = config.action_slots['attack']['key']
                # Small delay to ensure target action completes before attack
                time.sleep(0.1)
                input_handler.send_input(attack_key)
        
        return {
            'success': True,
            'mob_name': detected_mob,
            'needs_retarget': False,
            'max_recursion_reached': False
        }


# ============================================================================
# Auto-Targeting Logic
# ============================================================================

class AutoTargetManager:
    """Manages auto-targeting logic"""
    
    def __init__(self):
        self.last_target_search_time = 0
    
    def should_search_for_target(self, current_time):
        """Check if enough time has passed to search for a new target"""
        return (current_time - self.last_target_search_time >= 
                config.TARGET_SEARCH_INTERVAL)
    
    def reset_search_timer(self):
        """Reset target search timer to allow immediate retargeting"""
        self.last_target_search_time = 0
    
    def update_search_timer(self, current_time):
        """Update target search timer"""
        self.last_target_search_time = current_time
    
    def try_auto_target(self, reason=""):
        """Attempt to auto-target an enemy (uses RetargetManager)"""
        # Don't auto-target if assist_only is enabled (party leader determines target)
        if config.assist_only_enabled:
            return False
        
        # Don't auto-target if we're currently looting
        if config.is_looting:
            return False
        
        if config.auto_attack_enabled:
            context = f"auto-target ({reason})" if reason else "auto-target"
            RetargetManager.retarget_with_mob_check(
                reset_state_on_skip=True,
                context=context
            )
            if reason:
                print(f"Auto-targeting ({reason})")
            return True
        return False


# ============================================================================
# Main Check Function
# ============================================================================

# Global instance for maintaining state
_auto_target_manager = AutoTargetManager()


def _trigger_smart_loot_safe():
    """Run smart loot without blocking retarget if loot module fails in frozen builds."""
    try:
        bot_logic.smart_loot()
    except Exception as e:
        config.is_looting = False
        current_time = time.time()
        if (current_time - config.last_enemy_hp_log_time >=
                config.HP_MP_LOG_INTERVAL):
            print(f"[Auto Attack] Smart loot failed: {e}")
            config.last_enemy_hp_log_time = current_time


def _mob_match_lost_during_combat(prev_match):
    """True when CV match disappeared while actively fighting a matched mob."""
    return (
        mob_filter.is_active()
        and prev_match is not None
        and config.current_mob_match is None
        and config.enemy_target_time > 0
        and not config.is_looting
    )


def _finish_kill_with_loot(reason):
    """Trigger loot and reset combat state after a kill."""
    print(f"[Auto Attack] {reason} - triggering smart loot")
    _trigger_smart_loot_safe()
    EnemyStateManager.reset_enemy_state()
    _auto_target_manager.reset_search_timer()
    if config.skill_sequence_manager:
        config.skill_sequence_manager.reset_sequence()


def check_auto_attack():
    """Check enemy HP bar and update GUI display, auto-target when no target"""
    # Don't auto-target if assist_only is enabled (party leader determines target)
    # But still monitor enemy HP for assist_only logic
    if config.assist_only_enabled:
        # Still check enemy HP for assist_only mode, but don't auto-target
        # The assist_only logic will handle when to attack based on HP decrease
        pass  # Continue to HP monitoring below
    
    # Only monitor enemy HP when auto attack is enabled (or assist_only is enabled)
    # If disabled, reset all enemy state and stop monitoring
    if not config.auto_attack_enabled and not config.assist_only_enabled:
        config.current_enemy_hp_percentage = 0.0
        # Reset enemy state to prevent any lingering state
        EnemyStateManager.reset_enemy_state()
        return
    
    if not config.connected_window:
        return
    
    current_time = time.time()
    if (current_time - config.last_enemy_hp_capture_time <
            config.get_enemy_hp_capture_interval()):
        return
    
    config.last_enemy_hp_capture_time = current_time
    
    # Block retarget / mob-filter scans while loot window is active
    if config.is_looting:
        if current_time - config.looting_start_time >= config.LOOTING_DURATION:
            config.is_looting = False
        else:
            return

    # Require enemy detection regions (manual pick or legacy calibrator)
    if not region_helpers.combat_detection_ready():
        config.current_enemy_hp_percentage = 0.0
        return
    
    try:
        hwnd = config.connected_window.handle
        enemy_hp_percentage = 0.0
        
        cv_mob_filter = mob_filter.is_active()
        prev_mob_match = config.current_mob_match if cv_mob_filter else None

        result = detect_enemy_for_auto_attack(hwnd)
        
        if result['found']:
            raw_enemy_hp_percentage = result['hp']
            has_red_bar = True
            config.last_enemy_seen_time = current_time
            
        else:
            has_red_bar = False
            raw_enemy_hp_percentage = 0.0

        # Track whether the enemy name row exists (can disappear earlier than HP pixels).
        name_present = result.get('name_present', None)
        if has_red_bar and name_present is False:
            config.enemy_name_missing_streak = int(getattr(config, 'enemy_name_missing_streak', 0)) + 1
        else:
            config.enemy_name_missing_streak = 0
            if name_present is True:
                config.last_enemy_name_seen_time = current_time

        if cv_mob_filter and not config.is_looting:
            if has_red_bar:
                mob_filter.refresh_scan(hwnd)
            else:
                mob_filter.clear_match()

        mob_match_lost = _mob_match_lost_during_combat(prev_mob_match)
        
        # Handle case when no enemy is found
        if not has_red_bar:
            config.enemy_name_missing_streak = 0
            # Check if we had an enemy recently (multiple conditions to catch all cases)
            # Also check if we detected a name but no HP bar (enemy might be dead but name still visible briefly)
            had_enemy = (
                len(config.enemy_hp_readings) > 0 or 
                config.enemy_target_time > 0 or
                config.current_target_mob is not None or
                config.current_enemy_name is not None
            )
            
            if had_enemy:
                # Enemy was killed - trigger smart loot first
                # This handles the case where enemy bar disappears (enemy died)
                reason = "enemy bar disappeared"
                print(
                    f"[Auto Attack] Enemy disappeared ({reason}) - triggering smart loot "
                    f"(had_enemy: readings={len(config.enemy_hp_readings)}, "
                    f"target_time={config.enemy_target_time}, mob={config.current_target_mob})"
                )
                _trigger_smart_loot_safe()
                EnemyStateManager.reset_enemy_state()
                _auto_target_manager.reset_search_timer()
                
                # Reset skill sequence when enemy is lost
                if config.skill_sequence_manager:
                    config.skill_sequence_manager.reset_sequence()
                
                # smart_loot() now handles timing and clears is_looting when done
                # Retarget immediately if looting is complete
                if not config.is_looting:
                    _auto_target_manager.try_auto_target("enemy killed")
                return
            
            EnemyStateManager.reset_enemy_state()
            
            # Reset skill sequence when no enemy found
            if config.skill_sequence_manager:
                config.skill_sequence_manager.enemy_found_previous = False
                config.skill_sequence_manager.skill_sequence_index = 0
                config.skill_sequence_manager.skill_waiting_activation = False
            
            # Try auto-targeting if not looting and interval has passed
            if not config.is_looting:
                if _auto_target_manager.should_search_for_target(current_time):
                    _auto_target_manager.try_auto_target("no enemy detected")
                    _auto_target_manager.update_search_timer(current_time)
        else:
            # Stale HP bar case: name row is gone but red pixels linger (common right after kill).
            # If this persists for a few frames, treat target as lost and retarget (no loot trigger).
            streak_threshold = int(getattr(config, 'enemy_name_missing_streak_threshold', 3))
            grace_s = float(getattr(config, 'enemy_name_missing_grace_seconds', 0.6))
            if (name_present is False
                    and config.enemy_target_time > 0
                    and (current_time - config.enemy_target_time) >= grace_s
                    and config.enemy_name_missing_streak >= streak_threshold):
                print(
                    f"[Auto Attack] Target name missing for {config.enemy_name_missing_streak} frames "
                    f"while HP bar still visible — forcing retarget"
                )
                EnemyStateManager.reset_enemy_state()
                _auto_target_manager.reset_search_timer()
                if not config.is_looting:
                    _auto_target_manager.try_auto_target("target name missing (stale HP)")
                return

            # After a kill the mob name often clears before the HP bar.
            if mob_match_lost:
                _finish_kill_with_loot(
                    "Mob template match lost during combat (likely kill)"
                )
                return

            # Block combat when mob filter is on but target is not on the whitelist.
            if (cv_mob_filter and not config.is_looting
                    and not should_target_current_mob()):
                print("[Mob Filter] No whitelist match — retargeting")
                EnemyStateManager.reset_enemy_state()
                if config.skill_sequence_manager:
                    config.skill_sequence_manager.reset_sequence()
                if MOB_VERIFICATION_DELAY > 0:
                    time.sleep(MOB_VERIFICATION_DELAY)
                _auto_target_manager.try_auto_target("non-target mob detected")
                return

            # Process enemy HP percentage
            if config.enemy_hp_readings:
                # Check for enemy death
                if EnemyHpProcessor.detect_enemy_death(
                    raw_enemy_hp_percentage, config.enemy_hp_readings
                ):
                    enemy_hp_percentage = 0.0
                    EnemyStateManager.reset_enemy_state()
                    # Trigger smart loot when enemy death is detected via HP jump
                    print(f"[Auto Attack] Enemy death detected (HP jump) - triggering smart loot")
                    _trigger_smart_loot_safe()
                    _auto_target_manager.reset_search_timer()
                    # smart_loot() now handles timing and clears is_looting when done
                    if not config.is_looting:
                        _auto_target_manager.try_auto_target("enemy died")
                    # Reset skill sequence when enemy dies
                    if config.skill_sequence_manager:
                        config.skill_sequence_manager.reset_sequence()
                    return
                
                # Update HP readings with smoothing
                enemy_hp_percentage = EnemyHpProcessor.update_hp_readings(
                    raw_enemy_hp_percentage, config.enemy_hp_readings
                )
                
                # Update stagnant tracking
                EnemyHpProcessor.update_stagnant_tracking(
                    current_time, enemy_hp_percentage
                )
                
                # Execute skill sequence when enemy is found (only if any skills are enabled)
                # Check assist_only mode: only use skills if should_use_skills returns True
                if (config.skill_sequence_manager and config.area_skills and
                    any(
                        config.skill_sequence_config[i]['image_path']
                        and config.skill_sequence_config[i]['enabled']
                        for i in range(8)
                    )):
                    if (should_use_skills(enemy_hp_percentage)
                            and should_target_current_mob()):
                        try:
                            skill_screen = result.get('screen')
                            if skill_screen is None:
                                skill_screen = frame_cache.get_frame(hwnd, config.calibrator)
                            if skill_screen is not None:
                                config.skill_sequence_manager.execute_skill_sequence(
                                    hwnd, skill_screen, config.area_skills,
                                    enemy_found=True, run_active=config.bot_running,
                                )
                        except Exception as e:
                            print(f"[AutoAttack] Error executing skill sequence: {e}")
                
                if (cv_mob_filter and config.enemy_target_time > 0 and
                        not config.is_looting and
                        current_time - config.last_mob_verification_time > MOB_VERIFICATION_INTERVAL):
                    config.last_mob_verification_time = current_time
                    prev_verify_match = config.current_mob_match
                    mob_filter.refresh_scan_stable(hwnd)
                    if _mob_match_lost_during_combat(prev_verify_match):
                        _finish_kill_with_loot(
                            "Mob template match lost during periodic verification"
                        )
                        return
                    if config.current_mob_match is None:
                        print("[Mob Filter] Lost CV match during combat — retargeting")
                        EnemyStateManager.reset_enemy_state()
                        if config.skill_sequence_manager:
                            config.skill_sequence_manager.reset_sequence()
                        if MOB_VERIFICATION_DELAY > 0:
                            time.sleep(MOB_VERIFICATION_DELAY)
                        _auto_target_manager.try_auto_target(
                            "non-target mob detected during combat"
                        )
                        return
                
                # Check for death (HP dropped from high to very low)
                # Also check if HP bar width is suspiciously small (might be false positive or dead enemy)
                if (raw_enemy_hp_percentage <= HP_DEATH_THRESHOLD and 
                    config.enemy_target_time > 0 and 
                    len(config.enemy_hp_readings) > 1):
                    previous_readings = config.enemy_hp_readings[:-1]
                    if (previous_readings and 
                        max(previous_readings) > HP_PREVIOUS_READING_MIN):
                        print(
                            f"[Auto Attack] Enemy HP dropped from {max(previous_readings):.1f}% "
                            f"to {raw_enemy_hp_percentage:.1f}% - triggering smart loot"
                        )
                        # Trigger smart loot when HP drops to death threshold
                        _trigger_smart_loot_safe()
                        enemy_hp_percentage = 0.0
                        EnemyStateManager.reset_enemy_state()
                        _auto_target_manager.reset_search_timer()
                        # smart_loot() now handles timing and clears is_looting when done
                        if not config.is_looting:
                            _auto_target_manager.try_auto_target("enemy died")
                        # Reset skill sequence when enemy dies
                        if config.skill_sequence_manager:
                            config.skill_sequence_manager.reset_sequence()
                        return
                
                # Additional check: if HP is very low and we've been tracking this enemy,
                # it might be dead (handles cases where HP bar is still visible but enemy is dead)
                if (raw_enemy_hp_percentage <= HP_DEATH_THRESHOLD and 
                    config.enemy_target_time > 0 and
                    current_time - config.enemy_target_time > 1.0):  # Enemy tracked for at least 1 second
                    print(
                        f"[Auto Attack] Enemy HP very low ({raw_enemy_hp_percentage:.1f}%) "
                        f"after tracking for {current_time - config.enemy_target_time:.1f}s - "
                        f"assuming enemy is dead, triggering smart loot"
                    )
                    _trigger_smart_loot_safe()
                    enemy_hp_percentage = 0.0
                    EnemyStateManager.reset_enemy_state()
                    _auto_target_manager.reset_search_timer()
                    # smart_loot() now handles timing and clears is_looting when done
                    if not config.is_looting:
                        _auto_target_manager.try_auto_target("enemy died (low HP)")
                    if config.skill_sequence_manager:
                        config.skill_sequence_manager.reset_sequence()
                    return
            else:
                # First reading - no smoothing
                config.enemy_hp_readings.append(raw_enemy_hp_percentage)
                enemy_hp_percentage = raw_enemy_hp_percentage
            
            if enemy_hp_percentage > 0:
                # Reset target search time when enemy is found
                _auto_target_manager.reset_search_timer()
                
                # Initialize new enemy tracking
                if config.enemy_target_time == 0:
                    EnemyStateManager.initialize_new_enemy(
                        current_time, enemy_hp_percentage
                    )
                    
                    # Reset skill sequence for new enemy
                    if config.skill_sequence_manager:
                        config.skill_sequence_manager.reset_sequence()
                    
                    # Verify mob filter after targeting
                    if mob_filter.is_active():
                        mob_filter.refresh_scan_stable(hwnd)
                        if config.current_mob_match is None:
                            print("[Mob Filter] No CV template match after targeting — retargeting")
                            EnemyStateManager.reset_enemy_state()
                            if config.skill_sequence_manager:
                                config.skill_sequence_manager.reset_sequence()
                            if MOB_VERIFICATION_DELAY > 0:
                                time.sleep(MOB_VERIFICATION_DELAY)
                            _auto_target_manager.try_auto_target("non-target mob detected")
                            return
                    
                    print(f"Enemy targeted")
        
        # Store enemy HP percentage in config for GUI to read
        config.current_enemy_hp_percentage = enemy_hp_percentage
        
    except Exception as e:
        current_time = time.time()
        if (current_time - config.last_enemy_hp_log_time >= 
                config.HP_MP_LOG_INTERVAL):
            print(f"Error capturing enemy HP bar: {e}")
            config.last_enemy_hp_log_time = current_time
        config.current_enemy_hp_percentage = 0.0
