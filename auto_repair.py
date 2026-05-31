"""
Auto repair — detects light-green 'is about to break' warning text in the
calibrated system message region (CV color + line shape, no OCR) and presses repair.
"""
import os
import time

import config
import debug_io
import skill_bar_actions
import window_utils

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print('[CV2] OpenCV not available. Install with: pip install opencv-python')


CALIBRATION_WARN_INTERVAL = 30.0
DETECTION_LOG_INTERVAL = 2.0
COOLDOWN_LOG_INTERVAL = 5.0

# Light-green in-game warning text (HSV) — excludes magenta combat log (H ~150)
WARNING_GREEN_LOWER = np.array([48, 70, 95]) if CV2_AVAILABLE else None
WARNING_GREEN_UPPER = np.array([70, 140, 255]) if CV2_AVAILABLE else None
MIN_GREEN_PIXEL_RATIO = 0.003
MIN_WARNING_LINE_WIDTH = 70


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
    """Clicks the repair skill icon in the skill bar when a warning threshold is reached."""

    @staticmethod
    def execute_repair(current_time, hwnd):
        print("[Auto Repair] REPAIR TRIGGERED - clicking repair skill in skill bar")
        if skill_bar_actions.click_skill_icon(hwnd, 'hammer'):
            config.last_repair_time = current_time
            return True
        print("[Auto Repair] Could not find hammer icon in skill bar")
        return False

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


def build_warning_green_mask(bgr_image):
    """Mask pixels matching the light-green break-warning text color."""
    if not CV2_AVAILABLE or bgr_image is None or bgr_image.size == 0:
        return None
    hsv = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2HSV)
    return cv2.inRange(hsv, WARNING_GREEN_LOWER, WARNING_GREEN_UPPER)


def _max_green_run_in_row(mask_row):
    xs = np.where(mask_row > 0)[0]
    if xs.size == 0:
        return 0
    return int(xs[-1] - xs[0] + 1)


def analyze_break_warning(bgr_image):
    """
    Detect light-green warning line(s) in a captured system-message region.
    Returns (detected: bool, info: dict).
    """
    if not CV2_AVAILABLE or bgr_image is None or bgr_image.size == 0:
        return False, {}

    mask = build_warning_green_mask(bgr_image)
    if mask is None:
        return False, {}

    ratio = float(np.count_nonzero(mask)) / float(mask.size)
    if ratio < MIN_GREEN_PIXEL_RATIO:
        return False, {'green_ratio': ratio}

    best_line_width = 0
    qualifying_rows = 0
    for y in range(mask.shape[0]):
        run = _max_green_run_in_row(mask[y])
        best_line_width = max(best_line_width, run)
        if run >= MIN_WARNING_LINE_WIDTH:
            qualifying_rows += 1

    detected = qualifying_rows >= 1
    return detected, {
        'green_ratio': ratio,
        'best_line_width': best_line_width,
        'qualifying_rows': qualifying_rows,
        'mask': mask,
    }


class WarningTextDetector:
    """Region capture + CV detection for break-warning text."""

    def __init__(self):
        self.last_message_area = None
        self._warning_visible = False

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
        return window_utils.capture_window_region_bgr(hwnd, left, top, width, height)

    def detect_break_warning(self, hwnd):
        """
        Return True only when the break-warning newly appears (not visible -> visible).
        While the same message stays on screen, returns False so we count appearances,
        not poll ticks. Counter is not reset when the message scrolls away.
        """
        if not CV2_AVAILABLE:
            return False

        region = self.capture_warning_region(hwnd)
        if region is None:
            self._warning_visible = False
            return False

        detected, info = analyze_break_warning(region)
        if not detected:
            self._warning_visible = False
            return False

        if self._warning_visible:
            return False

        self._warning_visible = True
        self.last_message_area = region.copy()

        if debug_io.should_save_debug_images():
            debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'debug')
            os.makedirs(debug_dir, exist_ok=True)
            debug_io.save_cv2_image(
                os.path.join(debug_dir, 'system_message_area.png'), region)
            mask = info.get('mask')
            if mask is not None:
                debug_io.save_cv2_image(
                    os.path.join(debug_dir, 'system_message_green_mask.png'), mask)

        return True


_break_warning_tracker = BreakWarningTracker()
_repair_state_manager = RepairStateManager()
_warning_detector = WarningTextDetector()


def get_repair_count():
    return _break_warning_tracker.get_count()


def get_repair_trigger_count():
    return config.BREAK_WARNING_TRIGGER_COUNT


def reset_repair_count():
    """Clear accumulated break-warning appearances and detection state."""
    _break_warning_tracker.clear()
    _warning_detector._warning_visible = False
    update_repair_count_display()


def update_repair_count_display():
    """Thread-safe refresh of the auto-repair warning counter in the GUI."""
    try:
        from gui import BotGUI
        from config import safe_update_gui

        if not hasattr(BotGUI, '_instance') or not BotGUI._instance:
            return
        gui = BotGUI._instance
        if not hasattr(gui, 'auto_repair_count_label'):
            return
        safe_update_gui(gui._update_auto_repair_count_display)
    except Exception:
        pass


def check_auto_repair():
    """
    Poll the warning region for light-green break-warning text.
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
        detected = _warning_detector.detect_break_warning(hwnd)
    except Exception as e:
        print(f"[Auto Repair] Error in check: {e}")
        return

    if not detected:
        return

    _break_warning_tracker.add_detection(current_time)
    detection_count = _break_warning_tracker.get_count()
    update_repair_count_display()

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

    if RepairExecutor.execute_repair(current_time, hwnd):
        reset_repair_count()
