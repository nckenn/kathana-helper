"""
Auto unstuck functionality - detects when character is stuck and unstucks
"""
import time
import random
import config
import ocr_utils
import input_handler
import mob_detection


def check_auto_unstuck():
    """Check system messages for damage detection and trigger unstuck if no damage detected for timeout period"""
    if not config.auto_change_target_enabled:
        return
    
    if not config.auto_attack_enabled:
        config.last_damage_detected_time = 0
        config.last_damage_value = None
        return
    
    if config.system_message_area.get('width', 0) <= 0 or config.system_message_area.get('height', 0) <= 0:
        current_time = time.time()
        if not hasattr(check_auto_unstuck, 'last_warn_time'):
            check_auto_unstuck.last_warn_time = 0
        if current_time - check_auto_unstuck.last_warn_time > 30.0:
            print("[Auto Unstuck] System message area not calibrated! Please set it in Calibration Tool.")
            check_auto_unstuck.last_warn_time = current_time
        return
    
    current_time = time.time()
    if current_time - config.last_unstuck_check_time < config.UNSTUCK_CHECK_INTERVAL:
        return
    
    config.last_unstuck_check_time = current_time
    
    if config.last_damage_detected_time == 0:
        config.last_damage_detected_time = current_time
        config.last_damage_value = None
    
    message_text = ocr_utils.read_system_message_ocr(debug_prefix="[Auto Unstuck]")
    
    if message_text:
        damage = ocr_utils.parse_damage_from_message(message_text)
        
        if damage is not None:
            if config.last_damage_value is None or damage != config.last_damage_value:
                config.last_damage_detected_time = current_time
                config.last_damage_value = damage
                if not hasattr(check_auto_unstuck, 'last_damage_log_time'):
                    check_auto_unstuck.last_damage_log_time = 0
                if current_time - check_auto_unstuck.last_damage_log_time > 5.0:
                    print(f"[Auto Unstuck] New damage detected: {damage} (previous: {config.last_damage_value}) - unstuck timer reset")
                    check_auto_unstuck.last_damage_log_time = current_time
    
    if config.last_damage_detected_time > 0:
        time_since_last_damage = current_time - config.last_damage_detected_time
        if time_since_last_damage >= config.unstuck_timeout:
            print(f"[Auto Unstuck] No damage detected for {time_since_last_damage:.1f}s (timeout: {config.unstuck_timeout}s) - Unstucking...")
            config.last_damage_detected_time = current_time
            config.last_damage_value = None
            
            movement_keys = ['w', 's', 'a', 'd']
            num_movements = random.randint(4, 5)
            for _ in range(num_movements):
                key = random.choice(movement_keys)
                input_handler.send_movement_key(key, hold_duration=0.15)
                time.sleep(0.05)
            
            if config.auto_attack_enabled:
                target_key = config.action_slots['target']['key']
                input_handler.send_input(target_key)
                config.last_auto_target_time = current_time
                
                if config.mob_detection_enabled and config.mob_skip_list:
                    time.sleep(0.15)
                    detected_mob = mob_detection.detect_mob_name()
                    if detected_mob:
                        config.current_target_mob = detected_mob
                        if mob_detection.should_skip_current_mob():
                            print(f"[Mob Filter] Skipping mob after unstuck: {detected_mob}")
                            time.sleep(0.1)
                            input_handler.send_input(target_key)
                            config.last_auto_target_time = current_time
            print(f"[Auto Unstuck] Unstuck complete, retargeting")
