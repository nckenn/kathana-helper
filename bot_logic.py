"""
Main bot logic - skill checking, action handling, and bot loop
"""
import time
import config
import input_handler
import mob_detection
import bar_detection
import auto_repair
import auto_unstuck


def check_skill_slots():
    """Check and trigger skill slots based on their intervals"""
    current_time = time.time()
    
    for slot_num, slot_data in config.skill_slots.items():
        if slot_data['enabled']:
            time_since_last = current_time - slot_data['last_used']
            if time_since_last >= slot_data['interval']:
                trigger_skill(slot_num)
                config.skill_slots[slot_num]['last_used'] = current_time


def trigger_skill(slot_num):
    """Trigger a skill for the specified slot number or function key"""
    try:
        # Always check mob filter before attacking - verify current mob is up to date
        if config.mob_detection_enabled:
            # Refresh mob detection if it's been a while since last detection
            current_time = time.time()
            if current_time - config.last_mob_detection_time > 0.5:
                detected_mob = mob_detection.detect_mob_name()
                if detected_mob:
                    config.current_target_mob = detected_mob
                    config.last_mob_detection_time = current_time
            
            if mob_detection.should_skip_current_mob():
                return
        
        if isinstance(slot_num, int):
            skill_key = str(slot_num)
        elif isinstance(slot_num, str) and slot_num.startswith('f'):
            skill_key = slot_num.lower()
        else:
            skill_key = str(slot_num)
        
        input_handler.send_input(skill_key)
        time.sleep(0.1)
        
    except Exception as e:
        print(f"Error triggering skill slot {slot_num}: {e}")


def check_action_slots():
    """Check and trigger action slots based on their intervals"""
    # Note: Auto loot (pick) is now handled by smart_loot() when enemy dies
    pass


def smart_loot():
    """Smart loot function - triggers looting when enemy is killed with multiple attempts"""
    try:
        current_time = time.time()
        if current_time - config.last_smart_loot_time < config.SMART_LOOT_COOLDOWN:
            return
        
        if not config.action_slots['pick']['enabled']:
            return
        
        action_key = config.action_slots['pick']['key']
        config.last_smart_loot_time = current_time
        
        # Set looting flag to prevent auto-targeting during looting
        config.is_looting = True
        config.looting_start_time = current_time
        
        # Multiple loot attempts with delays to ensure items are picked up
        # Sometimes loot appears slightly after enemy death, so we try multiple times
        num_attempts = 3
        attempt_delay = 0.2  # Delay between attempts
        
        for attempt in range(num_attempts):
            input_handler.send_input(action_key)
            if attempt < num_attempts - 1:  # Don't sleep after last attempt
                time.sleep(attempt_delay)
        
        print(f"Smart loot triggered ({num_attempts} attempts, key: {action_key})")
    except Exception as e:
        print(f"Error in smart loot: {e}")
        # Note: is_looting flag will be cleared by check_enemy_HP after LOOTING_DURATION


def check_mouse_clicker():
    """Check and trigger mouse clicker based on interval (anti-stuck)"""
    if not config.mouse_clicker_enabled:
        return
    
    current_time = time.time()
    time_since_last = current_time - config.mouse_clicker_last_used
    
    if time_since_last >= config.mouse_clicker_interval:
        input_handler.perform_mouse_click()
        config.mouse_clicker_last_used = current_time


def reset_bot_state():
    """Reset all bot state variables (called on bot start/stop)"""
    current_time = time.time()
    
    for slot_num in config.skill_slots:
        config.skill_slots[slot_num]['last_used'] = current_time
    
    for action_key in config.action_slots:
        config.action_slots[action_key]['last_used'] = current_time
    
    config.last_hp_capture_time = 0
    config.last_mp_capture_time = 0
    config.last_enemy_hp_capture_time = 0
    config.last_auto_target_time = 0
    config.enemy_target_time = 0
    config.last_mob_verification_time = 0
    config.last_damage_detected_time = 0
    config.last_damage_value = None
    config.last_enemy_hp_for_unstuck = None
    config.last_unstuck_check_time = 0
    config.last_hp_log_time = 0
    config.last_mp_log_time = 0
    config.last_mob_detection_time = 0
    config.current_target_mob = None
    config.mouse_clicker_last_used = 0
    config.last_smart_loot_time = 0
    config.is_looting = False
    config.looting_start_time = 0
    config.low_damage_count = 0
    config.last_repair_time = 0
    config.last_auto_repair_check_time = 0
    config.low_damage_timestamps = []
    
    config.hp_readings.clear()
    config.mp_readings.clear()
    config.enemy_hp_readings.clear()
    
    print("[BOT STATE] All timers and smoothing buffers reset")


def bot_loop():
    """Main bot loop that runs in a separate thread"""
    while config.bot_running:
        if config.connected_window:
            bar_detection.check_HP()
            bar_detection.check_MP()
            mob_detection.update_mob_display()
            bar_detection.check_enemy_HP()
            check_skill_slots()
            check_action_slots()
            
            if config.mouse_clicker_enabled:
                check_mouse_clicker()
            
            auto_repair.check_auto_repair()
            
            if config.auto_change_target_enabled:
                auto_unstuck.check_auto_unstuck()
        time.sleep(0.1)
    print("Bot loop stopped")
