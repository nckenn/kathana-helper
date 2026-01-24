"""
Settings management - save and load bot configuration
"""
import json
import os
import sys
import config


def convert_to_relative_path(absolute_path):
    """Convert an absolute path to relative path for saving in configuration"""
    if not absolute_path:
        return None
    
    # If already relative, return as-is
    if not os.path.isabs(absolute_path):
        return os.path.normpath(absolute_path)
    
    try:
        # Determine base path
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        # Normalize paths
        absolute_path = os.path.normpath(absolute_path)
        base_path = os.path.normpath(base_path)
        
        # Try to extract relative path
        try:
            relative_path = os.path.relpath(absolute_path, base_path)
            return os.path.normpath(relative_path)
        except ValueError:
            # Paths on different drives (Windows) - try to extract 'jobs' folder part
            path_parts = absolute_path.split(os.sep)
            if 'jobs' in path_parts:
                jobs_idx = path_parts.index('jobs')
                relative_parts = path_parts[jobs_idx:]
                return os.path.join(*relative_parts)
            # Can't convert, return None (shouldn't happen in normal usage)
            return None
    except Exception as e:
        print(f"Warning: Could not convert path {absolute_path} to relative: {e}")
        return None


def save_settings():
    """Save all bot settings to a JSON file"""
    try:
        clean_skill_slots = {}
        for slot_key in config.skill_slots:
            clean_skill_slots[slot_key] = {
                'enabled': config.skill_slots[slot_key]['enabled'],
                'interval': config.skill_slots[slot_key]['interval'],
                'last_used': 0
            }
        
        clean_action_slots = {}
        for action_key in config.action_slots:
            if action_key == 'pick':
                clean_action_slots[action_key] = {
                    'enabled': config.action_slots[action_key]['enabled'],
                    'interval': config.action_slots[action_key]['interval'],
                    'last_used': 0,
                    'key': config.action_slots[action_key]['key']
                }
        
        settings = {
            'skill_slots': clean_skill_slots,
            'action_slots': clean_action_slots,
            'mob_target_list': config.mob_target_list.copy(),
            'mob_detection_enabled': config.mob_detection_enabled,
            # target_name_area is NOT saved - detection/calibration region should not be persisted
            # target_hp_bar_area is NOT saved - detection/calibration region should not be persisted
            'auto_attack_enabled': config.auto_attack_enabled,
            'auto_hp_enabled': config.auto_hp_enabled,
            'hp_threshold': config.hp_threshold,
            # hp_bar_area is NOT saved - calibration data should not be persisted
            'auto_mp_enabled': config.auto_mp_enabled,
            'mp_threshold': config.mp_threshold,
            # mp_bar_area is NOT saved - calibration data should not be persisted
            'mouse_clicker_enabled': config.mouse_clicker_enabled,
            'mouse_clicker_interval': config.mouse_clicker_interval,
            'mouse_clicker_use_cursor': config.mouse_clicker_use_cursor,
            'mouse_clicker_coords': config.mouse_clicker_coords.copy(),
            'looting_duration': config.LOOTING_DURATION,
            'auto_repair_enabled': config.auto_repair_enabled,
            'break_warning_trigger_count': config.BREAK_WARNING_TRIGGER_COUNT,
            'auto_repair_check_interval': config.AUTO_REPAIR_CHECK_INTERVAL,
            # system_message_area is NOT saved - calibration data should not be persisted
            'auto_change_target_enabled': config.auto_change_target_enabled,
            'unstuck_timeout': config.unstuck_timeout,
            'is_mage': config.is_mage,
            'selected_window': config.selected_window if config.selected_window else "",
            'buffs_config': {str(i): {
                'enabled': config.buffs_config[i]['enabled'],
                'image_path': convert_to_relative_path(config.buffs_config[i].get('image_path')),  # Convert to relative
                'key': config.buffs_config[i]['key']
            } for i in range(8)},
            'skill_sequence_config': {str(i): {
                'enabled': config.skill_sequence_config[i]['enabled'],
                'image_path': convert_to_relative_path(config.skill_sequence_config[i].get('image_path')),  # Convert to relative
                'key': config.skill_sequence_config[i].get('key', '')
            } for i in range(8)}
        }
        
        # Get current GUI values if available
        try:
            from gui import BotGUI
            if hasattr(BotGUI, '_instance') and BotGUI._instance:
                gui = BotGUI._instance
                settings['auto_attack_enabled'] = gui.auto_attack_var.get()
                settings['hp_threshold'] = int(gui.hp_threshold_var.get())
                # hp_bar_area is NOT saved - calibration data should not be persisted
                settings['mp_threshold'] = int(gui.mp_threshold_var.get())
                # mp_bar_area is NOT saved - calibration data should not be persisted
                settings['mouse_clicker_enabled'] = gui.mouse_clicker_var.get()
                settings['mouse_clicker_interval'] = float(gui.mouse_clicker_interval_var.get())
                settings['mouse_clicker_use_cursor'] = (gui.mouse_clicker_mode_var.get() == "cursor")
                settings['mouse_clicker_coords'] = {
                    'x': int(gui.mouse_clicker_x_var.get()),
                    'y': int(gui.mouse_clicker_y_var.get())
                }
                settings['selected_window'] = gui.window_var.get() if gui.window_var.get() else ""
                if hasattr(gui, 'looting_duration_var'):
                    try:
                        settings['looting_duration'] = float(gui.looting_duration_var.get())
                    except ValueError:
                        settings['looting_duration'] = config.LOOTING_DURATION
                if hasattr(gui, 'auto_repair_var'):
                    settings['auto_repair_enabled'] = gui.auto_repair_var.get()
                if hasattr(gui, 'break_warning_trigger_count_var'):
                    try:
                        settings['break_warning_trigger_count'] = int(gui.break_warning_trigger_count_var.get())
                    except ValueError:
                        settings['break_warning_trigger_count'] = config.BREAK_WARNING_TRIGGER_COUNT
                if hasattr(gui, 'auto_repair_check_interval_var'):
                    try:
                        settings['auto_repair_check_interval'] = float(gui.auto_repair_check_interval_var.get())
                    except ValueError:
                        settings['auto_repair_check_interval'] = config.AUTO_REPAIR_CHECK_INTERVAL
                if hasattr(gui, 'auto_change_target_var'):
                    settings['auto_change_target_enabled'] = gui.auto_change_target_var.get()
                if hasattr(gui, 'unstuck_timeout_var'):
                    settings['unstuck_timeout'] = float(gui.unstuck_timeout_var.get())
                if hasattr(gui, 'is_mage_var'):
                    settings['is_mage'] = gui.is_mage_var.get()
        except (ValueError, AttributeError, ImportError) as e:
            print(f"Warning: Could not save some GUI values: {e}")
        
        with open(config.SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
        
        print(f"Settings saved to {config.SETTINGS_FILE}")
        return True
    except Exception as e:
        print(f"Error saving settings: {e}")
        return False


def load_settings():
    """Load all bot settings from a JSON file"""
    try:
        if not os.path.exists(config.SETTINGS_FILE):
            print(f"No settings file found: {config.SETTINGS_FILE}")
            return False
        
        with open(config.SETTINGS_FILE, 'r') as f:
            settings = json.load(f)
        
        # Load skill slots
        if 'skill_slots' in settings:
            for slot_key_str in settings['skill_slots']:
                if slot_key_str.isdigit():
                    slot_key = int(slot_key_str)
                elif isinstance(slot_key_str, str) and slot_key_str.lower().startswith('f'):
                    slot_key = slot_key_str.lower()
                else:
                    slot_key = slot_key_str
                
                if (isinstance(slot_key, int) and 1 <= slot_key <= 8) or \
                   (isinstance(slot_key, str) and slot_key.startswith('f') and 
                    slot_key[1:].isdigit() and 1 <= int(slot_key[1:]) <= 10):
                    if slot_key not in config.skill_slots:
                        config.skill_slots[slot_key] = {'enabled': False, 'interval': 1, 'last_used': 0}
                    slot_data = settings['skill_slots'][slot_key_str]
                    config.skill_slots[slot_key].update({
                        'enabled': slot_data.get('enabled', False),
                        'interval': slot_data.get('interval', 1),
                        'last_used': 0
                    })
            print("Loaded skill slots settings")
        
        # Load action slots
        if 'action_slots' in settings:
            if 'pick' in settings['action_slots']:
                config.action_slots['pick'] = settings['action_slots']['pick']
            print("Loaded action slots settings")
        
        # Load mob settings
        if 'mob_target_list' in settings:
            config.mob_target_list = settings['mob_target_list']
        # Backward compatibility: migrate old mob_skip_list to mob_target_list
        elif 'mob_skip_list' in settings:
            config.mob_target_list = settings['mob_skip_list']
            print("[Settings] Migrated mob_skip_list to mob_target_list (inverted logic)")
        if 'mob_detection_enabled' in settings:
            config.mob_detection_enabled = settings['mob_detection_enabled']
        # target_name_area / target_hp_bar_area are NOT loaded - detection/calibration regions should not be persisted
        # (Backward-compat keys like mob_name_coordinates are also intentionally ignored)
        
        # Load auto features
        if 'auto_attack_enabled' in settings:
            config.auto_attack_enabled = settings['auto_attack_enabled']
        if 'looting_duration' in settings:
            config.LOOTING_DURATION = settings['looting_duration']
        if 'auto_repair_enabled' in settings:
            config.auto_repair_enabled = settings['auto_repair_enabled']
        if 'break_warning_trigger_count' in settings:
            config.BREAK_WARNING_TRIGGER_COUNT = settings['break_warning_trigger_count']
        if 'auto_repair_check_interval' in settings:
            config.AUTO_REPAIR_CHECK_INTERVAL = settings['auto_repair_check_interval']
        # system_message_area is NOT loaded - calibration data should not be persisted
        if 'auto_change_target_enabled' in settings:
            config.auto_change_target_enabled = settings['auto_change_target_enabled']
        if 'unstuck_timeout' in settings:
            config.unstuck_timeout = settings['unstuck_timeout']
        
        # Load HP/MP settings
        if 'auto_hp_enabled' in settings:
            config.auto_hp_enabled = settings['auto_hp_enabled']
        if 'hp_threshold' in settings:
            config.hp_threshold = settings['hp_threshold']
        # hp_bar_area is NOT loaded - calibration data should not be persisted
        # (calibration must be performed each session)
        
        if 'auto_mp_enabled' in settings:
            config.auto_mp_enabled = settings['auto_mp_enabled']
        if 'mp_threshold' in settings:
            config.mp_threshold = settings['mp_threshold']
        # mp_bar_area is NOT loaded - calibration data should not be persisted
        # (calibration must be performed each session)
        
        # Load mouse clicker settings
        if 'mouse_clicker_enabled' in settings:
            config.mouse_clicker_enabled = settings['mouse_clicker_enabled']
        if 'mouse_clicker_interval' in settings:
            config.mouse_clicker_interval = settings['mouse_clicker_interval']
        if 'mouse_clicker_use_cursor' in settings:
            config.mouse_clicker_use_cursor = settings['mouse_clicker_use_cursor']
        if 'mouse_clicker_coords' in settings:
            config.mouse_clicker_coords.update(settings['mouse_clicker_coords'])
        
        if 'is_mage' in settings:
            config.is_mage = settings['is_mage']
        
        if 'selected_window' in settings:
            config.selected_window = settings['selected_window']
        
        # Load buffs configuration
        if 'buffs_config' in settings:
            for idx_str, buff_data in settings['buffs_config'].items():
                try:
                    idx = int(idx_str)
                    if 0 <= idx < 8:
                        config.buffs_config[idx]['enabled'] = buff_data.get('enabled', False)
                        # Convert absolute paths to relative when loading
                        image_path = buff_data.get('image_path', None)
                        if image_path and os.path.isabs(image_path):
                            image_path = convert_to_relative_path(image_path)
                        config.buffs_config[idx]['image_path'] = image_path
                        config.buffs_config[idx]['key'] = buff_data.get('key', '')
                except (ValueError, KeyError):
                    continue
            print("Loaded buffs configuration")
        
        # Load skill sequence configuration
        if 'skill_sequence_config' in settings:
            for idx_str, skill_data in settings['skill_sequence_config'].items():
                try:
                    idx = int(idx_str)
                    if 0 <= idx < 8:
                        config.skill_sequence_config[idx]['enabled'] = skill_data.get('enabled', False)
                        # Convert absolute paths to relative when loading
                        image_path = skill_data.get('image_path', None)
                        if image_path and os.path.isabs(image_path):
                            image_path = convert_to_relative_path(image_path)
                        config.skill_sequence_config[idx]['image_path'] = image_path
                        config.skill_sequence_config[idx]['key'] = skill_data.get('key', '')
                except (ValueError, KeyError):
                    continue
            print("Loaded skill sequence configuration")
        
        print(f"Settings loaded from {config.SETTINGS_FILE}")
        return True
    except Exception as e:
        print(f"Error loading settings: {e}")
        return False
