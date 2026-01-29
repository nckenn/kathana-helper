"""
Auto repair functionality - monitors system messages for item break warnings
Triggers repair when 'is about to break' warning is detected 3 times
"""
import time
import hashlib
import os
import config
import ocr_utils
import input_handler
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print('[CV2] OpenCV not available. Install with: pip install opencv-python')


# ============================================================================
# Constants
# ============================================================================

# Timing constants
CALIBRATION_WARN_INTERVAL = 30.0  # Seconds between calibration warnings
DETECTION_LOG_INTERVAL = 2.0  # Seconds between detection logs
COOLDOWN_LOG_INTERVAL = 5.0  # Seconds between cooldown logs


# ============================================================================
# Helper Classes
# ============================================================================

class BreakWarningTracker:
    """Tracks break warning detections"""
    
    def __init__(self):
        self.detection_timestamps = []
    
    def add_detection(self, current_time):
        """Add a new detection timestamp"""
        self.detection_timestamps.append(current_time)
    
    def get_count(self):
        """Get current detection count"""
        return len(self.detection_timestamps)
    
    def clear(self):
        """Clear all detections"""
        self.detection_timestamps.clear()
    
    def should_trigger_repair(self):
        """Check if repair should be triggered"""
        return self.get_count() >= config.BREAK_WARNING_TRIGGER_COUNT


class RepairExecutor:
    """Handles repair execution"""
    
    @staticmethod
    def execute_repair(current_time):
        """Execute repair action"""
        input_handler.send_input(config.repair_key)
        config.last_repair_time = current_time
        print(f"[Auto Repair] REPAIR TRIGGERED ({config.repair_key.upper()})")
    
    @staticmethod
    def is_on_cooldown(current_time):
        """Check if repair is on cooldown"""
        return (current_time - config.last_repair_time) < config.REPAIR_COOLDOWN
    
    @staticmethod
    def get_remaining_cooldown(current_time):
        """Get remaining cooldown time"""
        elapsed = current_time - config.last_repair_time
        return max(0.0, config.REPAIR_COOLDOWN - elapsed)


class RepairStateManager:
    """Manages repair state and logging"""
    
    def __init__(self):
        self.last_warn_time = 0
        self.last_log_time = 0
        self.last_cooldown_log_time = 0
    
    def should_warn_calibration(self, current_time):
        """Check if calibration warning should be shown"""
        if current_time - self.last_warn_time > CALIBRATION_WARN_INTERVAL:
            self.last_warn_time = current_time
            return True
        return False
    
    def should_log_detection(self, current_time):
        """Check if detection should be logged"""
        if current_time - self.last_log_time > DETECTION_LOG_INTERVAL:
            self.last_log_time = current_time
            return True
        return False
    
    def should_log_cooldown(self, current_time):
        """Check if cooldown should be logged"""
        if current_time - self.last_cooldown_log_time > COOLDOWN_LOG_INTERVAL:
            self.last_cooldown_log_time = current_time
            return True
        return False


class CalibrationValidator:
    """Validates calibration settings"""
    
    @staticmethod
    def is_calibrated():
        """Check if system message area is calibrated"""
        return (config.system_message_area.get('width', 0) > 0 and 
                config.system_message_area.get('height', 0) > 0)


