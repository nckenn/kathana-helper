"""Automatic HP/MP potion usage."""
import random
import time
import config
import input_handler
import bar_reader


class AutoPots:
    def __init__(self):
        self.last_hp_by_key = {}
        self.last_mp_time = 0.0
        self.cooldown = 0.5

    def check(self):
        if not config.connected_window:
            return
        hwnd = config.connected_window.handle
        now = time.time()

        need_hp = config.auto_hp_enabled and config.bar_area_configured(config.hp_bar_area)
        need_mp = config.auto_mp_enabled and config.bar_area_configured(config.mp_bar_area)
        if not need_hp and not need_mp:
            return

        hp_due = need_hp and (now - config.last_hp_capture_time >= config.HP_CAPTURE_INTERVAL)
        mp_due = need_mp and (now - config.last_mp_capture_time >= config.MP_CAPTURE_INTERVAL)
        if not hp_due and not mp_due:
            return

        hp_percent = config.current_hp_percentage
        mp_percent = config.current_mp_percentage

        if hp_due:
            hp_val = bar_reader.read_hp_percent(hwnd)
            if hp_val is not None:
                hp_percent = max(0, min(100, hp_val))
                config.current_hp_percentage = hp_percent
                config.last_hp_capture_time = now

        if mp_due:
            mp_val = bar_reader.read_mp_percent(hwnd)
            if mp_val is not None:
                mp_percent = max(0, min(100, mp_val))
                config.current_mp_percentage = mp_percent
                config.last_mp_capture_time = now

        if config.auto_hp_enabled and config.hp_thresholds:
            matching = [t for t in config.hp_thresholds if hp_percent <= t['threshold']]
            matching.sort(key=lambda x: x['threshold'], reverse=True)
            for row in matching:
                key = row['key']
                if now - self.last_hp_by_key.get(key, 0) >= self.cooldown:
                    input_handler.send_input(key)
                    self.last_hp_by_key[key] = now
                    time.sleep(random.uniform(0.05, 0.1))
                    break

        if config.auto_mp_enabled and mp_percent <= float(config.mp_threshold):
            if now - self.last_mp_time >= self.cooldown:
                input_handler.send_input(config.mp_key)
                self.last_mp_time = now
                time.sleep(random.uniform(0.05, 0.1))
