"""
Auto-pots module for automatically using potions when HP/MP is low
Auto-pots functionality for automatic potion usage
"""
import time
import random
import config
import input_handler
import frame_cache


class AutoPots:
    """Handles automatic potion usage when HP/MP drops below thresholds"""

    def __init__(self):
        """Initialize the AutoPots system"""
        self.last_hp_pot_time = 0  # Kept for backward compatibility
        self.last_hp_pot_time_by_key = {}  # Track cooldown per key for multi-threshold support
        self.last_mp_pot_time = 0
        self.pot_cooldown = 0.5  # Minimum time between pot uses (seconds)
        self.last_rohati_heal_time = 0
        self.rohati_heal_cooldown = 3.0

    def check_auto_pots(self):
        """Check and use potions if necessary - HP and MP are checked separately"""
        try:
            if not config.calibrator:
                return

            hwnd = config.connected_window.handle
            current_time = time.time()

            should_check_hp = (config.auto_hp_enabled and
                              (current_time - config.last_hp_capture_time >=
                               config.get_hp_capture_interval()))
            should_check_mp = (config.auto_mp_enabled and
                              (current_time - config.last_mp_capture_time >=
                               config.get_mp_capture_interval()))

            if not should_check_hp and not should_check_mp:
                return

            if should_check_hp and should_check_mp:
                screen = frame_cache.get_frame(hwnd, config.calibrator)
                if screen is not None:
                    percentages = config.calibrator.get_hp_mp_percentages_from_screen(screen)
                    if percentages is not None:
                        hp_percent, mp_percent = percentages
                        config.last_hp_capture_time = current_time
                        config.last_mp_capture_time = current_time
                    else:
                        hp_percent = config.current_hp_percentage
                        mp_percent = config.current_mp_percentage
                else:
                    hp_percent = config.calibrator.get_hp_percentage(hwnd)
                    mp_percent = config.calibrator.get_mp_percentage(hwnd)
                    config.last_hp_capture_time = current_time
                    config.last_mp_capture_time = current_time
            elif should_check_hp:
                hp_percent = config.calibrator.get_hp_percentage(hwnd)
                config.last_hp_capture_time = current_time
                mp_percent = config.current_mp_percentage
            else:
                mp_percent = config.calibrator.get_mp_percentage(hwnd)
                config.last_mp_capture_time = current_time
                hp_percent = config.current_hp_percentage

            hp_percent = max(0, min(100, hp_percent))
            mp_percent = max(0, min(100, mp_percent))

            config.current_hp_percentage = hp_percent
            config.current_mp_percentage = mp_percent

            mp_threshold = float(config.mp_threshold)

            if config.auto_hp_enabled:
                if config.hp_thresholds and len(config.hp_thresholds) > 0:
                    matching_thresholds = [t for t in config.hp_thresholds if hp_percent <= t['threshold']]
                    if matching_thresholds:
                        matching_thresholds.sort(key=lambda x: x['threshold'], reverse=True)

                        for threshold_data in matching_thresholds:
                            key = threshold_data['key']

                            last_use_time = self.last_hp_pot_time_by_key.get(key, 0)
                            if current_time - last_use_time >= self.pot_cooldown:
                                self.use_hp_pot_with_key(hwnd, key, False)
                                self.last_hp_pot_time_by_key[key] = current_time
                                self.last_hp_pot_time = current_time
                                if len(matching_thresholds) > 1:
                                    time.sleep(random.uniform(0.05, 0.1))

            if config.auto_mp_enabled:
                if mp_percent <= mp_threshold and current_time - self.last_mp_pot_time >= self.pot_cooldown:
                    self.use_mp_pot(hwnd)
                    self.last_mp_pot_time = current_time

        except ValueError:
            print("[Auto Pots] Error: HP/MP thresholds must be valid numbers")
        except Exception as e:
            print(f"[Auto Pots] Error: {e}")

    def use_hp_pot(self, hwnd, use_rohati_heal=False):
        """
        Use an HP potion by pressing the first configured HP key (for backward compatibility)
        If use_rohati_heal is True, executes sequence: E -> R
        """
        if config.hp_thresholds and len(config.hp_thresholds) > 0:
            first_key = config.hp_thresholds[0]['key']
            self.use_hp_pot_with_key(hwnd, first_key, use_rohati_heal)

    def use_hp_pot_with_key(self, hwnd, key, use_rohati_heal=False):
        """Use an HP potion by pressing the specified key."""
        input_handler.send_input(key)
        time.sleep(random.uniform(0.05, 0.1))

        if use_rohati_heal:
            current_time = time.time()
            if current_time - self.last_rohati_heal_time >= self.rohati_heal_cooldown:
                print('[ROHATI HEAL] Executing key sequence: E -> R')
                input_handler.send_input('e')
                time.sleep(random.uniform(0.05, 0.1))
                input_handler.send_input('r')
                print('[ROHATI HEAL] Key sequence completed')
                self.last_rohati_heal_time = current_time
            else:
                tiempo_restante = self.rohati_heal_cooldown - (current_time - self.last_rohati_heal_time)
                print(f'[ROHATI HEAL] Cooldown active. Time remaining: {tiempo_restante:.1f}s')

    def use_mp_pot(self, hwnd):
        """Use an MP potion by pressing the configured MP key."""
        input_handler.send_input(config.mp_key)
        time.sleep(random.uniform(0.05, 0.1))
