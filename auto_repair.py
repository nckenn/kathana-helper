"""
Auto repair — detects light-green 'is about to break' warning text in the
calibrated system message region and presses the repair hotkey.
"""
import hashlib
import os
import time

import config
import debug_io
import input_handler
import ocr_utils

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print('[CV2] OpenCV not available. Install with: pip install opencv-python')

import window_utils


CALIBRATION_WARN_INTERVAL = 30.0
DETECTION_LOG_INTERVAL = 2.0
COOLDOWN_LOG_INTERVAL = 5.0

# Light-green/yellow-green in-game warning text (HSV)
WARNING_GREEN_LOWER = np.array([25, 30, 150]) if CV2_AVAILABLE else None
WARNING_GREEN_UPPER = np.array([95, 255, 255]) if CV2_AVAILABLE else None
MIN_GREEN_PIXEL_RATIO = 0.004


class BreakWarningTracker:
    """Tracks break warning detections."""

    def __init__(self):
        self.detection_timestamps = []

    def add_detection(self, current_time):
        self.detection_timestamps.append(current_time)

    def get_count(self):
        return len(self.detection_timestamps)

    def clear(self):
        self.detection_timestamps.clear()

    def should_trigger_repair(self):
        return self.get_count() >= config.BREAK_WARNING_TRIGGER_COUNT


class RepairExecutor:
    """Presses the configured repair hotkey when a warning is detected."""

    @staticmethod
    def execute_repair(current_time):
        repair_key = (getattr(config, 'repair_key', None) or 'f10').strip()
        if not repair_key:
            print("[Auto Repair] Cannot execute repair: no repair key configured")
            return False
        print(f"[Auto Repair] REPAIR TRIGGERED - pressing key '{repair_key}'")
        input_handler.send_input(repair_key)
        config.last_repair_time = current_time
        return True

    @staticmethod
    def is_on_cooldown(current_time):
        return (current_time - config.last_repair_time) < config.REPAIR_COOLDOWN

    @staticmethod
    def get_remaining_cooldown(current_time):
        elapsed = current_time - config.last_repair_time
        return max(0.0, config.REPAIR_COOLDOWN - elapsed)


class RepairStateManager:
    def __init__(self):
        self.last_warn_time = 0
        self.last_log_time = 0
        self.last_cooldown_log_time = 0

    def should_warn_calibration(self, current_time):
        if current_time - self.last_warn_time > CALIBRATION_WARN_INTERVAL:
            self.last_warn_time = current_time
            return True
        return False

    def should_log_detection(self, current_time):
        if current_time - self.last_log_time > DETECTION_LOG_INTERVAL:
            self.last_log_time = current_time
            return True
        return False

    def should_log_cooldown(self, current_time):
        if current_time - self.last_cooldown_log_time > COOLDOWN_LOG_INTERVAL:
            self.last_cooldown_log_time = current_time
            return True
        return False


class CalibrationValidator:
    @staticmethod
    def is_calibrated():
        return (config.system_message_area.get('width', 0) > 0 and
                config.system_message_area.get('height', 0) > 0)


