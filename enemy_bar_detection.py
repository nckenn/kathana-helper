"""
Enemy HP detection using calibration-based method
Detects enemy HP bar position and percentage relative to player MP bar
Future: Will also include enemy name detection
"""
import numpy as np
import cv2
import time
import os
import config
import input_handler
import mob_detection
import bot_logic


def detect_enemy_for_auto_attack(hwnd, targets=None):
    """
    Detect enemy HP percentage and name for auto-attack using calibration-based method
    Uses MP position as reference to find enemy HP bar
    Only considers valid if name matches targets (if targets list is provided)
    
    Args:
        hwnd: Window handle
        targets: Optional list of target mob names to attack (if None, attack all)
        
    Returns:
        dict: {'found': bool, 'hp': float, 'position': tuple or None, 'name': str or None, 'ocr_text': str or None}
    """
    if not config.calibrator or config.calibrator.mp_position is None:
        return {'found': False, 'hp': 0.0, 'position': None, 'name': None, 'ocr_text': None}
    
    try:
        # Capture screen
        screen = config.calibrator.capture_window(hwnd)
        if screen is None:
            return {'found': False, 'hp': 0.0, 'position': None, 'name': None, 'ocr_text': None}
        
        # Get MP position as reference
        mp_x, mp_y = config.calibrator.mp_position
        
        # Search area: 19 pixels below MP position, 163 pixels wide, 35 pixels tall
        search_y = mp_y + 19
        search_area = screen[search_y:search_y + 35, mp_x - 1:mp_x - 1 + 163]
        
        if search_area.size == 0 or search_area.shape[0] < 18:
            return {'found': False, 'hp': 0.0, 'position': None, 'name': None, 'ocr_text': None}
        
        # Extract enemy name area (first 18 pixels)
        name_area = search_area[0:18, :]
        
        # Save debug image of name area
        debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'debug')
        if not os.path.exists(debug_dir):
            os.makedirs(debug_dir)
        cv2.imwrite(os.path.join(debug_dir, 'enemy_name_area_debug.png'), name_area)
        
        # Extract enemy name using OCR (always extract, even if no HP bar found)
        import mob_detection
        detected_name, ocr_text = mob_detection.extract_enemy_name_easyocr(name_area)
        
        # Check for special mobs to avoid (e.g., "Avara Kara")
        if detected_name:
            detected_name_normalized = mob_detection.normalize_text(detected_name)
            if 'avara kara' in detected_name_normalized or 'avara' in detected_name_normalized:
                print(f'[TARGET] Enemy detected \'{detected_name}\' contains Avara. Avoiding attack.')
                return {'found': False, 'hp': 0.0, 'position': None, 'name': detected_name, 'ocr_text': ocr_text, 'avara_detected': True}
        
        # Check target list if provided (only attack if name matches targets)
        if targets and detected_name:
            detected_name_normalized = mob_detection.normalize_text(detected_name)
            similarities = []
            for target in targets:
                target_normalized = mob_detection.normalize_text(target)
                if mob_detection.contains_complete_word(target, detected_name):
                    similarity = 1.0
                else:
                    if abs(len(detected_name_normalized) - len(target_normalized)) <= 2:
                        similarity = mob_detection.calculate_similarity(detected_name_normalized, target_normalized) if target_normalized else 0
                    else:
                        similarity = 0
                similarities.append(similarity)
            
            max_similarity = max(similarities) if similarities else 0
            
            # Save debug image with target comparison
            debug_img = search_area.copy()
            cv2.putText(debug_img, f'OCR: {detected_name}', (2, 13), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1, cv2.LINE_AA)
            for idx, target in enumerate(targets):
                cv2.putText(debug_img, f'Target{idx + 1}: {target}', (2, 25 + 12 * idx), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 0, 0), 1, cv2.LINE_AA)
                cv2.putText(debug_img, f'Sim{idx + 1}: {similarities[idx]:.2f}', (2, 35 + 12 * idx), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 0, 0), 1, cv2.LINE_AA)
            cv2.imwrite(os.path.join(debug_dir, 'enemy_hp_search_area_ocr_targets.png'), debug_img)
            
            if max_similarity < 0.7:
                print(f'[TARGET] Detected name \'{detected_name_normalized}\' does not match (similarity {max_similarity:.2f}) with targets {targets}. Ignoring enemy.')
                return {'found': False, 'hp': 0.0, 'position': None, 'name': detected_name, 'ocr_text': ocr_text}
        
        # Convert to HSV for better red detection
        hsv = cv2.cvtColor(search_area, cv2.COLOR_BGR2HSV)
        
        # Red color ranges in HSV
        lower_red1 = np.array([0, 100, 100])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([160, 100, 100])
        upper_red2 = np.array([180, 255, 255])
        
        # Create masks for red detection
        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        mask = cv2.bitwise_or(mask1, mask2)
        
        # Save debug images
        cv2.imwrite(os.path.join(debug_dir, 'enemy_hp_mask_red.png'), mask)
        cv2.imwrite(os.path.join(debug_dir, 'enemy_hp_search_area.png'), search_area)
        
        # Find the widest red bar (18 pixels height)
        best_y = None
        best_width = 0
        best_first = 0
        best_last = 0
        
        for y in range(0, search_area.shape[0] - 18 + 1):
            # Extract 18-pixel high strip
            strip = mask[y:y + 18, :]
            # Count red pixels per column
            column_sum = np.sum(strip == 255, axis=0)
            # Columns with at least 6 red pixels are valid
            valid_columns = np.where(column_sum >= 6)[0]
            
            if len(valid_columns) > 0:
                first = valid_columns[0]
                last = valid_columns[-1]
                width = last - first + 1
                
                # Keep track of widest bar found
                if width > best_width:
                    best_width = width
                    best_y = y
                    best_first = first
                    best_last = last
        
        # If we found a red bar, calculate HP percentage
        if best_y is not None and best_width > 0:
            enemy_x = mp_x - 1 + best_first
            enemy_y = search_y + best_y + 9
            position = (enemy_x, enemy_y)
            
            # Calculate percentage: bar width / total search width (163) * 100
            hp_percentage = best_width / 163 * 100
            hp_percentage = float(max(0, min(100, hp_percentage)))
            
            # Save debug image of found bar
            bar_found = search_area[best_y + 9:best_y + 9 + 18, best_first:best_last + 1]
            cv2.imwrite(os.path.join(debug_dir, f'enemy_hp_bar_found_{enemy_x}_{enemy_y}.png'), bar_found)
            
            return {
                'found': True,
                'hp': hp_percentage,
                'position': position,
                'name': detected_name,
                'ocr_text': ocr_text
            }
        else:
            return {'found': False, 'hp': 0.0, 'position': None, 'name': detected_name, 'ocr_text': ocr_text}
            
    except Exception as e:
        print(f"[Enemy HP Detection] Error: {e}")
        return {'found': False, 'hp': 0.0, 'position': None, 'name': None, 'ocr_text': None}


