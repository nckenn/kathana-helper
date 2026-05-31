"""
Auto-attack system for enemy detection and targeting
Detects enemy HP bar position and percentage relative to player MP bar
Includes enemy name detection using OCR and mob filtering
"""
import numpy as np
import cv2
import time
import os
import re
import difflib
import threading
import config
import input_handler
import bot_logic
import ocr_utils
import debug_utils
import debug_io
import frame_cache


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

# HSV color ranges for red detection
RED_LOWER_1 = np.array([0, 100, 100])
RED_UPPER_1 = np.array([10, 255, 255])
RED_LOWER_2 = np.array([160, 100, 100])
RED_UPPER_2 = np.array([180, 255, 255])

# Target matching
TARGET_SIMILARITY_THRESHOLD = 0.7
MOB_VERIFICATION_INTERVAL = 2.0  # Seconds between mob verifications during combat

# Name stability (anti-OCR-fluke): require the same name twice quickly before trusting it
NAME_STABLE_REQUIRED_READS = 2
NAME_STABLE_MAX_GAP_SECONDS = 0.8

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
# Text Processing Utilities
# ============================================================================

def normalize_text(text):
    """Convert to lowercase, remove special characters but preserve spaces"""
    if not text:
        return ''
    return re.sub('[^a-zA-Z\\s]', '', text.lower())


def _collapse_spaces(text: str) -> str:
    """Collapse repeated whitespace to single spaces and trim."""
    return re.sub(r'\s+', ' ', (text or '')).strip()


def contains_complete_word(target, detected):
    """Returns True if target matches EXACTLY with detected (same words, same order)"""
    target = target.lower().strip()
    detected = detected.lower().strip()
    detected_clean = re.sub('[^a-zA-Z0-9\\s]', '', detected)
    target_words = target.split()
    detected_words = detected_clean.split()
    if len(target_words) != len(detected_words):
        return False
    for i in range(len(target_words)):
        if target_words[i] != detected_words[i]:
            return False
    return True


def calculate_similarity(a, b):
    """Returns similarity between two strings (0-1) using SequenceMatcher"""
    return difflib.SequenceMatcher(None, a, b).ratio()


# ============================================================================
# OCR Functions
# ============================================================================

