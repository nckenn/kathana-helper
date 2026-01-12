"""
HP/MP bar detection and percentage calculation
"""
import numpy as np
from PIL import Image
import win32gui
from PIL import ImageGrab
import config
import window_utils
import input_handler
import time


def calculate_bar_percentage(img, bar_type='hp'):
    """Calculate the fill percentage of an HP or MP bar with gradient colors
    Returns percentage (0-100) based on filled vs empty area detection
    Improved algorithm with multi-row sampling for consistency during panning"""
    try:
        img_array = np.array(img)
        height, width, channels = img_array.shape
        
        if height < 5 or width < 10:
            print(f"Warning: Bar image too small ({width}x{height}), returning 100%")
            return 100
        
        sample_rows = [
            height // 4,
            height // 2,
            (3 * height) // 4
        ]
        
        filled_widths = []
        
        for row_idx in sample_rows:
            if row_idx >= height:
                continue
                
            filled_width = 0
            empty_columns = 0
            
            if bar_type == 'hp':
                for x in range(width):
                    column = img_array[:, x, :]
                    
                    red_pixels = column[:, 0]
                    green_pixels = column[:, 1]
                    blue_pixels = column[:, 2]
                    
                    red_dominant_count = np.sum((red_pixels > 50) & 
                                                (red_pixels > green_pixels + 10) & 
                                                (red_pixels > blue_pixels + 10))
                    
                    bright_red_count = np.sum(red_pixels > 60)
                    red_bright_count = np.sum((red_pixels > 40) | (green_pixels > 40))
                    
                    threshold_factor = 0.15
                    
                    is_filled = (red_dominant_count > height * threshold_factor or 
                                bright_red_count > height * 0.2 or
                                red_bright_count > height * 0.25)
                    
                    if is_filled:
                        filled_width += 1
                        empty_columns = 0
                    else:
                        empty_columns += 1
                        if empty_columns >= 3:
                            break
            else:  # mp
                for x in range(width):
                    column = img_array[:, x, :]
                    
                    red_pixels = column[:, 0]
                    green_pixels = column[:, 1]
                    blue_pixels = column[:, 2]
                    
                    blue_dominant_count = np.sum((blue_pixels > 50) & 
                                                 (blue_pixels > red_pixels + 10))
                    
                    cyan_count = np.sum((blue_pixels > 50) & (green_pixels > 40))
                    blue_bright_count = np.sum((blue_pixels > 40) | (green_pixels > 40))
                    
                    threshold_factor = 0.12
                    
                    is_filled = (blue_dominant_count > height * threshold_factor or 
                                cyan_count > height * 0.15 or
                                blue_bright_count > height * 0.25)
                    
                    if is_filled:
                        filled_width += 1
                        empty_columns = 0
                    else:
                        empty_columns += 1
                        if empty_columns >= 3:
                            break
            
            filled_widths.append(filled_width)
        
        if filled_widths:
            filled_widths.sort()
            median_filled = filled_widths[len(filled_widths) // 2]
            percentage = (median_filled / width) * 100 if width > 0 else 0
        else:
            percentage = 100
        
        return min(100, max(0, percentage))
        
    except Exception as e:
        print(f"Error calculating bar percentage ({bar_type}): {e}")
        return 100


def check_HP():
    """Check player HP and use potion if low"""
    if not config.connected_window:
        return
    
    current_time = time.time()
    if current_time - config.last_hp_capture_time < config.HP_CAPTURE_INTERVAL:
        return
    
    config.last_hp_capture_time = current_time
    
    # Get bar area from GUI if available, otherwise use defaults
    try:
        from gui import BotGUI
        if hasattr(BotGUI, '_instance') and BotGUI._instance:
            gui = BotGUI._instance
            x = int(gui.hp_x_var.get())
            y = int(gui.hp_y_var.get())
            width = int(gui.hp_width_var.get())
            height = int(gui.hp_height_var.get())
            threshold = int(gui.hp_threshold_var.get())
        else:
            x = config.hp_bar_area['x']
            y = config.hp_bar_area['y']
            width = config.hp_bar_area['width']
            height = config.hp_bar_area['height']
            threshold = config.hp_threshold
    except (ValueError, AttributeError):
        x = config.hp_bar_area['x']
        y = config.hp_bar_area['y']
        width = config.hp_bar_area['width']
        height = config.hp_bar_area['height']
        threshold = config.hp_threshold
    
    if width <= 0 or height <= 0:
        return
    
    try:
        hwnd = config.connected_window.handle
        bar_img = window_utils.capture_window_region(hwnd, x, y, width, height)
        
        if bar_img is None:
            rect = win32gui.GetWindowRect(hwnd)
            screen_x = rect[0] + x
            screen_y = rect[1] + y
            bar_img = ImageGrab.grab(bbox=(screen_x, screen_y, screen_x + width, screen_y + height))
        
        if bar_img is None:
            return
        
        raw_hp_percentage = calculate_bar_percentage(bar_img, 'hp')
        
        config.hp_readings.append(raw_hp_percentage)
        if len(config.hp_readings) > config.HP_MP_SMOOTHING_WINDOW:
            config.hp_readings.pop(0)
        
        hp_percentage = sum(config.hp_readings) / len(config.hp_readings) if config.hp_readings else raw_hp_percentage
        
        # Update GUI display
        try:
            from gui import BotGUI
            from config import safe_update_gui
            if hasattr(BotGUI, '_instance') and BotGUI._instance:
                gui = BotGUI._instance
                if hasattr(gui, 'hp_percent_label'):
                    safe_update_gui(lambda: gui.hp_percent_label.configure(text=f"{hp_percentage:.1f}%"))
                if hasattr(gui, 'hp_progress_bar'):
                    safe_update_gui(lambda: gui.hp_progress_bar.set(hp_percentage / 100.0))
        except:
            pass
        
    except Exception as e:
        current_time = time.time()
        if current_time - config.last_hp_log_time >= config.HP_MP_LOG_INTERVAL:
            print(f"Error capturing HP bar: {e}")
            config.last_hp_log_time = current_time
        return
    
    current_time = time.time()
    if hp_percentage <= threshold:
        if config.auto_hp_enabled:
            use_potion()
            print(f"HP Low ({hp_percentage:.1f}%) - Using Potion (threshold: {threshold}%)")
            config.last_hp_log_time = current_time
            config.hp_readings.clear()
        else:
            if current_time - config.last_hp_log_time >= config.HP_MP_LOG_INTERVAL:
                print(f"HP Low ({hp_percentage:.1f}%) - Auto HP disabled")
                config.last_hp_log_time = current_time
    else:
        if current_time - config.last_hp_log_time >= config.HP_MP_LOG_INTERVAL:
            print(f"HP OK ({hp_percentage:.1f}%)")
            config.last_hp_log_time = current_time


def check_MP():
    """Check player MP and use potion if low"""
    if not config.connected_window:
        return
    
    current_time = time.time()
    if current_time - config.last_mp_capture_time < config.MP_CAPTURE_INTERVAL:
        return
    
    config.last_mp_capture_time = current_time
    
    try:
        from gui import BotGUI
        from config import safe_update_gui
        if hasattr(BotGUI, '_instance') and BotGUI._instance:
            gui = BotGUI._instance
            x = int(gui.mp_x_var.get())
            y = int(gui.mp_y_var.get())
            width = int(gui.mp_width_var.get())
            height = int(gui.mp_height_var.get())
            threshold = int(gui.mp_threshold_var.get())
        else:
            x = config.mp_bar_area['x']
            y = config.mp_bar_area['y']
            width = config.mp_bar_area['width']
            height = config.mp_bar_area['height']
            threshold = config.mp_threshold
    except (ValueError, AttributeError):
        x = config.mp_bar_area['x']
        y = config.mp_bar_area['y']
        width = config.mp_bar_area['width']
        height = config.mp_bar_area['height']
        threshold = config.mp_threshold
    
    if width <= 0 or height <= 0:
        return
    
    try:
        hwnd = config.connected_window.handle
        bar_img = window_utils.capture_window_region(hwnd, x, y, width, height)
        
        if bar_img is None:
            rect = win32gui.GetWindowRect(hwnd)
            screen_x = rect[0] + x
            screen_y = rect[1] + y
            bar_img = ImageGrab.grab(bbox=(screen_x, screen_y, screen_x + width, screen_y + height))
        
        if bar_img is None:
            return
        
        raw_mp_percentage = calculate_bar_percentage(bar_img, 'mp')
        
        config.mp_readings.append(raw_mp_percentage)
        if len(config.mp_readings) > config.HP_MP_SMOOTHING_WINDOW:
            config.mp_readings.pop(0)
        
        mp_percentage = sum(config.mp_readings) / len(config.mp_readings) if config.mp_readings else raw_mp_percentage
        
        # Update GUI display
        try:
            from gui import BotGUI
            from config import safe_update_gui
            if hasattr(BotGUI, '_instance') and BotGUI._instance:
                gui = BotGUI._instance
                if hasattr(gui, 'mp_percent_label'):
                    safe_update_gui(lambda: gui.mp_percent_label.configure(text=f"{mp_percentage:.1f}%"))
                if hasattr(gui, 'mp_progress_bar'):
                    safe_update_gui(lambda: gui.mp_progress_bar.set(mp_percentage / 100.0))
        except:
            pass
        
    except Exception as e:
        current_time = time.time()
        if current_time - config.last_mp_log_time >= config.HP_MP_LOG_INTERVAL:
            print(f"Error capturing MP bar: {e}")
            config.last_mp_log_time = current_time
        return
    
    current_time = time.time()
    if mp_percentage <= threshold:
        if config.auto_mp_enabled:
            use_mp_potion()
            print(f"MP Low ({mp_percentage:.1f}%) - Using Potion (threshold: {threshold}%)")
            config.last_mp_log_time = current_time
            config.mp_readings.clear()
        else:
            if current_time - config.last_mp_log_time >= config.HP_MP_LOG_INTERVAL:
                print(f"MP Low ({mp_percentage:.1f}%) - Auto MP disabled")
                config.last_mp_log_time = current_time
    else:
        if current_time - config.last_mp_log_time >= config.HP_MP_LOG_INTERVAL:
            print(f"MP OK ({mp_percentage:.1f}%)")
            config.last_mp_log_time = current_time


def use_potion():
    """Use health potion when HP is low"""
    input_handler.send_input('0')
    time.sleep(0.5)


def use_mp_potion():
    """Use mana potion when MP is low"""
    input_handler.send_input('9')
    time.sleep(0.5)


def check_enemy_HP():
    """Check enemy HP bar and update GUI display, auto-target when no target"""
    import numpy as np
    import win32gui
    from PIL import ImageGrab
    import mob_detection
    import bot_logic
    
    if not config.connected_window:
        return
    
    current_time = time.time()
    if current_time - config.last_enemy_hp_capture_time < config.ENEMY_HP_CAPTURE_INTERVAL:
        return
    
    config.last_enemy_hp_capture_time = current_time
    
    # Clear looting flag after looting duration has passed
    if config.is_looting:
        if current_time - config.looting_start_time >= config.LOOTING_DURATION:
            config.is_looting = False
    
    def reset_enemy_state():
        config.enemy_target_time = 0
        config.enemy_hp_readings.clear()
        # Don't reset last_damage_detected_time here - let it continue so unstuck timer keeps running
        # It will be reset when a new target is acquired
        config.last_damage_value = None
        config.last_enemy_hp_for_unstuck = None
        config.last_mob_verification_time = 0
    
    def send_target_key_with_mob_check(recursion_depth=0):
        if recursion_depth >= 5:
            print(f"[Mob Filter] Max retries reached, stopping retarget loop")
            return False
        
        input_handler.send_input(config.action_slots['target']['key'])
        config.last_auto_target_time = current_time
        
        # Increased delay to ensure mob name appears after targeting
        delay = 0.3 if recursion_depth > 0 else 0.2
        time.sleep(delay)
        
        previous_mob = config.current_target_mob
        detected_mob = None
        max_retries = 6  # Increased retries for more reliable detection
        retry_delay = 0.15  # Slightly increased retry delay
        
        for attempt in range(max_retries):
            detected_mob = mob_detection.detect_mob_name()
            if detected_mob:
                if detected_mob != previous_mob or previous_mob is None:
                    config.current_target_mob = detected_mob
                    config.last_mob_detection_time = current_time
                    break
                elif recursion_depth > 0 and attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    config.current_target_mob = detected_mob
                    config.last_mob_detection_time = current_time
                    break
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
        
        try:
            from gui import BotGUI
            from config import safe_update_gui
            if hasattr(BotGUI, '_instance') and BotGUI._instance:
                gui = BotGUI._instance
                if detected_mob:
                    mob_name = detected_mob
                    if config.mob_detection_enabled and mob_detection.should_skip_current_mob():
                        safe_update_gui(lambda: gui.current_mob_label.configure(text=mob_name, text_color="orange"))
                    else:
                        safe_update_gui(lambda: gui.current_mob_label.configure(text=mob_name, text_color="green"))
                else:
                    safe_update_gui(lambda: gui.current_mob_label.configure(text="None", text_color="red"))
        except:
            pass
        
        # Always verify mob detection and skip list check, even if detection failed
        if config.mob_detection_enabled and config.mob_skip_list:
            # Re-detect mob one more time to ensure we have the latest name
            if not detected_mob:
                time.sleep(0.1)
                detected_mob = mob_detection.detect_mob_name()
                if detected_mob:
                    config.current_target_mob = detected_mob
                    config.last_mob_detection_time = current_time
            
            if detected_mob and mob_detection.should_skip_current_mob():
                print(f"[Mob Filter] Skipping mob: {detected_mob} (in skip list, retry {recursion_depth + 1}/5)")
                reset_enemy_state()
                config.current_target_mob = None
                time.sleep(0.25)  # Slightly longer delay before retargeting
                print(f"[Mob Filter] Retargeting to skip mob")
                return send_target_key_with_mob_check(recursion_depth + 1)
        
        return False
    
    def try_auto_target(reason="", bypass_cooldown=False):
        # Don't auto-target if we're currently looting (item names appear in same location as enemy names)
        if config.is_looting:
            return False
        
        if config.auto_attack_enabled:
            if bypass_cooldown or current_time - config.last_auto_target_time >= config.AUTO_TARGET_COOLDOWN:
                send_target_key_with_mob_check()
                if reason:
                    print(f"Auto-targeting ({reason})")
                return True
        return False
    
    try:
        from gui import BotGUI
        if hasattr(BotGUI, '_instance') and BotGUI._instance:
            gui = BotGUI._instance
            x = int(gui.enemy_hp_x_var.get())
            y = int(gui.enemy_hp_y_var.get())
            width = int(gui.enemy_hp_width_var.get())
            height = int(gui.enemy_hp_height_var.get())
        else:
            x = config.target_hp_bar_area['x']
            y = config.target_hp_bar_area['y']
            width = config.target_hp_bar_area['width']
            height = config.target_hp_bar_area['height']
    except (ValueError, AttributeError):
        x, y = config.target_hp_bar_area['x'], config.target_hp_bar_area['y']
        width, height = config.target_hp_bar_area['width'], config.target_hp_bar_area['height']
    
    if width <= 0 or height <= 0:
        return
    
    try:
        hwnd = config.connected_window.handle
        bar_img = window_utils.capture_window_region(hwnd, x, y, width, height)
        
        if bar_img is None:
            rect = win32gui.GetWindowRect(hwnd)
            screen_x = rect[0] + x
            screen_y = rect[1] + y
            bar_img = ImageGrab.grab(bbox=(screen_x, screen_y, screen_x + width, screen_y + height))
        
        enemy_hp_percentage = 0.0
        
        if bar_img is None:
            try:
                from gui import BotGUI
                from config import safe_update_gui
                if hasattr(BotGUI, '_instance') and BotGUI._instance:
                    gui = BotGUI._instance
                    if hasattr(gui, 'enemy_hp_percent_label'):
                        safe_update_gui(lambda: gui.enemy_hp_percent_label.configure(text=f"{enemy_hp_percentage:.1f}%"))
                    if hasattr(gui, 'enemy_hp_progress_bar'):
                        safe_update_gui(lambda: gui.enemy_hp_progress_bar.set(enemy_hp_percentage / 100.0))
                    # Update unstuck countdown (will show "---" when no enemy)
                    if hasattr(gui, 'unstuck_countdown_label'):
                        import auto_unstuck
                        auto_unstuck.update_unstuck_countdown_display(current_time)
            except:
                pass
            return
        
        img_array = np.array(bar_img)
        img_height, img_width, img_channels = img_array.shape
        
        red_channel = img_array[:, :, 0]
        green_channel = img_array[:, :, 1]
        blue_channel = img_array[:, :, 2]
        
        red_dominant_mask = (red_channel > 80) & (red_channel > green_channel + 20) & (red_channel > blue_channel + 20)
        red_dominant_count = np.sum(red_dominant_mask)
        
        bright_red_mask = (red_channel > 100) & (red_channel > green_channel + 15)
        bright_red_count = np.sum(bright_red_mask)
        
        total_pixels = img_height * img_width
        has_red_bar = (red_dominant_count > total_pixels * 0.10) or (bright_red_count > total_pixels * 0.15)
        
        if not has_red_bar:
            if len(config.enemy_hp_readings) > 0 or config.enemy_target_time > 0:
                # Small delay to ensure enemy is fully dead and loot is available
                time.sleep(0.15)
                bot_logic.smart_loot()
                # Don't auto-target immediately after looting - wait for looting to complete
                # The try_auto_target will be blocked by is_looting flag anyway, but we return early here
                reset_enemy_state()
                return
            
            reset_enemy_state()
            # Only try auto-targeting if not looting
            if not config.is_looting:
                try_auto_target("no enemy detected")
        else:
            raw_enemy_hp_percentage = calculate_bar_percentage(bar_img, 'hp')
            
            is_suspicious = raw_enemy_hp_percentage >= 95 and red_dominant_count < total_pixels * 0.15
            
            if is_suspicious:
                enemy_hp_percentage = 0.0
                reset_enemy_state()
                time.sleep(0.15)  # Delay before looting
                bot_logic.smart_loot()
                try_auto_target("no valid target")
            elif config.enemy_hp_readings:
                last_avg = sum(config.enemy_hp_readings) / len(config.enemy_hp_readings)
                if last_avg < 50 and raw_enemy_hp_percentage >= 95:
                    enemy_hp_percentage = 0.0
                    reset_enemy_state()
                    time.sleep(0.15)  # Delay before looting to ensure enemy is dead
                    bot_logic.smart_loot()
                    try_auto_target("enemy died")
                else:
                    config.enemy_hp_readings.append(raw_enemy_hp_percentage)
                    if len(config.enemy_hp_readings) > config.HP_MP_SMOOTHING_WINDOW:
                        config.enemy_hp_readings.pop(0)
                    enemy_hp_percentage = sum(config.enemy_hp_readings) / len(config.enemy_hp_readings)
                    
                    # Periodic mob verification during combat to catch skip list mobs
                    if config.mob_detection_enabled and config.mob_skip_list and config.enemy_target_time > 0:
                        # Check mob every 2 seconds during combat
                        if current_time - config.last_mob_verification_time > 2.0:
                            config.last_mob_verification_time = current_time
                            detected_mob = mob_detection.detect_mob_name()
                            if detected_mob:
                                config.current_target_mob = detected_mob
                                config.last_mob_detection_time = current_time
                                if mob_detection.should_skip_current_mob():
                                    print(f"[Mob Filter] Detected skip list mob during combat: {detected_mob} - retargeting")
                                    reset_enemy_state()
                                    time.sleep(0.2)
                                    try_auto_target("skip list mob detected during combat")
                                    return
                    
                    if raw_enemy_hp_percentage <= 3.0 and config.enemy_target_time > 0 and len(config.enemy_hp_readings) > 1:
                        previous_readings = config.enemy_hp_readings[:-1]
                        if previous_readings and max(previous_readings) > 10.0:
                            print(f"Enemy HP dropped from {max(previous_readings):.1f}% to {raw_enemy_hp_percentage:.1f}% - triggering smart loot")
                            # Small delay to ensure enemy is fully dead before looting
                            time.sleep(0.1)
                            bot_logic.smart_loot()
                            enemy_hp_percentage = 0.0
                            reset_enemy_state()
            else:
                config.enemy_hp_readings.append(raw_enemy_hp_percentage)
                enemy_hp_percentage = raw_enemy_hp_percentage
            
            if enemy_hp_percentage > 0:
                if config.enemy_target_time == 0:
                    config.enemy_target_time = current_time
                    config.last_unstuck_check_time = 0  # Reset unstuck check interval to allow immediate damage detection
                    config.last_enemy_hp_for_unstuck = None  # Reset HP tracking for new enemy
                    config.last_damage_detected_time = current_time  # Reset damage detection timer for new target
                    
                    # Verify mob detection after targeting to ensure we have the correct mob name
                    if config.mob_detection_enabled:
                        time.sleep(0.1)  # Small delay for mob name to appear
                        detected_mob = mob_detection.detect_mob_name()
                        if detected_mob:
                            config.current_target_mob = detected_mob
                            config.last_mob_detection_time = current_time
                            if config.mob_skip_list and mob_detection.should_skip_current_mob():
                                print(f"[Mob Filter] Detected skip list mob after targeting: {detected_mob} - retargeting")
                                reset_enemy_state()
                                time.sleep(0.2)
                                try_auto_target("skip list mob detected")
                                return
                    
                    print(f"Enemy targeted")
        
        try:
            from gui import BotGUI
            from config import safe_update_gui
            if hasattr(BotGUI, '_instance') and BotGUI._instance:
                gui = BotGUI._instance
                if hasattr(gui, 'enemy_hp_percent_label'):
                    safe_update_gui(lambda: gui.enemy_hp_percent_label.configure(text=f"{enemy_hp_percentage:.1f}%"))
                if hasattr(gui, 'enemy_hp_progress_bar'):
                    safe_update_gui(lambda: gui.enemy_hp_progress_bar.set(enemy_hp_percentage / 100.0))
                # Update unstuck countdown when enemy HP is displayed
                if hasattr(gui, 'unstuck_countdown_label'):
                    import auto_unstuck
                    auto_unstuck.update_unstuck_countdown_display(current_time)
        except:
            pass
        
    except Exception as e:
        current_time = time.time()
        if current_time - config.last_enemy_hp_log_time >= config.HP_MP_LOG_INTERVAL:
            print(f"Error capturing enemy HP bar: {e}")
            config.last_enemy_hp_log_time = current_time
        enemy_hp_percentage = 0.0
        try:
            from gui import BotGUI
            from config import safe_update_gui
            if hasattr(BotGUI, '_instance') and BotGUI._instance:
                gui = BotGUI._instance
                if hasattr(gui, 'enemy_hp_percent_label'):
                    safe_update_gui(lambda: gui.enemy_hp_percent_label.configure(text=f"{enemy_hp_percentage:.1f}%"))
                if hasattr(gui, 'enemy_hp_progress_bar'):
                    safe_update_gui(lambda: gui.enemy_hp_progress_bar.set(enemy_hp_percentage / 100.0))
                # Update unstuck countdown (will show "---" when no enemy)
                if hasattr(gui, 'unstuck_countdown_label'):
                    import auto_unstuck
                    auto_unstuck.update_unstuck_countdown_display(current_time)
        except:
            pass