def check_enemy_for_auto_attack():
    """Check enemy HP bar and update GUI display, auto-target when no target"""
    if not config.connected_window:
        return
    
    current_time = time.time()
    if current_time - config.last_enemy_hp_capture_time < config.ENEMY_HP_CAPTURE_INTERVAL:
        return
    
    config.last_enemy_hp_capture_time = current_time
    
    # Track last target search time (2.0 second interval)
    if not hasattr(check_enemy_for_auto_attack, 'last_target_search_time'):
        check_enemy_for_auto_attack.last_target_search_time = 0
    
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
        # Reset unstuck tracking
        config.enemy_hp_stagnant_time = 0
        config.last_enemy_hp_before_stagnant = None
        config.last_mob_verification_time = 0
        # Ensure UI enemy HP resets immediately
        config.current_enemy_hp_percentage = 0.0
        config.current_target_mob = None
        config.current_enemy_name = None
    
    def send_target_key_with_mob_check(recursion_depth=0):
        if recursion_depth >= 5:
            print(f"[Mob Filter] Max retries reached, stopping retarget loop")
            return False
        
        input_handler.send_input(config.action_slots['target']['key'])
        
        # Delay to ensure mob name appears after targeting
        delay = 0.15 if recursion_depth > 0 else 0.1
        time.sleep(delay)
        
        previous_mob = config.current_target_mob
        detected_mob = None
        max_retries = 6  # Increased retries for more reliable detection
        retry_delay = 0.15  # Slightly increased retry delay
        
        # Use reusable function to detect and verify mob after retarget
        mob_result = mob_detection.detect_and_verify_mob_after_target(delay=delay, retry_delay=retry_delay)
        detected_mob = mob_result['name']
        
        # Check if mob needs retargeting (not in target list)
        if mob_result['needs_retarget']:
            print(f"[Mob Filter] Skipping mob: {detected_mob} (not in target list, retry {recursion_depth + 1}/5)")
            reset_enemy_state()
            config.current_target_mob = None
            config.current_enemy_name = None
            time.sleep(0.25)  # Slightly longer delay before retargeting
            print(f"[Mob Filter] Retargeting to find target mob")
            return send_target_key_with_mob_check(recursion_depth + 1)
        
        return False
    
    def try_auto_target(reason=""):
        # Don't auto-target if we're currently looting (item names appear in same location as enemy names)
        if config.is_looting:
            return False
        
        if config.auto_attack_enabled:
            send_target_key_with_mob_check()
            if reason:
                print(f"Auto-targeting ({reason})")
            return True
        return False
    
    # Require calibration to be available
    if not config.calibrator or config.calibrator.mp_position is None:
        # Store 0.0 in config when calibration not available
        config.current_enemy_hp_percentage = 0.0
        return
    
    try:
        hwnd = config.connected_window.handle
        enemy_hp_percentage = 0.0
        
        # Use calibration-based detection (includes enemy name extraction)
        # Pass target list if mob detection is enabled
        targets = config.mob_target_list if (config.mob_detection_enabled and config.mob_target_list) else None
        result = detect_enemy_for_auto_attack(hwnd, targets=targets)
        if result['found']:
            raw_enemy_hp_percentage = result['hp']
            has_red_bar = True
            # Update current target mob with detected name from calibration
            if result.get('name'):
                config.current_target_mob = result['name']
                config.last_mob_detection_time = current_time
        else:
            has_red_bar = False
            raw_enemy_hp_percentage = 0.0
        
        if not has_red_bar:
            if len(config.enemy_hp_readings) > 0 or config.enemy_target_time > 0:
                # Enemy was killed - immediately retarget (bypass search interval)
                bot_logic.smart_loot()
                reset_enemy_state()
                # Reset target search time to allow immediate retargeting
                check_enemy_for_auto_attack.last_target_search_time = 0
                # Immediately retarget after enemy death
                if not config.is_looting:
                    try_auto_target("enemy killed")
                return
            
            reset_enemy_state()
            # Only try auto-targeting if not looting and interval has passed (2.0 second interval)
            # When no enemy is found, wait 2.0 seconds between searches
            if not config.is_looting:
                if current_time - check_enemy_for_auto_attack.last_target_search_time >= config.TARGET_SEARCH_INTERVAL:
                    try_auto_target("no enemy detected")
                    check_enemy_for_auto_attack.last_target_search_time = current_time
        else:
            # Process enemy HP percentage from calibration-based detection
            if config.enemy_hp_readings:
                last_avg = sum(config.enemy_hp_readings) / len(config.enemy_hp_readings)
                if last_avg < 50 and raw_enemy_hp_percentage >= 95:
                    enemy_hp_percentage = 0.0
                    reset_enemy_state()
                    bot_logic.smart_loot()
                    # Immediately retarget after enemy death - bypass search interval
                    check_enemy_for_auto_attack.last_target_search_time = 0
                    try_auto_target("enemy died")
                else:
                    config.enemy_hp_readings.append(raw_enemy_hp_percentage)
                    if len(config.enemy_hp_readings) > config.HP_MP_SMOOTHING_WINDOW:
                        config.enemy_hp_readings.pop(0)
                    enemy_hp_percentage = sum(config.enemy_hp_readings) / len(config.enemy_hp_readings)
                    
                    # Check for HP changes to reset unstuck timer (HP difference > 5.0)
                    if config.last_enemy_hp_before_stagnant is not None:
                        hp_difference = abs(enemy_hp_percentage - config.last_enemy_hp_before_stagnant)
                        if hp_difference > 5.0:
                            # HP changed significantly - reset stagnant timer
                            config.enemy_hp_stagnant_time = current_time
                            config.last_enemy_hp_before_stagnant = enemy_hp_percentage
                        else:
                            # HP changed minimally - update HP but keep timer running
                            config.last_enemy_hp_before_stagnant = enemy_hp_percentage
                    else:
                        # Initialize stagnant tracking
                        config.enemy_hp_stagnant_time = current_time
                        config.last_enemy_hp_before_stagnant = enemy_hp_percentage
                    
                    # Periodic mob verification during combat to catch non-target mobs
                    if config.mob_detection_enabled and config.mob_target_list and config.enemy_target_time > 0:
                        # Check mob every 2 seconds during combat
                        if current_time - config.last_mob_verification_time > 2.0:
                            config.last_mob_verification_time = current_time
                            # Use name from calibration-based detection
                            detected_mob = result.get('name')
                            if detected_mob:
                                config.current_target_mob = detected_mob
                                config.current_enemy_name = detected_mob
                                config.last_mob_detection_time = current_time
                                if not mob_detection.should_target_current_mob():
                                    print(f"[Mob Filter] Detected non-target mob during combat: {detected_mob} - retargeting")
                                    reset_enemy_state()
                                    time.sleep(0.2)
                                    try_auto_target("non-target mob detected during combat")
                                    return
                    
                    if raw_enemy_hp_percentage <= 3.0 and config.enemy_target_time > 0 and len(config.enemy_hp_readings) > 1:
                        previous_readings = config.enemy_hp_readings[:-1]
                        if previous_readings and max(previous_readings) > 10.0:
                            print(f"Enemy HP dropped from {max(previous_readings):.1f}% to {raw_enemy_hp_percentage:.1f}% - triggering smart loot")
                            bot_logic.smart_loot()
                            enemy_hp_percentage = 0.0
                            reset_enemy_state()
                            # Immediately retarget after enemy death - bypass search interval
                            check_enemy_for_auto_attack.last_target_search_time = 0
                            try_auto_target("enemy died")
                            return
            else:
                config.enemy_hp_readings.append(raw_enemy_hp_percentage)
                enemy_hp_percentage = raw_enemy_hp_percentage
            
            if enemy_hp_percentage > 0:
                # When enemy is found, reset target search time to allow continuous checking
                # If enemy found, check continuously without waiting
                check_enemy_for_auto_attack.last_target_search_time = 0
                
                if config.enemy_target_time == 0:
                    config.enemy_target_time = current_time
                    config.last_unstuck_check_time = 0  # Reset unstuck check interval to allow immediate damage detection
                    config.last_enemy_hp_for_unstuck = None  # Reset HP tracking for new enemy
                    config.last_damage_detected_time = current_time  # Reset damage detection timer for new target
                    # Reset unstuck tracking for new enemy
                    config.enemy_hp_stagnant_time = current_time
                    config.last_enemy_hp_before_stagnant = enemy_hp_percentage
                    
                    # Verify mob detection after targeting to ensure we have the correct mob name
                    if config.mob_detection_enabled:
                        # Use name from calibration-based detection
                        detected_mob = result.get('name')
                        if detected_mob:
                            config.current_target_mob = detected_mob
                            config.current_enemy_name = detected_mob
                            config.last_mob_detection_time = current_time
                            if config.mob_target_list and not mob_detection.should_target_current_mob():
                                print(f"[Mob Filter] Detected non-target mob after targeting: {detected_mob} - retargeting")
                                reset_enemy_state()
                                time.sleep(0.2)
                                try_auto_target("non-target mob detected")
                                return
                    
                    print(f"Enemy targeted")
        
        # Store enemy HP percentage in config for GUI to read (similar to HP/MP pattern)
        config.current_enemy_hp_percentage = enemy_hp_percentage
        
    except Exception as e:
        current_time = time.time()
        if current_time - config.last_enemy_hp_log_time >= config.HP_MP_LOG_INTERVAL:
            print(f"Error capturing enemy HP bar: {e}")
            config.last_enemy_hp_log_time = current_time
        # Store 0.0 in config when error occurs
        config.current_enemy_hp_percentage = 0.0
