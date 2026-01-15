"""
Main bot logic - skill checking, action handling, and bot loop
"""
import time
import config
import input_handler
import auto_attack
import auto_repair
import auto_unstuck
import auto_pots

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
            # Use current enemy name from config (updated by auto_attack via calibration)
            if not auto_attack.should_target_current_mob():
                return
        
        if isinstance(slot_num, int):
            skill_key = str(slot_num)
        elif isinstance(slot_num, str) and slot_num.startswith('f'):
            skill_key = slot_num.lower()
        else:
            skill_key = str(slot_num)
        
        # Send input immediately - no blocking delay (input handler manages timing internally)
        input_handler.send_input(skill_key)
        
    except Exception as e:
        print(f"Error triggering skill slot {slot_num}: {e}")


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
        # Note: is_looting flag will be cleared by check_enemy_for_auto_attack after LOOTING_DURATION


def check_buffs():
    """Check and activate buffs if needed"""
    if not config.buffs_manager or not config.calibrator:
        return
    
    # Check if any enabled buffs are configured (have image paths and are enabled)
    buffs_configured = any(
        config.buffs_config[i]['image_path'] and config.buffs_config[i]['enabled'] 
        for i in range(8)
    )
    if not buffs_configured:
        return
    
    # Check if skill bars are calibrated
    if (not config.calibrator.skills_bar1_position or 
        not config.calibrator.skills_bar2_position):
        return
    
    try:
        import cv2
        import os
        
        # Get window handle
        if hasattr(config.connected_window, 'handle'):
            hwnd = config.connected_window.handle
        else:
            hwnd = config.connected_window
        
        # Capture screen
        screen = config.calibrator.capture_window(hwnd)
        if screen is not None:
            # Extract area_skills from stored coordinates
            x_min, y_min, x_max, y_max = config.area_skills
            
            # Ensure coordinates are within screen bounds
            h, w = screen.shape[:2]
            if (x_min >= 0 and y_min >= 0 and x_max <= w and y_max <= h):
                area_skills = screen[y_min:y_max, x_min:x_max]
                
                # Calculate area_buffs_activos (40 pixels above skills area)
                buff_height_start = max(0, y_min - 40)
                buff_height_end = y_min
                buff_width_start = x_min
                buff_width_end = x_max
                
                if (buff_height_start >= 0 and buff_height_end <= h and
                    buff_width_start >= 0 and buff_width_end <= w and
                    buff_height_start < buff_height_end):
                    area_buffs_activos = screen[buff_height_start:buff_height_end, buff_width_start:buff_width_end]
                    
                    # Call buffs manager update
                    config.buffs_manager.update_and_activate_buffs(
                        hwnd, screen, area_skills, area_buffs_activos, 
                        x_min, y_min, run_active=config.bot_running
                    )
    except Exception as e:
        print(f"[Buffs] Error checking buffs: {e}")
        import traceback
        traceback.print_exc()


def check_skill_sequence():
    """Check and execute skill sequence if needed"""
    if not config.skill_sequence_manager or not config.calibrator:
        return
    
    # Check if any enabled skills are configured (have image paths and are enabled)
    skills_configured = any(
        config.skill_sequence_config[i].get('image_path') and config.skill_sequence_config[i]['enabled'] 
        for i in range(8)
    )
    if not skills_configured:
        return
    
    # Check if skill bars are calibrated
    if not config.area_skills:
        return
    
    try:
        import cv2
        import os
        
        # Get window handle
        if hasattr(config.connected_window, 'handle'):
            hwnd = config.connected_window.handle
        else:
            hwnd = config.connected_window
        
        # Capture screen
        screen = config.calibrator.capture_window(hwnd)
        if screen is not None:
            # Call skill sequence manager to execute sequence
            config.skill_sequence_manager.execute_skill_sequence(
                hwnd, screen, config.area_skills, run_active=config.bot_running
            )
    except Exception as e:
        print(f"[SkillSequence] Error checking skill sequence: {e}")
        import traceback
        traceback.print_exc()


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
    config.last_repair_time = 0
    config.last_auto_repair_check_time = 0
    
    config.hp_readings.clear()
    config.mp_readings.clear()
    config.enemy_hp_readings.clear()
    
    # Reset skill sequence state
    if config.skill_sequence_manager:
        config.skill_sequence_manager.reset_sequence()
    
    # Set flag to force initial auto-target on bot start (if auto attack enabled)
    config.force_initial_target = config.auto_attack_enabled
    
    print("[BOT STATE] All timers and smoothing buffers reset")


def bot_loop():
    """Main bot loop that runs in a separate thread"""
    if config.autopots_instance is None:
        config.autopots_instance = auto_pots.AutoPots()
    autopots = config.autopots_instance
    
    # Track if we've done initial targeting
    initial_target_done = False
    
    while config.bot_running:
        if config.connected_window:
            if config.calibrator and config.calibrator.hp_position is not None and config.calibrator.mp_position is not None:
                # Force initial auto-target on bot start if auto attack is enabled
                if (config.force_initial_target and config.auto_attack_enabled and 
                    not initial_target_done and not config.is_looting):
                    # Small delay to ensure everything is initialized
                    time.sleep(0.2)
                    auto_attack._auto_target_manager.reset_search_timer()
                    auto_attack._auto_target_manager.try_auto_target("bot started")
                    initial_target_done = True
                    config.force_initial_target = False
                    print("[Bot Start] Forced initial auto-targeting")
                
                # High priority: Auto pots and buffs (buffs should be checked early for combat effectiveness)
                autopots.check_auto_pots()
                check_buffs()  # High priority - check buffs early
                # Skill sequence is now executed inside check_auto_attack when enemy is found
                auto_attack.check_auto_attack()
                auto_unstuck.check_auto_unstuck()
                check_skill_slots()
                auto_repair.check_auto_repair()
                check_mouse_clicker()
            
        time.sleep(0.1)
    
    # Clean up when bot stops
    print("Bot loop stopped")