class WarningTextDetector:
    """Region-only capture with light-green pre-filter before OCR."""

    def __init__(self):
        self.last_image_hash = None
        self.last_ocr_time = 0
        self.min_ocr_interval = 1.0
        self.last_message_area = None

    def _region_bounds(self):
        x = config.system_message_area['x']
        y = config.system_message_area['y']
        width = config.system_message_area['width']
        height = config.system_message_area['height']
        if width <= 0 or height <= 0:
            return None
        half_width = width // 2
        half_height = height // 2
        left = x - half_width
        top = y - half_height
        return left, top, width, height

    def capture_warning_region(self, hwnd):
        bounds = self._region_bounds()
        if bounds is None:
            return None
        left, top, width, height = bounds
        img = window_utils.capture_window_region(hwnd, left, top, width, height)
        if img is None:
            return None
        arr = np.array(img)
        if CV2_AVAILABLE and len(arr.shape) == 3 and arr.shape[2] == 3:
            return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        return arr

    def has_warning_green_text(self, bgr_image):
        if not CV2_AVAILABLE or bgr_image is None or bgr_image.size == 0:
            return False, None
        hsv = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, WARNING_GREEN_LOWER, WARNING_GREEN_UPPER)
        ratio = float(np.count_nonzero(mask)) / float(mask.size)
        return ratio >= MIN_GREEN_PIXEL_RATIO, mask

    def prepare_ocr_image(self, bgr_image, green_mask):
        if not CV2_AVAILABLE or bgr_image is None:
            return bgr_image
        if green_mask is not None:
            filtered = cv2.bitwise_and(bgr_image, bgr_image, mask=green_mask)
            if np.count_nonzero(green_mask) > 0:
                return cv2.cvtColor(filtered, cv2.COLOR_BGR2RGB)
        return cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)

    def calculate_image_hash(self, img_array):
        if img_array is None or img_array.size == 0:
            return None
        try:
            sampled = img_array[::4, ::4]
            return hashlib.md5(sampled.tobytes()).hexdigest()
        except Exception:
            return None

    def detect_break_warning(self, hwnd, current_time):
        """Return OCR dict if break warning text is present, else None."""
        if not CV2_AVAILABLE:
            return None

        region = self.capture_warning_region(hwnd)
        if region is None:
            return None

        has_green, green_mask = self.has_warning_green_text(region)
        if not has_green:
            self.last_image_hash = self.calculate_image_hash(region)
            return None

        current_hash = self.calculate_image_hash(region)
        if current_hash is None:
            return None

        if current_hash == self.last_image_hash:
            return None

        if current_time - self.last_ocr_time < self.min_ocr_interval:
            return None

        self.last_image_hash = current_hash
        self.last_ocr_time = current_time
        self.last_message_area = region.copy()

        if debug_io.should_save_debug_images():
            debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'debug')
            os.makedirs(debug_dir, exist_ok=True)
            debug_io.save_cv2_image(
                os.path.join(debug_dir, 'system_message_area.png'), region)
            if green_mask is not None:
                debug_io.save_cv2_image(
                    os.path.join(debug_dir, 'system_message_green_mask.png'), green_mask)

        ocr_image = self.prepare_ocr_image(region, green_mask)
        return ocr_utils.read_system_message_ocr_from_image(
            ocr_image, debug_prefix="[Auto Repair]")


_break_warning_tracker = BreakWarningTracker()
_repair_state_manager = RepairStateManager()
_warning_detector = WarningTextDetector()


def get_repair_count():
    return _break_warning_tracker.get_count()


def get_repair_trigger_count():
    return config.BREAK_WARNING_TRIGGER_COUNT


def check_auto_repair():
    """
    Poll the warning region every ~300ms for light-green break-warning text.
    OCR runs only when green text is visible and the region changed.
    """
    if not config.auto_repair_enabled:
        return

    if not CalibrationValidator.is_calibrated():
        current_time = time.time()
        if _repair_state_manager.should_warn_calibration(current_time):
            print(
                "[Auto Repair] Warning region not calibrated! "
                "Set the system message area in Calibration."
            )
        return

    current_time = time.time()

    if config.skill_sequence_manager:
        if (hasattr(config.skill_sequence_manager, 'skill_waiting_activation') and
                config.skill_sequence_manager.skill_waiting_activation):
            return
        if (hasattr(config.skill_sequence_manager, 'ultimo_tiempo_skill') and
                config.skill_sequence_manager.ultimo_tiempo_skill > 0 and
                current_time - config.skill_sequence_manager.ultimo_tiempo_skill < 0.3):
            return

    if (current_time - config.last_auto_repair_check_time <
            config.get_auto_repair_check_interval()):
        return

    config.last_auto_repair_check_time = current_time

    if not config.connected_window:
        return

    try:
        hwnd = (config.connected_window.handle
                if hasattr(config.connected_window, 'handle')
                else config.connected_window)
        message_text = _warning_detector.detect_break_warning(hwnd, current_time)
    except Exception as e:
        print(f"[Auto Repair] Error in check: {e}")
        return

    if not message_text:
        return

    if not ocr_utils.check_item_break_warning(message_text):
        return

    _break_warning_tracker.add_detection(current_time)
    detection_count = _break_warning_tracker.get_count()

    if _repair_state_manager.should_log_detection(current_time):
        print(
            f"[Auto Repair] Break warning detected "
            f"(count: {detection_count}/{config.BREAK_WARNING_TRIGGER_COUNT})"
        )

    if not _break_warning_tracker.should_trigger_repair():
        return

    if RepairExecutor.is_on_cooldown(current_time):
        if _repair_state_manager.should_log_cooldown(current_time):
            remaining = RepairExecutor.get_remaining_cooldown(current_time)
            print(f"[Auto Repair] Repair on cooldown ({remaining:.1f}s remaining)")
        return

    if RepairExecutor.execute_repair(current_time):
        _break_warning_tracker.clear()
