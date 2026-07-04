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
import logger
import state
import mob_filter
import loot_helpers

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
        if mob_filter.is_active():
            hwnd = config.connected_window.handle if config.connected_window else None
            if not hwnd or not mob_filter.should_allow_combat(hwnd):
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
        if loot_helpers.should_skip_loot(current_time):
            return
        if not loot_helpers.can_start_loot():
            current_time = time.time()
            if (current_time - config.last_enemy_hp_log_time >=
                    config.HP_MP_LOG_INTERVAL):
                print(
                    "[Auto Attack] Smart loot skipped — enable Pick action "
                    "and assign a key in Action Slots"
                )
                config.last_enemy_hp_log_time = current_time
            return

        action_key = loot_helpers.begin_loot(current_time)
        num_attempts = 3
        attempt_delay = 0.05

        for attempt in range(num_attempts):
            input_handler.send_input(action_key)
            if attempt < num_attempts - 1:
                time.sleep(attempt_delay)

        # is_looting stays True until LOOTING_DURATION expires; check_auto_attack retargets then.

    except Exception as e:
        logger.error(f"Smart loot error: {e}", "Loot")
        config.is_looting = False


def _extract_buff_active_area(screen, origin):
    """Crop above system message when buff_area is not manually set."""
    import frame_cache
    import region_helpers

    if screen is None:
        return None
    derived = region_helpers.derive_buff_area_from_system_message(
        config.system_message_area,
    )
    if not derived:
        return None
    fh, fw = screen.shape[:2]
    full_h = fh + origin[1]
    full_w = fw + origin[0]
    x1 = max(0, min(full_w, derived['x']))
    y1 = max(0, min(full_h, derived['y']))
    x2 = max(0, min(full_w, derived['x'] + derived['width']))
    y2 = max(0, min(full_h, derived['y'] + derived['height']))
    if x1 >= x2 or y1 >= y2:
        return None
    return frame_cache.crop_rect(screen, x1, y1, x2, y2, origin)


def _crop_buff_active_area(screen, origin):
    """Crop the active-buffs strip from a cached frame."""
    if config.bar_area_configured(config.buff_area):
        import frame_cache
        a = config.buff_area
        return frame_cache.crop_rect(
            screen,
            a['x'], a['y'],
            a['x'] + a['width'], a['y'] + a['height'],
            origin,
        )
    return _extract_buff_active_area(screen, origin)


def _capture_buff_active_area(hwnd, screen, origin):
    """Crop buff strip from cache; fall back to direct capture when cache crop is empty."""
    import window_utils

    area = _crop_buff_active_area(screen, origin)
    if area is not None and area.size > 0 and window_utils.capture_has_content(area):
        return area

    if config.bar_area_configured(config.buff_area):
        a = config.buff_area
        direct = window_utils.capture_window_region_bgr(
            hwnd, a['x'], a['y'], a['width'], a['height'],
        )
        if direct is not None and direct.size > 0 and window_utils.capture_has_content(direct):
            return direct

    if area is not None and area.size > 0:
        return area
    return None


def check_buffs():
    """Check and activate buffs if needed (template match active strip, press hotkey)."""
    if not config.buffs_manager:
        return

    buffs_configured = any(
        config.buffs_config[i]['enabled']
        and (config.buffs_config[i].get('key') or config.buffs_config[i]['image_path'])
        for i in range(8)
    )
    if not buffs_configured:
        return

    has_active_area = (
        config.bar_area_configured(config.buff_area)
        or config.bar_area_configured(config.system_message_area)
    )
    if not has_active_area:
        return

    if mob_filter.is_active() and not mob_filter.should_allow_buffs():
        if config.buffs_manager:
            config.buffs_manager.end_buffing_session()
        return

    current_time = time.time()
    if not hasattr(check_buffs, 'last_check_time'):
        check_buffs.last_check_time = 0
    buff_interval = config.get_buff_check_interval()
    if config.is_buffing:
        buff_interval = min(buff_interval, 0.35)
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
        area_buffs_activos = _capture_buff_active_area(hwnd, screen, origin)
        if area_buffs_activos is None:
            return

        config.buffs_manager.manage_buffing_session(area_buffs_activos)
        config.buffs_manager.update_and_activate_buffs(
            hwnd, screen, None, area_buffs_activos,
            0, 0, run_active=config.bot_running)
        config.buffs_manager.manage_buffing_session(area_buffs_activos)
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
    config.is_buffing = False
    config.buffing_start_time = 0
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
    
    logger.info("All timers and smoothing buffers reset", "BotState")


def bot_loop():
    """Main bot loop that runs in a separate thread"""
    if config.autopots_instance is None:
        config.autopots_instance = auto_pots.AutoPots()
    autopots = config.autopots_instance
    
    # Track if we've done initial targeting
    initial_target_done = False
    
    while config.bot_running:
        bs = state.BotState(running=config.bot_running, is_looting=config.is_looting)
        vs = state.VisionState(connected_window=config.connected_window, calibrator=config.calibrator)
        cs = state.CombatState(auto_attack_enabled=config.auto_attack_enabled, assist_only_enabled=config.assist_only_enabled)

        if vs.connected_window:
            # Optional: pause vision when game isn't focused (disabled by default for alt-tab multitasking).
            if getattr(config, "pause_when_unfocused", False):
                try:
                    import win32gui
                    hwnd = vs.connected_window.handle
                    if win32gui.IsIconic(hwnd) or win32gui.GetForegroundWindow() != hwnd:
                        time.sleep(getattr(config, "unfocused_sleep_seconds", 0.6))
                        continue
                except Exception:
                    # If focus checks fail, continue normally.
                    pass

            if config.bot_regions_ready() or (
                vs.calibrator
                and vs.calibrator.hp_position is not None
                and vs.calibrator.mp_position is not None
            ):
                if mob_filter.is_active() and vs.connected_window and not config.is_looting and not config.is_buffing:
                    hwnd = vs.connected_window.handle
                    engaged = (
                        config.enemy_target_time > 0
                        or len(config.enemy_hp_readings) > 0
                        or (config.current_enemy_hp_percentage or 0) > 1.0
                    )
                    if not engaged:
                        mob_filter.clear_match()

                # Force initial auto-target on bot start if auto attack is enabled
                if (config.force_initial_target and cs.auto_attack_enabled and
                    not initial_target_done and not bs.is_looting):
                    # Small delay to ensure everything is initialized
                    time.sleep(0.2)
                    auto_attack._auto_target_manager.reset_search_timer()
                    auto_attack._auto_target_manager.try_auto_target("bot started")
                    initial_target_done = True
                    config.force_initial_target = False
                    logger.info("Forced initial auto-targeting", "BotStart")
                
                # High priority: Auto pots and buffs (buffs should be checked early for combat effectiveness)
                # Only check if features are enabled to avoid unnecessary work
                if config.auto_hp_enabled or config.auto_mp_enabled:
                    autopots.check_auto_pots()
                # Only check buffs if any are enabled and configured
                if (config.buffs_manager and 
                    any(config.buffs_config[i]['image_path'] and config.buffs_config[i]['enabled'] 
                        for i in range(8))):
                    check_buffs()  # High priority - check buffs early (has internal throttling)
                if cs.auto_attack_enabled or cs.assist_only_enabled:
                    auto_attack.check_auto_attack()
                
                # Check and click assist button if assist_only is enabled (spam assist button)
                if cs.assist_only_enabled:
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
    logger.info("Bot loop stopped", "Bot")