def extract_enemy_name_easyocr(name_area):
    """
    Extract enemy name using EasyOCR (better performance and speed)
    Uses white character filtering for better detection
    
    Args:
        name_area: Image area containing enemy name (BGR format)
        
    Returns:
        tuple: (name: str, original_text: str) or ('', '') if not found
    """
    if not ocr_utils.initialize_ocr_reader():
        return ('', '')
    
    if config.ocr_reader is None:
        return ('', '')
    
    try:
        # Convert to HSV for white detection
        hsv = cv2.cvtColor(name_area, cv2.COLOR_BGR2HSV)
        lower_white = np.array([0, 0, 180])
        upper_white = np.array([180, 50, 255])
        mask_white = cv2.inRange(hsv, lower_white, upper_white)
        white_chars = cv2.bitwise_and(name_area, name_area, mask=mask_white)
        
        # Morphological operations to clean up the mask
        kernel_close = np.ones((2, 2), np.uint8)
        kernel_open = np.ones((1, 1), np.uint8)
        mask_white = cv2.morphologyEx(mask_white, cv2.MORPH_CLOSE, kernel_close)
        mask_white = cv2.morphologyEx(mask_white, cv2.MORPH_OPEN, kernel_open)
        
        # Convert to RGB for EasyOCR
        img_rgb = cv2.cvtColor(white_chars, cv2.COLOR_BGR2RGB)
        # Low-RAM safety: cap image size (mostly a no-op here, but keeps behavior consistent)
        img_rgb = ocr_utils._downscale_for_ocr(img_rgb)
        
        # Count white pixels for debugging
        white_pixels = cv2.countNonZero(mask_white)
        total_pixels = mask_white.shape[0] * mask_white.shape[1]
        white_percentage = white_pixels / total_pixels * 100
        
        # Try OCR with white-filtered image first
        try:
            results = config.ocr_reader.readtext(
                img_rgb,
                paragraph=False,
                detail=1,
                batch_size=int(getattr(config, 'ocr_batch_size', 1) or 1),
                contrast_ths=0.1,
                adjust_contrast=0.3,
                text_threshold=0.5,
                link_threshold=0.3,
                low_text=0.3,
                canvas_size=1280,
                mag_ratio=1.0
            )
        except Exception as e:
            # If OCR throws a memory error, retry with downscaled image
            msg = str(e).lower()
            if 'out of memory' in msg or 'memory' in msg:
                img_rgb_retry = ocr_utils._downscale_for_ocr(img_rgb)
                results = config.ocr_reader.readtext(
                    img_rgb_retry,
                    paragraph=False,
                    detail=1,
                    batch_size=1,
                    contrast_ths=0.1,
                    adjust_contrast=0.3,
                    text_threshold=0.5,
                    link_threshold=0.3,
                    low_text=0.3,
                    canvas_size=1280,
                    mag_ratio=1.0
                )
            else:
                raise
        
        if results:
            # Filter results to only letters
            filtered_results = []
            for result in results:
                text = result[1].strip()
                text_letters_only = re.sub('[^a-zA-Z\\s]', '', text)
                if text_letters_only and len(text_letters_only.strip()) >= 1:
                    filtered_results.append((result[0], text_letters_only.strip(), result[2]))
            
            if filtered_results:
                # Find best result (longest word count, then longest text)
                best_result = max(filtered_results, key=lambda x: len(x[1].split()))
                if len([r for r in filtered_results if len(r[1].split()) == len(best_result[1].split())]) > 1:
                    best_result = max(filtered_results, key=lambda x: len(x[1]))
            else:
                best_result = max(results, key=lambda x: len(x[1]))
            
            name = best_result[1].strip()
            original_text = best_result[1]
            
            if debug_io.should_save_debug_images():
                debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'debug')
                os.makedirs(debug_dir, exist_ok=True)
                debug_io.save_cv2_image(os.path.join(debug_dir, 'enemy_name_easyocr_input.png'), name_area)
                debug_io.save_cv2_image(os.path.join(debug_dir, 'enemy_name_white_chars.png'), white_chars)
                debug_io.save_cv2_image(os.path.join(debug_dir, 'enemy_name_mask.png'), mask_white)
                debug_img = name_area.copy()
                cv2.putText(debug_img, f'OCR Detected: {name}', (2, 13), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1, cv2.LINE_AA)
                cv2.putText(debug_img, f'Original Text: {original_text}', (2, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 0), 1, cv2.LINE_AA)
                cv2.putText(debug_img, f'Confidence: {best_result[2]:.2f}', (2, 37), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 0), 1, cv2.LINE_AA)
                debug_io.save_cv2_image(os.path.join(debug_dir, 'enemy_name_ocr_detected.png'), debug_img)
            
            return (name, original_text)
        else:
            # Try with original image if filtered version fails
            img_rgb_original = cv2.cvtColor(name_area, cv2.COLOR_BGR2RGB)
            img_rgb_original = ocr_utils._downscale_for_ocr(img_rgb_original)
            try:
                results_original = config.ocr_reader.readtext(
                    img_rgb_original,
                    paragraph=False,
                    detail=1,
                    batch_size=int(getattr(config, 'ocr_batch_size', 1) or 1),
                )
            except Exception as e:
                msg = str(e).lower()
                if 'out of memory' in msg or 'memory' in msg:
                    img_rgb_original_retry = ocr_utils._downscale_for_ocr(img_rgb_original)
                    results_original = config.ocr_reader.readtext(
                        img_rgb_original_retry,
                        paragraph=False,
                        detail=1,
                        batch_size=1,
                    )
                else:
                    raise
            
            if results_original:
                best_result = max(results_original, key=lambda x: len(x[1]))
                text = best_result[1]
                confidence = best_result[2]
                text_letters_only = re.sub('[^a-zA-Z\\s]', '', text)
                name = text_letters_only.strip()
                
                if debug_io.should_save_debug_images():
                    debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'debug')
                    os.makedirs(debug_dir, exist_ok=True)
                    debug_img = name_area.copy()
                    cv2.putText(debug_img, f'OCR Detected: {name}', (2, 13), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1, cv2.LINE_AA)
                    cv2.putText(debug_img, f'Original Text: {text}', (2, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 0), 1, cv2.LINE_AA)
                    cv2.putText(debug_img, f'Confidence: {confidence:.2f}', (2, 37), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 0), 1, cv2.LINE_AA)
                    cv2.putText(debug_img, 'No Filters', (2, 49), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 0, 255), 1, cv2.LINE_AA)
                    debug_io.save_cv2_image(os.path.join(debug_dir, 'enemy_name_ocr_detected.png'), debug_img)
                
                return (name, text)
            else:
                if debug_io.should_save_debug_images():
                    debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'debug')
                    os.makedirs(debug_dir, exist_ok=True)
                    debug_img = name_area.copy()
                    cv2.putText(debug_img, 'OCR Detected: NONE', (2, 13), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1, cv2.LINE_AA)
                    cv2.putText(debug_img, 'Original Text: N/A', (2, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1, cv2.LINE_AA)
                    cv2.putText(debug_img, 'Confidence: 0.00', (2, 37), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1, cv2.LINE_AA)
                    cv2.putText(debug_img, 'No Detection', (2, 49), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1, cv2.LINE_AA)
                    debug_io.save_cv2_image(os.path.join(debug_dir, 'enemy_name_ocr_detected.png'), debug_img)
                return ('', '')

    except Exception as e:
        print(f'[Enemy Name OCR] Error: {str(e)}')
        if debug_io.should_save_debug_images():
            debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'debug')
            os.makedirs(debug_dir, exist_ok=True)
            debug_img = name_area.copy()
            cv2.putText(debug_img, 'OCR Error', (2, 13), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1, cv2.LINE_AA)
            cv2.putText(debug_img, f'Error: {str(e)[:30]}', (2, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 255), 1, cv2.LINE_AA)
            cv2.putText(debug_img, 'Confidence: N/A', (2, 37), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1, cv2.LINE_AA)
            debug_io.save_cv2_image(os.path.join(debug_dir, 'enemy_name_ocr_detected.png'), debug_img)
        return ('', '')
    
    return ('', '')


