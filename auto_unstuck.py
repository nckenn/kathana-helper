"""
Auto unstuck functionality - detects when character is stuck and unstucks
Detects stagnant enemy HP and executes movement sequence to unstick
"""
import time
import random
import math
import config
import input_handler
import auto_attack


# ============================================================================
# Constants
# ============================================================================

# HP tracking thresholds
HP_STAGNANT_THRESHOLD = 5.0  # HP difference threshold to reset stagnant timer

# Unstuck movement parameters
MOVEMENT_KEYS = ['w', 's', 'a', 'd']
MOVEMENT_COUNT_MIN = 4
MOVEMENT_COUNT_MAX = 5
MOVEMENT_HOLD_DURATION = 0.15  # Seconds to hold movement key
MOVEMENT_DELAY = 0.05  # Delay between movements

# Note: Retargeting parameters are now in auto_attack.py (RetargetManager)

# Display color thresholds (as percentage of timeout)
COLOR_SAFE_THRESHOLD = 0.5  # Green when > 50% remaining
COLOR_WARNING_THRESHOLD = 0.25  # Yellow when > 25% remaining, red otherwise


# ============================================================================
# Helper Classes
# ============================================================================

class UnstuckTimer:
    """Manages unstuck timer calculations"""
    
    @staticmethod
    def get_remaining_time(unstuck_timeout):
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
    
    @staticmethod
    def reset():
        """Reset the unstuck timer"""
        config.enemy_hp_stagnant_time = 0
        config.last_enemy_hp_before_stagnant = None


class HpStagnantTracker:
    """Tracks HP stagnation for unstuck detection"""
    
    @staticmethod
    def update_tracking(current_time, current_hp):
        """
        Update HP stagnant tracking
        Returns True if HP changed significantly (timer should reset)
        """
        if config.last_enemy_hp_before_stagnant is not None:
            hp_difference = abs(config.last_enemy_hp_before_stagnant - current_hp)
            if hp_difference > HP_STAGNANT_THRESHOLD:
                # Reset stagnant timer if HP changes significantly
                config.enemy_hp_stagnant_time = current_time
                config.last_enemy_hp_before_stagnant = current_hp
                return True
            else:
                # Update HP but keep timer running if change is minimal
                config.last_enemy_hp_before_stagnant = current_hp
                return False
        else:
            # Initialize stagnant tracking
            config.enemy_hp_stagnant_time = current_time
            config.last_enemy_hp_before_stagnant = current_hp
            return False
    
    @staticmethod
    def get_current_hp():
        """Get current HP from readings"""
        if config.enemy_hp_readings and len(config.enemy_hp_readings) > 0:
            return sum(config.enemy_hp_readings) / len(config.enemy_hp_readings)
        return None
    
    @staticmethod
    def is_stagnant(current_time):
        """Check if HP has been stagnant for the timeout period"""
        if (config.enemy_hp_stagnant_time > 0 and 
            config.last_enemy_hp_before_stagnant is not None):
            time_stagnant = current_time - config.enemy_hp_stagnant_time
            return time_stagnant >= config.unstuck_timeout, time_stagnant
        return False, 0.0


class UnstuckExecutor:
    """Handles unstuck movement execution"""
    
    @staticmethod
    def execute_movement_sequence():
        """Execute random movement sequence to unstick character"""
        num_movements = random.randint(MOVEMENT_COUNT_MIN, MOVEMENT_COUNT_MAX)
        
        for _ in range(num_movements):
            key = random.choice(MOVEMENT_KEYS)
            input_handler.send_movement_key(key, hold_duration=MOVEMENT_HOLD_DURATION)
            time.sleep(MOVEMENT_DELAY)
    
    @staticmethod
    def retarget_after_unstuck():
        """Retarget after unstuck and verify mob if needed (uses AutoTargetManager)"""
        # Reset skill sequence BEFORE retargeting (consistent with other retarget scenarios)
        # When unstuck happens, we're abandoning current combat state, so reset sequence first
        if config.skill_sequence_manager:
            config.skill_sequence_manager.reset_sequence()
            print("[Auto Unstuck] Skill sequence reset before retargeting")
        
        # Use try_auto_target for consistency with rest of codebase
        # It handles looting checks, auto-attack enabled checks, and uses RetargetManager internally
        auto_attack._auto_target_manager.try_auto_target("after unstuck")
    
    @staticmethod
    def execute_unstuck(current_hp, time_stagnant):
        """Execute complete unstuck sequence"""
        print(
            f"[Auto Unstuck] Enemy HP stagnant at {current_hp:.1f}% for "
            f"{time_stagnant:.1f}s (timeout: {config.unstuck_timeout}s) - Unstucking..."
        )
        
        # Execute movement sequence
        UnstuckExecutor.execute_movement_sequence()
        
        # Retarget after movement
        UnstuckExecutor.retarget_after_unstuck()
        
        print(f"[Auto Unstuck] Unstuck complete, retargeting")
        
        # Reset stagnant tracking AFTER unstuck completes
        config.enemy_hp_stagnant_time = time.time()
        config.last_enemy_hp_before_stagnant = None