class ImageChangeDetector:
    """Detects changes in system message area to avoid unnecessary OCR"""
    
    def __init__(self):
        self.last_image_hash = None
        self.last_ocr_time = 0
        self.min_ocr_interval = 2.0  # Minimum time between OCR calls even if image changes (increased to reduce load)
        self.last_message_area = None  # Store last extracted area for debug
        self.last_empty_ocr_time = 0  # Track when we last got empty OCR result
        self.empty_ocr_cooldown = 3600.0  # Skip OCR for 1 hour after getting empty result
    
    def extract_message_area_from_screen(self, screen):
        """Extract system message area from full screen (follows pattern from buffs/skill sequence)"""
        if screen is None:
            return None
        
        try:
            x = config.system_message_area['x']
            y = config.system_message_area['y']
            width = config.system_message_area['width']
            height = config.system_message_area['height']
            
            if width <= 0 or height <= 0:
                return None
            
            # Calculate bounds (center-based like buffs)
            center_x = x
            center_y = y
            half_width = width // 2
            half_height = height // 2
            
            left = center_x - half_width
            top = center_y - half_height
            right = center_x + half_width
            bottom = center_y + half_height
            
            # Extract region from screen (like area_skills extraction)
            h, w = screen.shape[:2]
            if (left >= 0 and top >= 0 and right <= w and bottom <= h):
                message_area = screen[top:bottom, left:right]
                return message_area
            
            return None
        except Exception:
            return None
    
    def calculate_image_hash(self, img_array):
        """Calculate a hash of the image array for change detection"""
        if img_array is None:
            return None
        try:
            # Convert numpy array to bytes and hash (fast comparison)
            img_bytes = img_array.tobytes()
            return hashlib.md5(img_bytes).hexdigest()
        except Exception:
            return None
    
    def has_image_changed(self, screen, current_time):
        """Check if the system message area image has changed (follows pattern from buffs)"""
        # Enforce minimum interval between OCR calls
        if current_time - self.last_ocr_time < self.min_ocr_interval:
            return False
        
        # Skip OCR if we recently got empty result (avoid repeated OCR on empty messages)
        if current_time - self.last_empty_ocr_time < self.empty_ocr_cooldown:
            return False
        
        # Extract message area from screen (like buffs extract area_skills)
        message_area = self.extract_message_area_from_screen(screen)
        if message_area is None:
            return False
        
        # Store for debug saving
        self.last_message_area = message_area.copy()
        
        # Calculate hash
        current_hash = self.calculate_image_hash(message_area)
        if current_hash is None:
            return False
        
        # Check if hash changed
        if current_hash != self.last_image_hash:
            self.last_image_hash = current_hash
            self.last_ocr_time = current_time
            return True
        
        return False
    
    def mark_empty_ocr(self, current_time):
        """Mark that we got an empty OCR result to avoid repeated checks"""
        self.last_empty_ocr_time = current_time
    
    def save_debug_image(self):
        """Save debug image of system message area (like buffs save debug images)"""
        if not CV2_AVAILABLE or self.last_message_area is None:
            return
        
        try:
            debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'debug')
            if not os.path.exists(debug_dir):
                os.makedirs(debug_dir)
            cv2.imwrite(os.path.join(debug_dir, 'system_message_area.png'), self.last_message_area)
        except Exception as e:
            print(f"[Auto Repair] Error saving debug image: {e}")


# ============================================================================
# Main Function
# ============================================================================

# Global instances
_break_warning_tracker = BreakWarningTracker()
_repair_state_manager = RepairStateManager()
_image_change_detector = ImageChangeDetector()


def get_repair_count():
    """Get current break warning detection count for UI display"""
    return _break_warning_tracker.get_count()


def get_repair_trigger_count():
    """Get the trigger count required for repair"""
    return config.BREAK_WARNING_TRIGGER_COUNT