# ============================================================================
# Mob Filtering Functions
# ============================================================================

def should_target_current_mob():
    """Check if current mob should be targeted (opposite of skip - only attack if in target list)"""
    if not config.current_target_mob:
        return False
    
    # If no target list, attack all mobs
    if not config.mob_target_list:
        return True
    
    # Only attack if mob is in target list - STRICT MATCHING
    detected_normalized = normalize_text(config.current_target_mob)
    detected_words = detected_normalized.split()
    
    for target_mob in config.mob_target_list:
        target_normalized = normalize_text(target_mob)
        target_words = target_normalized.split()
        
        # STRICT: Only match if exact word-by-word match (same number of words, same words in order)
        if contains_complete_word(target_mob, config.current_target_mob):
            return True
        
        # STRICT: Additional check - if target has more words than detected, don't match
        # This prevents "Ananga" from matching "Ananga Dvant"
        if len(target_words) > len(detected_words):
            continue
        
        # STRICT: Only allow similarity match if lengths are very close (<= 1 char) and similarity is very high (>= 0.95)
        # This handles minor OCR errors (e.g., "Ananga Dvanta" vs "Ananga Dvant") but prevents partial matches
        if len(target_words) == len(detected_words):
            length_diff = abs(len(detected_normalized) - len(target_normalized))
            if length_diff <= 1:
                similarity = calculate_similarity(detected_normalized, target_normalized)
                if similarity >= 0.95:
                    return True
    
    return False


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
    
    if not config.calibrator or config.calibrator.mp_position is None:
        return {'detected': False, 'name': None, 'should_target': False, 'needs_retarget': False}
    
    # Minimal delay to allow mob name to appear after targeting (optimized for speed)
    if delay > 0:
        time.sleep(delay)
    
    hwnd = config.connected_window.handle
    detected_mob = None
    
    mob_filter_enabled = config.mob_detection_enabled and bool(config.mob_target_list)

    # If filtering is enabled, validate using stable OCR + target matching to avoid jitter retarget loops.
    if mob_filter_enabled:
        targets = config.mob_target_list
        result = detect_enemy_for_auto_attack(hwnd, targets=targets, read_name=True)
        detected_mob = result.get('name')

        if (not result.get('name_stable')) and retry_delay > 0:
            time.sleep(retry_delay)
            result = detect_enemy_for_auto_attack(hwnd, targets=targets, read_name=True)
            detected_mob = result.get('name')

        # Only decide retarget when we have a stable name and an explicit non-match.
        stable = bool(result.get('name_stable'))
        matches_target = result.get('matches_target')
        should_target = bool(matches_target) if (stable and matches_target is not None) else False
        needs_retarget = stable and (matches_target is False)

        if stable and detected_mob:
            config.current_target_mob = detected_mob
            config.current_enemy_name = detected_mob
            config.last_mob_detection_time = time.time()
        elif not stable:
            # Don't update mob name on unstable reads.
            detected_mob = None

        return {
            'detected': bool(detected_mob),
            'name': detected_mob,
            'should_target': should_target,
            'needs_retarget': needs_retarget
        }

    # No filtering: just detect mob name using calibration-based detection
    result = detect_enemy_for_auto_attack(hwnd, targets=None, read_name=True)
    detected_mob = result.get('name')

    if not detected_mob and config.mob_detection_enabled and retry_delay > 0:
        time.sleep(retry_delay)
        result = detect_enemy_for_auto_attack(hwnd, targets=None, read_name=True)
        detected_mob = result.get('name')
    
    # Update config with detected mob name
    if detected_mob:
        config.current_target_mob = detected_mob
        config.current_enemy_name = detected_mob
        config.last_mob_detection_time = time.time()
    else:
        config.current_enemy_name = None
    
    # Check if mob should be targeted
    should_target = should_target_current_mob() if detected_mob else False
    needs_retarget = detected_mob and config.mob_detection_enabled and config.mob_target_list and not should_target
    
    return {
        'detected': bool(detected_mob),
        'name': detected_mob,
        'should_target': should_target,
        'needs_retarget': needs_retarget
    }


