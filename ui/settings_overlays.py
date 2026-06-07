"""GUI ↔ config sync for settings save/load."""
import config


def sync_gui_to_config(gui):
    """Write current GUI widget values into config before saving."""
    if hasattr(gui, 'skill_vars'):
        for slot_key, var in gui.skill_vars.items():
            if slot_key in config.skill_slots:
                config.skill_slots[slot_key]['enabled'] = bool(var.get())
    if hasattr(gui, 'skill_intervals'):
        for slot_key, var in gui.skill_intervals.items():
            if slot_key not in config.skill_slots:
                continue
            try:
                config.skill_slots[slot_key]['interval'] = float(var.get())
            except ValueError:
                pass

    if hasattr(gui, 'action_vars'):
        for action_key, var in gui.action_vars.items():
            if action_key in config.action_slots:
                config.action_slots[action_key]['enabled'] = bool(var.get())
    if hasattr(gui, 'action_intervals'):
        for action_key, var in gui.action_intervals.items():
            if action_key not in config.action_slots:
                continue
            try:
                config.action_slots[action_key]['interval'] = float(var.get())
            except ValueError:
                pass

    if hasattr(gui, 'mob_detection_var'):
        config.mob_detection_enabled = bool(gui.mob_detection_var.get())
    if hasattr(gui, 'mob_elite_skip_var'):
        config.mob_elite_skip_enabled = bool(gui.mob_elite_skip_var.get())

    if hasattr(gui, 'auto_attack_var'):
        config.auto_attack_enabled = bool(gui.auto_attack_var.get())
    if hasattr(gui, 'auto_hp_var'):
        config.auto_hp_enabled = bool(gui.auto_hp_var.get())
    if hasattr(gui, 'auto_mp_var'):
        config.auto_mp_enabled = bool(gui.auto_mp_var.get())

    if hasattr(gui, 'mp_threshold_var'):
        try:
            config.mp_threshold = int(gui.mp_threshold_var.get())
        except ValueError:
            pass
    if hasattr(gui, 'mp_key_var'):
        config.mp_key = gui.mp_key_var.get().strip()

    if hasattr(gui, 'auto_repair_var'):
        config.auto_repair_enabled = bool(gui.auto_repair_var.get())
    if hasattr(gui, 'repair_key_var'):
        config.repair_key = gui.repair_key_var.get().strip()

    if hasattr(gui, 'auto_change_target_var'):
        config.auto_change_target_enabled = bool(gui.auto_change_target_var.get())
    if hasattr(gui, 'unstuck_timeout_var'):
        try:
            config.unstuck_timeout = float(gui.unstuck_timeout_var.get())
        except ValueError:
            pass

    if hasattr(gui, 'looting_duration_var'):
        try:
            config.LOOTING_DURATION = float(gui.looting_duration_var.get())
        except ValueError:
            pass

    if hasattr(gui, 'is_mage_var'):
        config.is_mage = bool(gui.is_mage_var.get())
    if hasattr(gui, 'assist_only_var'):
        config.assist_only_enabled = bool(gui.assist_only_var.get())
    if hasattr(gui, 'assist_key_var'):
        config.assist_key = gui.assist_key_var.get().strip()

    if hasattr(gui, 'mouse_clicker_var'):
        config.mouse_clicker_enabled = bool(gui.mouse_clicker_var.get())
    if hasattr(gui, 'mouse_clicker_interval_var'):
        try:
            config.mouse_clicker_interval = float(gui.mouse_clicker_interval_var.get())
        except ValueError:
            pass
    if hasattr(gui, 'mouse_clicker_mode_var'):
        config.mouse_clicker_use_cursor = gui.mouse_clicker_mode_var.get() == "cursor"
    if hasattr(gui, 'mouse_clicker_x_var'):
        try:
            config.mouse_clicker_coords['x'] = int(gui.mouse_clicker_x_var.get())
        except ValueError:
            pass
    if hasattr(gui, 'mouse_clicker_y_var'):
        try:
            config.mouse_clicker_coords['y'] = int(gui.mouse_clicker_y_var.get())
        except ValueError:
            pass

    if hasattr(gui, 'buffs_vars'):
        for i, var in gui.buffs_vars.items():
            if 0 <= i < 8:
                config.buffs_config[i]['enabled'] = bool(var.get())
    if hasattr(gui, 'buffs_key_vars'):
        for i, var in gui.buffs_key_vars.items():
            if 0 <= i < 8:
                config.buffs_config[i]['key'] = var.get().strip()

    if hasattr(gui, 'skill_sequence_vars'):
        for i, var in gui.skill_sequence_vars.items():
            if 0 <= i < 8:
                config.skill_sequence_config[i]['enabled'] = bool(var.get())
    if hasattr(gui, 'skill_sequence_bypass_vars'):
        for i, var in gui.skill_sequence_bypass_vars.items():
            if 0 <= i < 8:
                config.skill_sequence_config[i]['bypass'] = bool(var.get())
    if hasattr(gui, 'skill_sequence_key_vars'):
        for i, var in gui.skill_sequence_key_vars.items():
            if 0 <= i < 8:
                config.skill_sequence_config[i]['key'] = var.get().strip()

    if hasattr(gui, 'window_var'):
        config.selected_window = gui.window_var.get() if gui.window_var.get() else ""


def collect_gui_overlay(gui):
    """Legacy hook: sync GUI into config (overlay merge no longer required)."""
    sync_gui_to_config(gui)
    return {}
