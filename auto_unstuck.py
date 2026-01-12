"""
Auto unstuck functionality - detects when character is stuck and unstucks
"""
import time
import random
import math
import config
import input_handler
import mob_detection


def update_unstuck_countdown_display(current_time):
    """Update the unstuck countdown display in the GUI"""
    try:
        from gui import BotGUI
        from config import safe_update_gui
        if hasattr(BotGUI, '_instance') and BotGUI._instance:
            gui = BotGUI._instance
            if hasattr(gui, 'unstuck_countdown_label'):
                if config.enemy_target_time == 0 or config.last_damage_detected_time == 0:
                    # No enemy targeted or not initialized
                    safe_update_gui(lambda: gui.unstuck_countdown_label.configure(text="Unstuck: ---", text_color="gray"))
                else:
                    time_since_last_damage = current_time - config.last_damage_detected_time
                    remaining_time = max(0, config.unstuck_timeout - time_since_last_damage)
                    
                    # Color coding: green when safe, yellow when warning, red when critical
                    if remaining_time > config.unstuck_timeout * 0.5:
                        color = "green"
                    elif remaining_time > config.unstuck_timeout * 0.25:
                        color = "yellow"
                    else:
                        color = "red"
                    
                    # Use ceil to round up so countdown doesn't jump (e.g., 9.9s shows as 10s until it hits 9.0s)
                    display_seconds = math.ceil(remaining_time)
                    safe_update_gui(lambda: gui.unstuck_countdown_label.configure(
                        text=f"Unstuck: {display_seconds}s",
                        text_color=color
                    ))
    except:
        pass


def check_auto_unstuck():
    """Check enemy HP for damage detection and trigger unstuck if no damage detected for timeout period"""
    if not config.auto_change_target_enabled:
        return
    
    if not config.auto_attack_enabled:
        config.last_damage_detected_time = 0
        config.last_enemy_hp_for_unstuck = None
        update_unstuck_countdown_display(time.time())
        return
    
    # Need an enemy targeted to check HP
    if config.enemy_target_time == 0:
        config.last_damage_detected_time = 0
        config.last_enemy_hp_for_unstuck = None
        update_unstuck_countdown_display(time.time())
        return
    
    current_time = time.time()
    if current_time - config.last_unstuck_check_time < config.UNSTUCK_CHECK_INTERVAL:
        return
    
    config.last_unstuck_check_time = current_time
    
    # Initialize damage detection time if not set
    if config.last_damage_detected_time == 0:
        config.last_damage_detected_time = current_time
        config.last_enemy_hp_for_unstuck = None
    
    # Update countdown display
    update_unstuck_countdown_display(current_time)
    
    # Check if enemy HP has decreased (indicating damage dealt)
    if config.enemy_hp_readings and len(config.enemy_hp_readings) > 0:
        current_hp = sum(config.enemy_hp_readings) / len(config.enemy_hp_readings)
        
        # If we have a previous HP reading and current HP is lower, damage was dealt
        if config.last_enemy_hp_for_unstuck is not None:
            hp_decrease = config.last_enemy_hp_for_unstuck - current_hp
            
            # Only consider it damage if HP decreased by at least 0.5% (to avoid false positives from minor fluctuations)
            if hp_decrease > 0.5:
                config.last_damage_detected_time = current_time
                update_unstuck_countdown_display(current_time)  # Update display immediately when damage detected
                if not hasattr(check_auto_unstuck, 'last_damage_log_time'):
                    check_auto_unstuck.last_damage_log_time = 0
                if current_time - check_auto_unstuck.last_damage_log_time > 5.0:
                    print(f"[Auto Unstuck] Enemy HP decreased from {config.last_enemy_hp_for_unstuck:.1f}% to {current_hp:.1f}% - unstuck timer reset")
                    check_auto_unstuck.last_damage_log_time = current_time
        
        # Update last HP value for next comparison
        config.last_enemy_hp_for_unstuck = current_hp
    else:
        # No HP readings available, reset tracking
        config.last_enemy_hp_for_unstuck = None
    
    if config.last_damage_detected_time > 0:
        time_since_last_damage = current_time - config.last_damage_detected_time
        if time_since_last_damage >= config.unstuck_timeout:
            print(f"[Auto Unstuck] No damage detected for {time_since_last_damage:.1f}s (timeout: {config.unstuck_timeout}s) - Unstucking...")
            config.last_damage_value = None
            config.last_enemy_hp_for_unstuck = None
            
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
            # Reset damage detection time AFTER unstuck completes to show full countdown
            config.last_damage_detected_time = time.time()
            update_unstuck_countdown_display(config.last_damage_detected_time)