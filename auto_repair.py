"""
Auto repair functionality - monitors system messages for item break warnings
Triggers repair when 'is about to break' warning is detected 3 times
"""
import time
import config
import ocr_utils
import input_handler


# ============================================================================
# Constants
# ============================================================================

# Break warning detection
BREAK_WARNING_TRIGGER_COUNT = 3  # Number of detections required to trigger repair

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
        return self.get_count() >= BREAK_WARNING_TRIGGER_COUNT


class RepairExecutor:
    """Handles repair execution"""
    
    @staticmethod
    def execute_repair(current_time):
        """Execute repair action"""
        input_handler.send_input('f10')
        config.last_repair_time = current_time
        print(f"[Auto Repair] REPAIR TRIGGERED (F10)")
    
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


# ============================================================================
# Main Function
# ============================================================================

# Global instances
_break_warning_tracker = BreakWarningTracker()
_repair_state_manager = RepairStateManager()


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
    
    # Throttle checks based on interval
    if (current_time - config.last_auto_repair_check_time < 
            config.AUTO_REPAIR_CHECK_INTERVAL):
        return
    
    config.last_auto_repair_check_time = current_time
    
    # Read system message
    message_text = ocr_utils.read_system_message_ocr(debug_prefix="[Auto Repair]")
    
    if not message_text:
        return
    
    # Check for break warning
    break_warning_detected = ocr_utils.check_item_break_warning(message_text)
    
    if break_warning_detected:
        # Add detection
        _break_warning_tracker.add_detection(current_time)
        detection_count = _break_warning_tracker.get_count()
        
        # Log detection (throttled)
        if _repair_state_manager.should_log_detection(current_time):
            print(
                f"[Auto Repair] Item break warning detected "
                f"(count: {detection_count}/{BREAK_WARNING_TRIGGER_COUNT})"
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
