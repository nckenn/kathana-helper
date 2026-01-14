"""
Auto unstuck functionality - detects when character is stuck and unstucks
"""
import time
import random
import math
import config
import input_handler
import mob_detection


def get_unstuck_remaining_time(unstuck_timeout):
    """
    Get remaining unstuck time
    Returns (elapsed, remaining) in seconds
    """
    if config.enemy_hp_stagnant_time == 0 or config.last_enemy_hp_before_stagnant is None:
        return (0.0, unstuck_timeout)
    
    current_time = time.time()
    elapsed = max(0.0, current_time - config.enemy_hp_stagnant_time)
    remaining = max(0.0, unstuck_timeout - elapsed)
    return (elapsed, remaining)


def update_unstuck_countdown_display(current_time):
    """Update the unstuck countdown display in the GUI"""
    try:
        from gui import BotGUI
        from config import safe_update_gui
        if hasattr(BotGUI, '_instance') and BotGUI._instance:
            gui = BotGUI._instance
            if hasattr(gui, 'unstuck_countdown_label'):
                # Check if auto unstuck is enabled
                if not config.auto_change_target_enabled:
                    safe_update_gui(lambda: gui.unstuck_countdown_label.configure(
                        text="Unstuck: Disabled", 
                        text_color="gray"
                    ))
                    return
                
                # Use stagnant HP time instead of damage detection time
                _, remaining_time = get_unstuck_remaining_time(config.unstuck_timeout)
                
                if config.enemy_hp_stagnant_time == 0 or config.last_enemy_hp_before_stagnant is None:
                    # Not initialized or no target
                    safe_update_gui(lambda: gui.unstuck_countdown_label.configure(text="Unstuck: ---", text_color="gray"))
                else:
                    # Color coding: green when safe, yellow when warning, red when critical
                    if remaining_time > config.unstuck_timeout * 0.5:
                        color = "green"
                    elif remaining_time > config.unstuck_timeout * 0.25:
                        color = "yellow"
                    else:
                        color = "red"
                    
                    # Use ceil to round up so countdown doesn't jump (e.g., 9.9s shows as 10s until it hits 9.0s)
                    display_seconds = math.ceil(remaining_time)
                    # Show "(no target)" indicator when there's no target but timer is running
                    target_indicator = " (no target)" if config.enemy_target_time == 0 else ""
                    safe_update_gui(lambda: gui.unstuck_countdown_label.configure(
                        text=f"Unstuck: {display_seconds}s{target_indicator}",
                        text_color=color
                    ))
    except:
        pass


def check_auto_unstuck():
    """
    Check enemy HP for stagnant detection and trigger unstuck if HP is stagnant for timeout period
    Checks if HP change > 5% to reset timer, uses stagnant HP time tracking
    """
    if not config.auto_change_target_enabled:
        # Update display to show disabled state
        update_unstuck_countdown_display(time.time())
        return
    
    if not config.auto_attack_enabled:
        config.enemy_hp_stagnant_time = 0
        config.last_enemy_hp_before_stagnant = None
        update_unstuck_countdown_display(time.time())
        return
    
    current_time = time.time()
    if current_time - config.last_unstuck_check_time < config.UNSTUCK_CHECK_INTERVAL:
        return
    
    config.last_unstuck_check_time = current_time
    
    # Update countdown display
    update_unstuck_countdown_display(current_time)
    
    # Only check for stagnant HP when we have a target and HP readings
    if config.enemy_target_time > 0 and config.enemy_hp_readings and len(config.enemy_hp_readings) > 0:
        current_hp = sum(config.enemy_hp_readings) / len(config.enemy_hp_readings)
        
        # Check if HP has been stagnant for the timeout period
        if config.enemy_hp_stagnant_time > 0 and config.last_enemy_hp_before_stagnant is not None:
            time_stagnant = current_time - config.enemy_hp_stagnant_time
            if time_stagnant >= config.unstuck_timeout:
                # HP has been stagnant for timeout period - execute unstuck
                print(f"[Auto Unstuck] Enemy HP stagnant at {current_hp:.1f}% for {time_stagnant:.1f}s (timeout: {config.unstuck_timeout}s) - Unstucking...")
                
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
                    
                    if config.mob_detection_enabled and config.mob_target_list:
                        # Use reusable function to detect and verify mob after retarget
                        mob_result = mob_detection.detect_and_verify_mob_after_target(delay=0.15, retry_delay=0.1)
                        
                        if mob_result['needs_retarget']:
                            print(f"[Mob Filter] Skipping mob after unstuck: {mob_result['name']} (not in target list)")
                            time.sleep(0.1)
                            input_handler.send_input(target_key)
                            config.last_auto_target_time = current_time
                
                print(f"[Auto Unstuck] Unstuck complete, retargeting")
                # Reset stagnant tracking AFTER unstuck completes
                config.enemy_hp_stagnant_time = time.time()
                config.last_enemy_hp_before_stagnant = None
                update_unstuck_countdown_display(time.time())