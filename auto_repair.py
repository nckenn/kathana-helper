"""
Auto repair functionality - monitors damage and triggers repair when needed
"""
import time
import config
import ocr_utils
import input_handler


def check_auto_repair():
    """Check system messages for 'is about to break' warning and trigger repair if detected 3 times"""
    if not config.auto_repair_enabled:
        return
    
    if not config.auto_attack_enabled:
        if config.low_damage_count > 0:
            config.low_damage_count = 0
            config.low_damage_timestamps.clear()
        return
    
    if config.system_message_area.get('width', 0) <= 0 or config.system_message_area.get('height', 0) <= 0:
        current_time = time.time()
        if not hasattr(check_auto_repair, 'last_warn_time'):
            check_auto_repair.last_warn_time = 0
        if current_time - check_auto_repair.last_warn_time > 30.0:
            print("[Auto Repair] System message area not calibrated! Please set it in Calibration Tool.")
            check_auto_repair.last_warn_time = current_time
        return
    
    current_time = time.time()
    if current_time - config.last_auto_repair_check_time < config.AUTO_REPAIR_CHECK_INTERVAL:
        return
    
    config.last_auto_repair_check_time = current_time
    
    # No time window - detections persist until repair is triggered
    config.low_damage_count = len(config.low_damage_timestamps)
    
    message_text = ocr_utils.read_system_message_ocr(debug_prefix="[Auto Repair]")
    
    if message_text:
        # Check for "is about to break" keyword instead of parsing damage
        break_warning_detected = ocr_utils.check_item_break_warning(message_text)
        
        if break_warning_detected:
            # Add timestamp for this detection (no time window filtering)
            config.low_damage_timestamps.append(current_time)
            config.low_damage_count = len(config.low_damage_timestamps)
            
            if not hasattr(check_auto_repair, 'last_log_time'):
                check_auto_repair.last_log_time = 0
            if current_time - check_auto_repair.last_log_time > 2.0:
                print(f"[Auto Repair] Item break warning detected (count: {config.low_damage_count}/3)")
                check_auto_repair.last_log_time = current_time
            
            # Trigger repair if detected 3 times (as requested)
            BREAK_WARNING_TRIGGER_COUNT = 3
            if config.low_damage_count >= BREAK_WARNING_TRIGGER_COUNT:
                if current_time - config.last_repair_time >= config.REPAIR_COOLDOWN:
                    input_handler.send_input('f10')
                    config.last_repair_time = current_time
                    print(f"[Auto Repair] REPAIR TRIGGERED (F10) - item break warning detected {config.low_damage_count} times!")
                    config.low_damage_count = 0
                    config.low_damage_timestamps.clear()
                else:
                    remaining_cooldown = config.REPAIR_COOLDOWN - (current_time - config.last_repair_time)
                    if not hasattr(check_auto_repair, 'last_cooldown_log_time'):
                        check_auto_repair.last_cooldown_log_time = 0
                    if current_time - check_auto_repair.last_cooldown_log_time > 5.0:
                        print(f"[Auto Repair] Repair on cooldown ({remaining_cooldown:.1f}s remaining)")
                        check_auto_repair.last_cooldown_log_time = current_time