# ============================================================================
# Helper Classes
# ============================================================================

class EnemyDetectionResult:
    """Container for enemy detection results"""
    def __init__(self, found=False, hp=0.0, position=None, name=None,
                 ocr_text=None, avara_detected=False, screen=None,
                 name_stable=None, matches_target=None, name_checked=None):
        self.found = found
        self.hp = hp
        self.position = position
        self.name = name
        self.ocr_text = ocr_text
        self.avara_detected = avara_detected
        self.screen = screen
        self.name_stable = name_stable
        self.matches_target = matches_target
        self.name_checked = name_checked

    def to_dict(self):
        """Convert to dictionary for backward compatibility"""
        result = {
            'found': self.found,
            'hp': self.hp,
            'position': self.position,
            'name': self.name,
            'ocr_text': self.ocr_text,
            'avara_detected': self.avara_detected,
        }
        if self.name_stable is not None:
            result['name_stable'] = self.name_stable
        if self.matches_target is not None:
            result['matches_target'] = self.matches_target
        if self.name_checked is not None:
            result['name_checked'] = self.name_checked
        if self.screen is not None:
            result['screen'] = self.screen
        return result


def _enemy_detection_needs_early_ocr(targets):
    """Legacy: whether we must OCR even without a confirmed HP bar."""
    # Keeping for compatibility; we now prefer HP-first in Low CPU mode whenever possible.
    if targets:
        return True
    if getattr(config, 'mob_avoid_list', None):
        return True
    return False


def _use_hp_first_detection_order(targets):
    """Low CPU: detect HP bar first; OCR only when a bar is found."""
    # Even when filtering is enabled, OCR-without-bar is wasted work. In Low CPU mode,
    # only OCR after we've confirmed an HP bar is present.
    return bool(config.low_cpu_mode)


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
        hsv = cv2.cvtColor(search_area, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv, RED_LOWER_1, RED_UPPER_1)
        mask2 = cv2.inRange(hsv, RED_LOWER_2, RED_UPPER_2)
        return cv2.bitwise_or(mask1, mask2)
    
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

    def save_target_comparison_debug(self, search_area, detected_name,
                                     targets, similarities):
        """Save debug image with target comparison"""
        if not debug_io.should_save_debug_images():
            return
        debug_img = search_area.copy()
        cv2.putText(
            debug_img, f'OCR: {detected_name}', (2, 13),
            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1, cv2.LINE_AA
        )
        for idx, target in enumerate(targets):
            y_pos = 25 + 12 * idx
            cv2.putText(
                debug_img, f'Target{idx + 1}: {target}', (2, y_pos),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 0, 0), 1, cv2.LINE_AA
            )
            cv2.putText(
                debug_img, f'Sim{idx + 1}: {similarities[idx]:.2f}', 
                (2, y_pos + 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 0, 0), 1, cv2.LINE_AA
            )
        debug_io.save_cv2_image(
            os.path.join(self.debug_dir, 'enemy_hp_search_area_ocr_targets.png'),
            debug_img)


