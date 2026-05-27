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
    """
    Smart loot function - triggers looting when enemy is killed with multiple attempts.
    Improved version with better timing, more attempts, and delayed start to ensure loot appears.
    """
    try:
        current_time = time.time()
        
        # Check if already looting to prevent duplicate calls
        # Only skip if we're still actively looting (not just based on time)
        if config.is_looting and (current_time - config.looting_start_time) < config.LOOTING_DURATION:
            print(f"[Smart Loot] Skipped - already looting (started {current_time - config.looting_start_time:.2f}s ago)")
            return
        
        # Check if pick action is enabled
        if not config.action_slots['pick']['enabled']:
            print("[Smart Loot] Skipped - pick action not enabled")
            return
        
        action_key = config.action_slots['pick']['key']
        if not action_key:
            print("[Smart Loot] Skipped - no pick key configured")
            return
        
        # Update last loot time immediately to prevent duplicate calls
        config.last_smart_loot_time = current_time
        
        # Set looting flag to prevent auto-targeting during looting
        config.is_looting = True
        config.looting_start_time = current_time
        
        print(f"[Smart Loot] Starting loot sequence (key: {action_key})")
        
        # No initial delay - loot immediately after kill detection
        # Multiple loot attempts with minimal delays to ensure items are picked up
        num_attempts = 4
        attempt_delay = 0.1  # Reduced delay between attempts for faster looting
        
        for attempt in range(num_attempts):
            input_handler.send_input(action_key)
            if attempt < num_attempts - 1:  # Don't sleep after last attempt
                time.sleep(attempt_delay)
        
        print(f"[Smart Loot] Completed ({num_attempts} attempts)")

        # Loot sequence is done; allow auto-targeting again immediately.
        # (Auto-attack callers often retarget right after smart_loot() returns.)
        config.is_looting = False

    except Exception as e:
        print(f"[Smart Loot] Error: {e}")
        import traceback
        traceback.print_exc()
        # Reset flags on error
        config.is_looting = False
        # Note: is_looting flag will be cleared by check_auto_attack after LOOTING_DURATION


def _extract_buff_active_area(screen, origin):
    """Crop the active-buffs strip from a cached frame."""
    import frame_cache
    if screen is None:
        return None
    sys_msg_x = config.system_message_area.get('x', 0)
    sys_msg_y = config.system_message_area.get('y', 0)
    sys_msg_width = config.system_message_area.get('width', 0)
    sys_msg_height = config.system_message_area.get('height', 0)
    if sys_msg_width <= 0 or sys_msg_height <= 0:
        return None

    fh, fw = screen.shape[:2]
    full_h = fh + origin[1]
    full_w = fw + origin[0]
    half_width = sys_msg_width // 2
    half_height = sys_msg_height // 2
    sys_msg_left = sys_msg_x - half_width
    sys_msg_right = sys_msg_x + half_width
    sys_msg_top = sys_msg_y - half_height
    sys_msg_left = max(0, min(full_w, sys_msg_left))
    sys_msg_right = max(0, min(full_w, sys_msg_right))
    sys_msg_top = max(0, min(full_h, sys_msg_top))
    buff_height_start = max(0, sys_msg_top - 44)
    buff_height_end = sys_msg_top - 4
    buff_width_start = sys_msg_left - 14
    buff_width_end = sys_msg_right + 10
    if (buff_height_start < 0 or buff_height_end > full_h
            or buff_width_start < 0 or buff_width_end > full_w
            or buff_height_start >= buff_height_end
            or buff_width_start >= buff_width_end):
        return None
    return frame_cache.crop_rect(
        screen,
        buff_width_start, buff_height_start,
        buff_width_end, buff_height_end,
        origin,
    )


def check_buffs():
    """Check and activate buffs if needed (image recognition — same in all modes)."""
    if not config.buffs_manager or not config.calibrator:
        return

    buffs_configured = any(
        config.buffs_config[i]['image_path'] and config.buffs_config[i]['enabled']
        for i in range(8)
    )
    if not buffs_configured:
        return

    if not config.system_message_area or config.system_message_area.get('width', 0) <= 0:
        return
    if not config.area_skills:
        return

    current_time = time.time()
    if not hasattr(check_buffs, 'last_check_time'):
        check_buffs.last_check_time = 0
    buff_interval = config.get_buff_check_interval()
    if current_time - check_buffs.last_check_time < buff_interval:
        return
    check_buffs.last_check_time = current_time

    try:
        if hasattr(config.connected_window, 'handle'):
            hwnd = config.connected_window.handle
        else:
            hwnd = config.connected_window

        import frame_cache
        screen = frame_cache.get_frame(hwnd, config.calibrator)
        if screen is None:
            return
        origin = frame_cache.get_origin()
        area_buffs_activos = _extract_buff_active_area(screen, origin)
        if area_buffs_activos is None:
            return

        x1, y1, x2, y2 = config.area_skills
        area_skills = frame_cache.crop_rect(screen, x1, y1, x2, y2, origin)
        if area_skills is None:
            return
        config.buffs_manager.update_and_activate_buffs(
            hwnd, screen, area_skills, area_buffs_activos,
            x1, y1, run_active=config.bot_running)
    except Exception as e:
        print(f"[Buffs] Error checking buffs: {e}")
        import traceback
        traceback.print_exc()


def check_skill_sequence():
    """Check and execute skill sequence if needed"""
    # Note: This function is kept for compatibility but skill sequence is now
    # executed from auto_attack.py when enemy is found
    # Skill sequence should only execute when enemy is found, not independently
    pass


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
                # Only check if features are enabled to avoid unnecessary work
                if config.auto_hp_enabled or config.auto_mp_enabled:
                    autopots.check_auto_pots()
                # Only check buffs if any are enabled and configured
                if (config.buffs_manager and 
                    any(config.buffs_config[i]['image_path'] and config.buffs_config[i]['enabled'] 
                        for i in range(8))):
                    check_buffs()  # High priority - check buffs early (has internal throttling)
                if config.auto_attack_enabled or config.assist_only_enabled:
                    auto_attack.check_auto_attack()
                
                # Check and click assist button if assist_only is enabled (spam assist button)
                if config.assist_only_enabled:
                    auto_attack.check_assist_key()
                
                if config.auto_change_target_enabled:
                    auto_unstuck.check_auto_unstuck()
                check_skill_slots()  # Lightweight - just checks intervals
                if config.auto_repair_enabled:
                    auto_repair.check_auto_repair()
                if config.mouse_clicker_enabled:
                    check_mouse_clicker()
            
        time.sleep(config.get_bot_loop_sleep())
    
    # Clean up when bot stops
    print("Bot loop stopped")
