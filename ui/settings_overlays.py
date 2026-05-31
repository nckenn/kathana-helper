"""GUI-only settings fields merged into save snapshots."""
import config


def collect_gui_overlay(gui):
    """Build widget-only settings dict from a BotGUI instance."""
    overlay = {
        'auto_attack_enabled': bool(gui.auto_attack_var.get()),
        'hp_thresholds': list(config.hp_thresholds),
        'mouse_clicker_enabled': bool(gui.mouse_clicker_var.get()),
        'mouse_clicker_interval': float(gui.mouse_clicker_interval_var.get()),
        'mouse_clicker_use_cursor': gui.mouse_clicker_mode_var.get() == "cursor",
        'mouse_clicker_coords': {
            'x': int(gui.mouse_clicker_x_var.get()),
            'y': int(gui.mouse_clicker_y_var.get()),
        },
        'selected_window': gui.window_var.get() if gui.window_var.get() else "",
    }
    if hasattr(gui, 'mp_threshold_var'):
        overlay['mp_threshold'] = int(gui.mp_threshold_var.get())
    if hasattr(gui, 'looting_duration_var'):
        try:
            overlay['looting_duration'] = float(gui.looting_duration_var.get())
        except ValueError:
            overlay['looting_duration'] = config.LOOTING_DURATION
    if hasattr(gui, 'auto_repair_var'):
        overlay['auto_repair_enabled'] = bool(gui.auto_repair_var.get())
    if hasattr(gui, 'repair_key_var'):
        overlay['repair_key'] = gui.repair_key_var.get()
    if hasattr(gui, 'break_warning_trigger_count_var'):
        try:
            overlay['break_warning_trigger_count'] = int(gui.break_warning_trigger_count_var.get())
        except ValueError:
            overlay['break_warning_trigger_count'] = config.BREAK_WARNING_TRIGGER_COUNT
    if hasattr(gui, 'mp_key_var'):
        overlay['mp_key'] = gui.mp_key_var.get()
    if hasattr(gui, 'auto_change_target_var'):
        overlay['auto_change_target_enabled'] = bool(gui.auto_change_target_var.get())
    if hasattr(gui, 'unstuck_timeout_var'):
        overlay['unstuck_timeout'] = float(gui.unstuck_timeout_var.get())
    if hasattr(gui, 'is_mage_var'):
        overlay['is_mage'] = bool(gui.is_mage_var.get())
    if hasattr(gui, 'assist_only_var'):
        overlay['assist_only_enabled'] = bool(gui.assist_only_var.get())
    if hasattr(gui, 'assist_key_var'):
        overlay['assist_key'] = gui.assist_key_var.get()
    return overlay