class EnemyNameValidator:
    """Handles enemy name validation and target matching"""

    _stable_last_name = ''
    _stable_last_time = 0.0
    _stable_count = 0

    @staticmethod
    def update_stability(detected_name: str, now: float) -> bool:
        """
        Track recent detected names and return True when the same normalized name
        has been seen `NAME_STABLE_REQUIRED_READS` times within `NAME_STABLE_MAX_GAP_SECONDS`.
        """
        name_norm = _collapse_spaces(normalize_text(detected_name))
        if not name_norm:
            EnemyNameValidator._stable_last_name = ''
            EnemyNameValidator._stable_last_time = now
            EnemyNameValidator._stable_count = 0
            return False

        if name_norm != EnemyNameValidator._stable_last_name or (now - EnemyNameValidator._stable_last_time) > NAME_STABLE_MAX_GAP_SECONDS:
            EnemyNameValidator._stable_last_name = name_norm
            EnemyNameValidator._stable_count = 1
        else:
            EnemyNameValidator._stable_count += 1

        EnemyNameValidator._stable_last_time = now
        return EnemyNameValidator._stable_count >= NAME_STABLE_REQUIRED_READS

    @staticmethod
    def is_name_stable(detected_name: str, now: float) -> bool:
        """Convenience wrapper to check stability without exposing internals."""
        return EnemyNameValidator.update_stability(detected_name, now)
    
    @staticmethod
    def check_avoid_mob_detection(detected_name):
        """Check if detected name matches any mob in the avoid list"""
        if not detected_name or not config.mob_avoid_list:
            return False
        
        detected_name_normalized = normalize_text(detected_name)
        
        # Check each mob in avoid list
        for avoid_mob in config.mob_avoid_list:
            avoid_mob_normalized = normalize_text(avoid_mob)
            
            # Check for exact word match (e.g., "Avara Kara" matches "Avara Kara")
            if contains_complete_word(avoid_mob, detected_name):
                return True
            
            # Check if avoid mob name is contained in detected name (normalized)
            if avoid_mob_normalized in detected_name_normalized:
                return True
            
            # Check if detected name is contained in avoid mob name (for partial matches)
            if detected_name_normalized in avoid_mob_normalized:
                return True
        
        return False
    
    @staticmethod
    def match_targets(detected_name, targets):
        """Check if detected name matches any target in the list - STRICT MATCHING"""
        if not detected_name or not targets:
            return False, []
        
        detected_name_normalized = normalize_text(detected_name)
        detected_words = detected_name_normalized.split()
        similarities = []
        
        for target in targets:
            target_normalized = normalize_text(target)
            target_words = target_normalized.split()
            
            # STRICT: Exact word-by-word match
            if contains_complete_word(target, detected_name):
                similarity = 1.0
            else:
                # STRICT: If target has more words than detected, don't match
                # This prevents "Ananga" from matching "Ananga Dvant"
                if len(target_words) > len(detected_words):
                    similarity = 0
                # STRICT: Only allow similarity match if same word count, very close length (<= 1 char), and high similarity (>= 0.95)
                elif len(target_words) == len(detected_words):
                    length_diff = abs(len(detected_name_normalized) - len(target_normalized))
                    if length_diff <= 1:
                        similarity = calculate_similarity(
                            detected_name_normalized, target_normalized
                        ) if target_normalized else 0
                        # Require very high similarity for strict matching
                        if similarity < 0.95:
                            similarity = 0
                    else:
                        similarity = 0
                else:
                    similarity = 0
            similarities.append(similarity)
        
        max_similarity = max(similarities) if similarities else 0
        # Use higher threshold for strict matching
        return max_similarity >= 0.95, similarities


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

