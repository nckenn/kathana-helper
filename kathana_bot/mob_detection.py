"""
Mob detection and filtering using OCR
"""
import threading
import numpy as np
import time
import win32gui
from PIL import ImageGrab
import config
import window_utils
import ocr_utils


# Initialize lock for thread-safe mob detection
if config.mob_detection_lock is None:
    config.mob_detection_lock = threading.Lock()


def detect_mob_name():
    """Detect mob name using OCR (EasyOCR)"""
    if not config.connected_window:
        return None
    
    if not ocr_utils.initialize_ocr_reader():
        return config.current_target_mob
    
    acquired = config.mob_detection_lock.acquire(timeout=0.1)
    if not acquired:
        return config.current_target_mob
    
    try:
        hwnd = config.connected_window.handle
        
        x = config.target_name_area['x']
        y = config.target_name_area['y']
        width = config.target_name_area['width']
        height = config.target_name_area['height']
        
        if width <= 0 or height <= 0:
            return config.current_target_mob
        
        center_x = x
        center_y = y
        half_width = width // 2
        half_height = height // 2
        
        left = center_x - half_width
        top = center_y - half_height
        
        img = window_utils.capture_window_region(hwnd, left, top, width, height)
        
        if img is None:
            try:
                right = center_x + half_width
                bottom = center_y + half_height
                rect = win32gui.GetWindowRect(hwnd)
                screen_left = rect[0] + left
                screen_top = rect[1] + top
                screen_right = rect[0] + right
                screen_bottom = rect[1] + bottom
                img = ImageGrab.grab(bbox=(screen_left, screen_top, screen_right, screen_bottom))
            except:
                return config.current_target_mob
        
        img_array = np.array(img)
        results = config.ocr_reader.readtext(img_array, detail=0, paragraph=False)
        
        if results and len(results) > 0:
            mob_name = results[0].strip()
            if mob_name:
                config.current_target_mob = mob_name
                return mob_name
        
        return config.current_target_mob
            
    except Exception as e:
        return config.current_target_mob
    finally:
        config.mob_detection_lock.release()


def should_skip_current_mob():
    """Check if current mob should be skipped"""
    if not config.current_target_mob or not config.mob_skip_list:
        return False
    
    for skip_mob in config.mob_skip_list:
        if skip_mob.lower() in config.current_target_mob.lower():
            return True
    
    return False


def update_mob_display():
    """Update the mob display in the GUI - periodic updates to catch target changes"""
    try:
        current_time = time.time()
        time_since_last_detection = current_time - config.last_mob_detection_time
        
        if time_since_last_detection < 0.5:
            # Recent detection - just update GUI
            try:
                from gui import BotGUI
                from config import safe_update_gui
                if hasattr(BotGUI, '_instance') and BotGUI._instance:
                    gui = BotGUI._instance
                    if config.current_target_mob:
                        mob_name = config.current_target_mob
                        if config.mob_detection_enabled and should_skip_current_mob():
                            safe_update_gui(lambda: gui.current_mob_label.configure(text=mob_name, text_color="orange"))
                        else:
                            safe_update_gui(lambda: gui.current_mob_label.configure(text=mob_name, text_color="green"))
                    else:
                        safe_update_gui(lambda: gui.current_mob_label.configure(text="None", text_color="red"))
            except:
                pass
            return
        
        if time_since_last_detection < config.MOB_DETECTION_INTERVAL:
            return
        
        config.last_mob_detection_time = current_time
        
        detected_mob = detect_mob_name()
        
        if detected_mob:
            config.current_target_mob = detected_mob
        
        # Update GUI
        try:
            from gui import BotGUI
            from config import safe_update_gui
            if hasattr(BotGUI, '_instance') and BotGUI._instance:
                gui = BotGUI._instance
                if detected_mob:
                    mob_name = detected_mob
                    if config.mob_detection_enabled and should_skip_current_mob():
                        safe_update_gui(lambda: gui.current_mob_label.configure(text=mob_name, text_color="orange"))
                    else:
                        safe_update_gui(lambda: gui.current_mob_label.configure(text=mob_name, text_color="green"))
                else:
                    safe_update_gui(lambda: gui.current_mob_label.configure(text="None", text_color="red"))
        except:
            pass
    except Exception as e:
        pass
