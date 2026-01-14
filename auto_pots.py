"""
Auto-pots module for automatically using potions when HP/MP is low
Based on the decompiled Autopots.py functionality
"""
import time
import random
import config
import input_handler


class AutoPots:
    """Handles automatic potion usage when HP/MP drops below thresholds"""
    
    def __init__(self):
        """Initialize the AutoPots system"""
        self.last_hp_pot_time = 0
        self.last_mp_pot_time = 0
        self.pot_cooldown = 0.5  # Minimum time between pot uses (seconds)
        self.last_rohati_heal_time = 0
        self.rohati_heal_cooldown = 3.0
    
    def check_and_use_pots(self, hwnd, hp_percent, mp_percent, hp_threshold, mp_threshold, use_rohati_heal=False):
        """
        Check HP/MP percentages and use potions if necessary
        
        Args:
            hwnd: Window handle of the game
            hp_percent: Current HP percentage
            mp_percent: Current MP percentage
            hp_threshold: HP threshold for using potion
            mp_threshold: MP threshold for using potion
            use_rohati_heal: If True, use Rohati heal before HP potion
        """
        current_time = time.time()
        
        # Check HP
        if hp_percent <= hp_threshold and current_time - self.last_hp_pot_time >= self.pot_cooldown:
            self.use_hp_pot(hwnd, use_rohati_heal)
            self.last_hp_pot_time = current_time
        
        # Check MP
        if mp_percent <= mp_threshold and current_time - self.last_mp_pot_time >= self.pot_cooldown:
            self.use_mp_pot(hwnd)
            self.last_mp_pot_time = current_time
    
    def use_hp_pot(self, hwnd, use_rohati_heal=False):
        """
        Use an HP potion by pressing '0'
        If use_rohati_heal is True, executes sequence: E -> R
        
        Args:
            hwnd: Window handle (unused, kept for compatibility)
            use_rohati_heal: If True, use Rohati heal before potion
        """
        input_handler.send_input('0')
        time.sleep(random.uniform(0.05, 0.1))
        
        if use_rohati_heal:
            current_time = time.time()
            if current_time - self.last_rohati_heal_time >= self.rohati_heal_cooldown:
                print('[ROHATI HEAL] Executing key sequence: E -> R')
                input_handler.send_input('e')
                time.sleep(random.uniform(0.05, 0.1))
                input_handler.send_input('r')
                print('[ROHATI HEAL] ✅ Key sequence completed')
                self.last_rohati_heal_time = current_time
            else:
                tiempo_restante = self.rohati_heal_cooldown - (current_time - self.last_rohati_heal_time)
                print(f'[ROHATI HEAL] Cooldown active. Time remaining: {tiempo_restante:.1f}s')
    
    def use_mp_pot(self, hwnd):
        """
        Use an MP potion by pressing '9'
        
        Args:
            hwnd: Window handle (unused, kept for compatibility)
        """
        input_handler.send_input('9')
        time.sleep(random.uniform(0.05, 0.1))