def detect_enemy_for_auto_attack(hwnd, targets=None, screen=None, read_name: bool = True):
    """
    Detect enemy HP percentage and name for auto-attack using calibration-based method
    Uses MP position as reference to find enemy HP bar
    Only considers valid if name matches targets (if targets list is provided)

    Args:
        hwnd: Window handle
        targets: Optional list of target mob names to attack (if None, attack all)
        screen: Optional pre-captured frame (uses frame cache if omitted)

    Returns:
        dict: detection fields plus optional 'screen' for reuse in same tick
    """
    if not config.calibrator or config.calibrator.mp_position is None:
        print('No MP position memorized')
        return EnemyDetectionResult().to_dict()

    try:
        mp_x, mp_y = config.calibrator.mp_position
        debug_utils.debug_print(f'MP position (memorized): ({mp_x}, {mp_y})', 'AutoAttack')

        if screen is None:
            screen = frame_cache.get_frame(hwnd, config.calibrator)
        if screen is None:
            return EnemyDetectionResult().to_dict()

        detector = EnemyHpBarDetector()
        search_y = mp_y + SEARCH_AREA_OFFSET_Y
        search_x = mp_x + SEARCH_AREA_OFFSET_X
        search_area = frame_cache.crop_rect(
            screen,
            search_x, search_y,
            search_x + SEARCH_AREA_WIDTH, search_y + SEARCH_AREA_HEIGHT,
            frame_cache.get_origin(),
        )

        if search_area.size == 0 or search_area.shape[0] < NAME_AREA_HEIGHT:
            return EnemyDetectionResult(screen=screen).to_dict()

        name_area = search_area[0:NAME_AREA_HEIGHT, :]
        if debug_io.should_save_debug_images():
            debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'debug')
            os.makedirs(debug_dir, exist_ok=True)
            debug_io.save_cv2_image(os.path.join(debug_dir, 'name_area_debug.png'), name_area)

        hsv = cv2.cvtColor(search_area, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv, RED_LOWER_1, RED_UPPER_1)
        mask2 = cv2.inRange(hsv, RED_LOWER_2, RED_UPPER_2)
        mask = cv2.bitwise_or(mask1, mask2)

        if debug_io.should_save_debug_images():
            debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'debug')
            os.makedirs(debug_dir, exist_ok=True)
            debug_io.save_cv2_image(os.path.join(debug_dir, 'mask_red.png'), mask)
            debug_io.save_cv2_image(os.path.join(debug_dir, 'search_area.png'), search_area)
        detector.save_debug_images(search_area, mask, name_area)

        best_y, best_width, best_first, best_last = detector.find_hp_bar(mask, search_area)
        bar_found = (
            best_y is not None and best_width > 0 and best_width >= MIN_HP_BAR_WIDTH
        )

        hp_first = _use_hp_first_detection_order(targets)
        detected_name = ''
        ocr_text = ''

        if read_name:
            if hp_first:
                if bar_found:
                    detected_name, ocr_text = extract_enemy_name_easyocr(name_area)
            else:
                detected_name, ocr_text = extract_enemy_name_easyocr(name_area)

        now = time.time()
        matches_target = None
        name_is_stable = None
        name_checked = False

        # Only apply stability + filtering when we actually read a name this tick.
        if read_name:
            name_checked = True
            name_is_stable = EnemyNameValidator.update_stability(detected_name, now)

            # Avoid-list acts like "never attack/keep" for these names.
            if EnemyNameValidator.check_avoid_mob_detection(detected_name):
                print(f'[TARGET] Enemy detected \'{detected_name}\' is in avoid list. Skipping attack.')
                matches_target = False

            # If target filtering is enabled, only decide match/non-match once the name is stable.
            # While unstable, keep matches_target as None to avoid retarget loops.
            # (We still return found=True when bar_found so combat logic continues.)
            if targets:
                if not name_is_stable:
                    matches_target = None
                elif detected_name:
                    matches, similarities = EnemyNameValidator.match_targets(detected_name, targets)
                    detector.save_target_comparison_debug(
                        search_area, detected_name, targets, similarities)
                    matches_target = bool(matches)
                    if not matches_target:
                        max_similarity = max(similarities) if similarities else 0
                        detected_name_normalized = normalize_text(detected_name)
                        print(
                            f'[TARGET] Detected name \'{detected_name_normalized}\' '
                            f'does not match (similarity {max_similarity:.2f}) with '
                            f'targets {targets}. Ignoring enemy.'
                        )

        if bar_found:
            enemy_x = mp_x - 1 + best_first
            enemy_y = search_y + best_y + HP_BAR_CENTER_OFFSET
            position = (enemy_x, enemy_y)
            hp_percentage = float(max(0, min(100, best_width / SEARCH_AREA_WIDTH * 100)))
            debug_utils.debug_print(
                f'Enemy at ({enemy_x}, {enemy_y}) HP {hp_percentage:.1f}%',
                'AutoAttack',
            )
            bar_img = search_area[
                best_y + HP_BAR_CENTER_OFFSET:best_y + HP_BAR_CENTER_OFFSET + HP_BAR_HEIGHT,
                best_first:best_last + 1,
            ]
            detector.save_debug_images(
                search_area, mask, name_area, bar_img, enemy_x, enemy_y)
            return EnemyDetectionResult(
                found=True,
                hp=hp_percentage,
                position=position,
                name=detected_name,
                ocr_text=ocr_text,
                screen=screen,
                name_stable=name_is_stable,
                matches_target=matches_target,
                name_checked=name_checked,
            ).to_dict()

        if detected_name:
            debug_utils.debug_print(
                f'Name \'{detected_name}\' but no HP bar — may be dead',
                'AutoAttack',
            )
        else:
            debug_utils.debug_print('No red HP bar detected', 'AutoAttack')
        return EnemyDetectionResult(
            found=False,
            name=detected_name,
            ocr_text=ocr_text,
            screen=screen,
        ).to_dict()

    except Exception as e:
        print(f"[Enemy HP Detection] Error: {e}")
        return EnemyDetectionResult().to_dict()


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
    """
    Assist mode: press configured assist hotkey on interval.
    Normal mode is unused (assist_only must be enabled).
    """
    if not config.assist_only_enabled:
        return

    if not config.connected_window:
        return

    assist_key = (getattr(config, 'assist_key', None) or '').strip()
    if not assist_key:
        return

    interval = getattr(config, "assist_click_interval_seconds", 1.0)
    current_time = time.time()
    if not hasattr(check_assist_key, 'last_click_time'):
        check_assist_key.last_click_time = 0

    if current_time - check_assist_key.last_click_time < interval:
        return

    try:
        input_handler.send_input(assist_key)
        check_assist_key.last_click_time = current_time
        debug_utils.debug_print(f'Assist key pressed: {assist_key}', 'AssistOnly')
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
        
        # Check if mob filter is enabled
        mob_filter_enabled = config.mob_detection_enabled and config.mob_target_list
        
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
                f"(not in target list, retry {recursion_depth + 1}/{max_recursion}){context_str}"
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
    
    # Clear looting flag after looting duration has passed
    if config.is_looting:
        if current_time - config.looting_start_time >= config.LOOTING_DURATION:
            config.is_looting = False
    
    # Require calibration to be available
    if not config.calibrator or config.calibrator.mp_position is None:
        config.current_enemy_hp_percentage = 0.0
        return
    
    try:
        hwnd = config.connected_window.handle
        enemy_hp_percentage = 0.0
        
        # Use calibration-based detection. OCR is expensive — only do it when needed.
        mob_filter_enabled = config.mob_detection_enabled and bool(config.mob_target_list)
        targets = config.mob_target_list if mob_filter_enabled else None

        # Only OCR name when:
        # - mob filtering is enabled AND
        #   - we don't have a recent stable name, or
        #   - it's time for periodic verification
        read_name = True
        if mob_filter_enabled:
            if not hasattr(check_auto_attack, "_last_name_ocr_time"):
                check_auto_attack._last_name_ocr_time = 0.0
            last_ocr = check_auto_attack._last_name_ocr_time
            have_recent_name = bool(config.current_target_mob) and (current_time - config.last_mob_detection_time) < 1.2
            needs_periodic = (config.enemy_target_time > 0) and (current_time - last_ocr) >= MOB_VERIFICATION_INTERVAL
            read_name = (not have_recent_name) or needs_periodic

        result = detect_enemy_for_auto_attack(hwnd, targets=targets, read_name=read_name)
        if read_name:
            check_auto_attack._last_name_ocr_time = current_time
        
        if result['found']:
            raw_enemy_hp_percentage = result['hp']
            has_red_bar = True
            config.last_enemy_seen_time = current_time
            
            # Update current target mob with detected name
            if result.get('name') and result.get('name_stable', True):
                config.current_target_mob = result['name']
                config.last_mob_detection_time = current_time
        else:
            has_red_bar = False
            raw_enemy_hp_percentage = 0.0
        
        # Handle case when no enemy is found
        if not has_red_bar:
            # Check if we had an enemy recently (multiple conditions to catch all cases)
            # Also check if we detected a name but no HP bar (enemy might be dead but name still visible briefly)
            had_enemy = (
                len(config.enemy_hp_readings) > 0 or 
                config.enemy_target_time > 0 or
                config.current_target_mob is not None or
                config.current_enemy_name is not None
            )
            
            # Additional check: if we detected a name but no HP bar, enemy is likely dead
            # This handles cases where the name might still be visible but HP bar is gone
            name_detected_but_no_bar = (
                result.get('name') and 
                not result.get('found') and
                result.get('hp', 0) == 0
            )
            
            if had_enemy or name_detected_but_no_bar:
                # Enemy was killed - trigger smart loot first
                # This handles the case where enemy bar disappears (enemy died)
                reason = "name detected but no HP bar" if name_detected_but_no_bar else "enemy bar disappeared"
                print(
                    f"[Auto Attack] Enemy disappeared ({reason}) - triggering smart loot "
                    f"(had_enemy: readings={len(config.enemy_hp_readings)}, "
                    f"target_time={config.enemy_target_time}, mob={config.current_target_mob})"
                )
                bot_logic.smart_loot()
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
            # If mob filter is enabled and the detected mob does not match the list, retarget without
            # treating this as "enemy disappeared" (prevents loot/stop-fighting behavior).
            mob_filter_enabled = config.mob_detection_enabled and bool(config.mob_target_list)
            if mob_filter_enabled and result.get('name_checked') and result.get('matches_target') is False:
                detected_mob = result.get('name')
                if detected_mob:
                    print(f"[Mob Filter] Non-target mob detected: {detected_mob} (retargeting)")
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
                    bot_logic.smart_loot()
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
                    if should_use_skills(enemy_hp_percentage):
                        try:
                            skill_screen = result.get('screen')
                            if skill_screen is None:
                                skill_screen = frame_cache.get_frame(hwnd, config.calibrator)
                            if skill_screen is not None:
                                config.skill_sequence_manager.execute_skill_sequence(
                                    hwnd, skill_screen, config.area_skills,
                                    enemy_found=True, run_active=config.bot_running
                                )
                        except Exception as e:
                            print(f"[AutoAttack] Error executing skill sequence: {e}")
                
                # Periodic mob verification during combat
                if (config.mob_detection_enabled and config.mob_target_list and 
                    config.enemy_target_time > 0):
                    if (current_time - config.last_mob_verification_time > 
                            MOB_VERIFICATION_INTERVAL):
                        config.last_mob_verification_time = current_time
                        detected_mob = result.get('name')
                        if detected_mob:
                            config.current_target_mob = detected_mob
                            config.current_enemy_name = detected_mob
                            config.last_mob_detection_time = current_time
                            if not should_target_current_mob():
                                print(
                                    f"[Mob Filter] Detected non-target mob during "
                                    f"combat: {detected_mob} - retargeting"
                                )
                                EnemyStateManager.reset_enemy_state()
                                # Reset skill sequence when changing target
                                if config.skill_sequence_manager:
                                    config.skill_sequence_manager.reset_sequence()
                                # Minimal delay before retargeting (optimized for speed)
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
                        bot_logic.smart_loot()
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
                    bot_logic.smart_loot()
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
                    
                    # Verify mob detection after targeting
                    if config.mob_detection_enabled:
                        detected_mob = result.get('name')
                        if detected_mob:
                            config.current_target_mob = detected_mob
                            config.current_enemy_name = detected_mob
                            config.last_mob_detection_time = current_time
                            if (config.mob_target_list and 
                                not should_target_current_mob()):
                                print(
                                    f"[Mob Filter] Detected non-target mob after "
                                    f"targeting: {detected_mob} - retargeting"
                                )
                                EnemyStateManager.reset_enemy_state()
                                # Reset skill sequence when retargeting
                                if config.skill_sequence_manager:
                                    config.skill_sequence_manager.reset_sequence()
                                # Minimal delay before retargeting (optimized for speed)
                                if MOB_VERIFICATION_DELAY > 0:
                                    time.sleep(MOB_VERIFICATION_DELAY)
                                _auto_target_manager.try_auto_target(
                                    "non-target mob detected"
                                )
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