def check_auto_repair():
    """
    Check system messages for 'is about to break' warning and trigger repair 
    if detected 3 times. Optimized to minimize delays.
    """
    # Early exit if disabled
    if not config.auto_repair_enabled:
        return
    
    # Early exit if auto attack is disabled (no need to check)
    if not config.auto_attack_enabled:
        _break_warning_tracker.clear()
        return
    
    # Check calibration
    if not CalibrationValidator.is_calibrated():
        current_time = time.time()
        if _repair_state_manager.should_warn_calibration(current_time):
            print(
                "[Auto Repair] System message area not calibrated! "
                "Please set it in Calibration Tool."
            )
        return
    
    current_time = time.time()
    
    # OPTIMIZATION: Skip repair checks during active skill execution
    # This prevents delays in skill sequence combos
    if config.skill_sequence_manager:
        # Skip if skill is waiting for activation (skill was just triggered)
        if (hasattr(config.skill_sequence_manager, 'skill_waiting_activation') and 
            config.skill_sequence_manager.skill_waiting_activation):
            return
        
        # Skip if skill was executed recently (within last 0.3 seconds) - short window to avoid combo delays
        if (hasattr(config.skill_sequence_manager, 'ultimo_tiempo_skill') and
            config.skill_sequence_manager.ultimo_tiempo_skill > 0 and
            current_time - config.skill_sequence_manager.ultimo_tiempo_skill < 0.3):
            return
    
    # Throttle checks based on interval
    if (current_time - config.last_auto_repair_check_time < 
            config.AUTO_REPAIR_CHECK_INTERVAL):
        return
    
    config.last_auto_repair_check_time = current_time
    
    # Follow pattern from buffs/skill sequence: capture full screen once, extract region
    if not config.calibrator:
        return
    
    try:
        # Get window handle
        if hasattr(config.connected_window, 'handle'):
            hwnd = config.connected_window.handle
        else:
            hwnd = config.connected_window
        
        # Capture full screen (like auto_attack and buffs do)
        screen = config.calibrator.capture_window(hwnd)
        if screen is None:
            return
        
        # Fast check: Only proceed if image has changed (avoids expensive OCR on identical frames)
        # This follows the pattern: extract region from screen, check for changes
        if not _image_change_detector.has_image_changed(screen, current_time):
            return
        
        # Save debug image when change detected (like buffs save debug images)
        _image_change_detector.save_debug_image()
        
        # Read system message (only when image changed)
        message_text = ocr_utils.read_system_message_ocr(debug_prefix="[Auto Repair]")
        
        # Debug: Log when message is read (but no break warning detected)
        if message_text:
            # Check what text was read
            if isinstance(message_text, dict):
                lines = message_text.get('lines', [])
                full_text = message_text.get('full', '')
                if lines:
                    # Only log if it contains relevant keywords to avoid spam
                    text_lower = full_text.lower()
                    if 'about' in text_lower or 'break' in text_lower:
                        print(f"[Auto Repair] OCR read message (checking for break warning): {full_text[:100]}")
                else:
                    print(f"[Auto Repair] OCR returned empty lines")
            else:
                print(f"[Auto Repair] OCR returned non-dict: {type(message_text)}")
        else:
            # Mark empty OCR to avoid repeated checks
            _image_change_detector.mark_empty_ocr(current_time)
            # Only log occasionally to avoid spam
            if not hasattr(check_auto_repair, 'last_no_message_log'):
                check_auto_repair.last_no_message_log = 0
            if current_time - check_auto_repair.last_no_message_log > 5.0:
                print(f"[Auto Repair] OCR returned no message (system message area may be empty or OCR failed)")
                check_auto_repair.last_no_message_log = current_time
        
    except Exception as e:
        print(f"[Auto Repair] Error in check: {e}")
        import traceback
        traceback.print_exc()
        return
    
    if not message_text:
        return
    
    # Check for break warning
    break_warning_detected = ocr_utils.check_item_break_warning(message_text)
    
    # Debug: Log keyword check result
    if not break_warning_detected:
        # Only log occasionally when we have text but no match
        if isinstance(message_text, dict):
            full_text = message_text.get('full', '')
            text_lower = full_text.lower()
            if 'about' in text_lower or 'break' in text_lower:
                if not hasattr(check_auto_repair, 'last_no_match_log'):
                    check_auto_repair.last_no_match_log = 0
                if current_time - check_auto_repair.last_no_match_log > 2.0:
                    print(f"[Auto Repair] Text contains 'about' or 'break' but pattern 'is about to break' not found: {full_text[:100]}")
                    check_auto_repair.last_no_match_log = current_time
    
    if break_warning_detected:
        # Add detection
        _break_warning_tracker.add_detection(current_time)
        detection_count = _break_warning_tracker.get_count()
        
        # Log detection (throttled)
        if _repair_state_manager.should_log_detection(current_time):
            print(
                f"[Auto Repair] Item break warning detected "
                f"(count: {detection_count}/{config.BREAK_WARNING_TRIGGER_COUNT})"
            )
        
        # Check if repair should be triggered
        if _break_warning_tracker.should_trigger_repair():
            if not RepairExecutor.is_on_cooldown(current_time):
                # Execute repair
                RepairExecutor.execute_repair(current_time)
                _break_warning_tracker.clear()
            else:
                # Log cooldown (throttled)
                if _repair_state_manager.should_log_cooldown(current_time):
                    remaining = RepairExecutor.get_remaining_cooldown(current_time)
                    print(
                        f"[Auto Repair] Repair on cooldown "
                        f"({remaining:.1f}s remaining)"
                    )