class UnstuckDisplay:
    """Handles unstuck countdown display updates"""
    
    @staticmethod
    def get_color_for_remaining_time(remaining_time, unstuck_timeout):
        """Get color code based on remaining time"""
        if remaining_time > unstuck_timeout * COLOR_SAFE_THRESHOLD:
            return "green"
        elif remaining_time > unstuck_timeout * COLOR_WARNING_THRESHOLD:
            return "yellow"
        else:
            return "red"
    
    @staticmethod
    def update_display(current_time):
        """Update the unstuck countdown display in the GUI"""
        try:
            from gui import BotGUI
            from config import safe_update_gui
            
            if not hasattr(BotGUI, '_instance') or not BotGUI._instance:
                return
            
            gui = BotGUI._instance
            if not hasattr(gui, 'unstuck_countdown_label'):
                return
            
            # Check if auto unstuck is enabled
            if not config.auto_change_target_enabled:
                safe_update_gui(lambda: gui.unstuck_countdown_label.configure(
                    text="Unstuck: Disabled", 
                    text_color="gray"
                ))
                return
            
            # Get remaining time
            _, remaining_time = UnstuckTimer.get_remaining_time(config.unstuck_timeout)
            
            if (config.enemy_hp_stagnant_time == 0 or 
                config.last_enemy_hp_before_stagnant is None):
                # Not initialized or no target
                safe_update_gui(lambda: gui.unstuck_countdown_label.configure(
                    text="Unstuck: ---", 
                    text_color="gray"
                ))
            else:
                # Get color based on remaining time
                color = UnstuckDisplay.get_color_for_remaining_time(
                    remaining_time, config.unstuck_timeout
                )
                
                # Use ceil to round up so countdown doesn't jump
                # (e.g., 9.9s shows as 10s until it hits 9.0s)
                display_seconds = math.ceil(remaining_time)
                
                # Show "(no target)" indicator when there's no target but timer is running
                target_indicator = (
                    " (no target)" if config.enemy_target_time == 0 else ""
                )
                
                safe_update_gui(lambda: gui.unstuck_countdown_label.configure(
                    text=f"Unstuck: {display_seconds}s{target_indicator}",
                    text_color=color
                ))
        except Exception:
            pass  # Silently fail if GUI not available


# ============================================================================
# Main Functions
# ============================================================================

def get_unstuck_remaining_time(unstuck_timeout):
    """
    Get remaining unstuck time
    Returns (elapsed, remaining) in seconds
    """
    return UnstuckTimer.get_remaining_time(unstuck_timeout)


def update_unstuck_countdown_display(current_time):
    """Update the unstuck countdown display in the GUI"""
    UnstuckDisplay.update_display(current_time)


def check_auto_unstuck():
    """
    Check enemy HP for stagnant detection and trigger unstuck if HP is stagnant 
    for timeout period. Checks if HP change > 5% to reset timer, uses stagnant 
    HP time tracking.
    """
    # Early exit if disabled
    if not config.auto_change_target_enabled:
        update_unstuck_countdown_display(time.time())
        return
    
    if not config.auto_attack_enabled:
        UnstuckTimer.reset()
        update_unstuck_countdown_display(time.time())
        return
    
    current_time = time.time()
    
    # Throttle checks based on interval
    if current_time - config.last_unstuck_check_time < config.UNSTUCK_CHECK_INTERVAL:
        return
    
    config.last_unstuck_check_time = current_time
    
    # Update countdown display
    update_unstuck_countdown_display(current_time)
    
    # Only check for stagnant HP when we have a target and HP readings
    if (config.enemy_target_time > 0 and 
        config.enemy_hp_readings and 
        len(config.enemy_hp_readings) > 0):
        
        current_hp = HpStagnantTracker.get_current_hp()
        if current_hp is None:
            return
        
        # Update HP tracking
        HpStagnantTracker.update_tracking(current_time, current_hp)
        
        # Check if HP has been stagnant for the timeout period
        is_stagnant, time_stagnant = HpStagnantTracker.is_stagnant(current_time)
        
        if is_stagnant:
            # Execute unstuck sequence
            UnstuckExecutor.execute_unstuck(current_hp, time_stagnant)
            
            # Update display after unstuck
            update_unstuck_countdown_display(time.time())
