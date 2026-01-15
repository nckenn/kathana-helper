"""
Settings management - save and load bot configuration
"""
import json
import os
import config


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
            'target_name_area': config.target_name_area.copy(),
            'target_hp_bar_area': config.target_hp_bar_area.copy(),
            'auto_attack_enabled': config.auto_attack_enabled,
            'auto_hp_enabled': config.auto_hp_enabled,
            'hp_threshold': config.hp_threshold,
            'hp_bar_area': config.hp_bar_area.copy(),
            'auto_mp_enabled': config.auto_mp_enabled,
            'mp_threshold': config.mp_threshold,
            'mp_bar_area': config.mp_bar_area.copy(),
            'mouse_clicker_enabled': config.mouse_clicker_enabled,
            'mouse_clicker_interval': config.mouse_clicker_interval,
            'mouse_clicker_use_cursor': config.mouse_clicker_use_cursor,
            'mouse_clicker_coords': config.mouse_clicker_coords.copy(),
            'auto_repair_enabled': config.auto_repair_enabled,
            'system_message_area': config.system_message_area.copy(),
            'auto_change_target_enabled': config.auto_change_target_enabled,
            'unstuck_timeout': config.unstuck_timeout,
            'is_mage': config.is_mage,
            'selected_window': config.selected_window if config.selected_window else "",
            'buffs_config': {str(i): {
                'enabled': config.buffs_config[i]['enabled'],
                'image_path': config.buffs_config[i]['image_path'],
                'key': config.buffs_config[i]['key']
            } for i in range(8)},
            'skill_sequence_config': {str(i): {
                'enabled': config.skill_sequence_config[i]['enabled'],
                'image_path': config.skill_sequence_config[i].get('image_path'),
                'key': config.skill_sequence_config[i].get('key', ''),
                'bypass': config.skill_sequence_config[i].get('bypass', False)
            } for i in range(8)}
        }
        
        # Get current GUI values if available
        try:
            from gui import BotGUI
            if hasattr(BotGUI, '_instance') and BotGUI._instance:
                gui = BotGUI._instance
                settings['auto_attack_enabled'] = gui.auto_attack_var.get()
                settings['hp_threshold'] = int(gui.hp_threshold_var.get())
                settings['hp_bar_area'] = {
                    'x': int(gui.hp_x_var.get()),
                    'y': int(gui.hp_y_var.get()),
                    'width': int(gui.hp_width_var.get()),
                    'height': int(gui.hp_height_var.get())
                }
                settings['mp_threshold'] = int(gui.mp_threshold_var.get())
                settings['mp_bar_area'] = {
                    'x': int(gui.mp_x_var.get()),
                    'y': int(gui.mp_y_var.get()),
                    'width': int(gui.mp_width_var.get()),
                    'height': int(gui.mp_height_var.get())
                }
                settings['mouse_clicker_enabled'] = gui.mouse_clicker_var.get()
                settings['mouse_clicker_interval'] = float(gui.mouse_clicker_interval_var.get())
                settings['mouse_clicker_use_cursor'] = (gui.mouse_clicker_mode_var.get() == "cursor")
                settings['mouse_clicker_coords'] = {
                    'x': int(gui.mouse_clicker_x_var.get()),
                    'y': int(gui.mouse_clicker_y_var.get())
                }
                settings['selected_window'] = gui.window_var.get() if gui.window_var.get() else ""
                if hasattr(gui, 'auto_repair_var'):
                    settings['auto_repair_enabled'] = gui.auto_repair_var.get()
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
        if 'target_name_area' in settings:
            config.target_name_area.update(settings['target_name_area'])
        elif 'mob_name_coordinates' in settings:
            config.target_name_area.update(settings['mob_name_coordinates'])
        if 'target_hp_bar_area' in settings:
            config.target_hp_bar_area.update(settings['target_hp_bar_area'])
        
        # Load auto features
        if 'auto_attack_enabled' in settings:
            config.auto_attack_enabled = settings['auto_attack_enabled']
        if 'auto_repair_enabled' in settings:
            config.auto_repair_enabled = settings['auto_repair_enabled']
        if 'system_message_area' in settings:
            config.system_message_area.update(settings['system_message_area'])
        if 'auto_change_target_enabled' in settings:
            config.auto_change_target_enabled = settings['auto_change_target_enabled']
        if 'unstuck_timeout' in settings:
            config.unstuck_timeout = settings['unstuck_timeout']
        
        # Load HP/MP settings
        if 'auto_hp_enabled' in settings:
            config.auto_hp_enabled = settings['auto_hp_enabled']
        if 'hp_threshold' in settings:
            config.hp_threshold = settings['hp_threshold']
        if 'hp_bar_area' in settings:
            config.hp_bar_area.update(settings['hp_bar_area'])
        elif 'hp_coordinates' in settings:
            config.hp_bar_area['x'] = settings['hp_coordinates'].get('x', 152)
            config.hp_bar_area['y'] = settings['hp_coordinates'].get('y', 69)
        
        if 'auto_mp_enabled' in settings:
            config.auto_mp_enabled = settings['auto_mp_enabled']
        if 'mp_threshold' in settings:
            config.mp_threshold = settings['mp_threshold']
        if 'mp_bar_area' in settings:
            config.mp_bar_area.update(settings['mp_bar_area'])
        elif 'mp_coordinates' in settings:
            config.mp_bar_area['x'] = settings['mp_coordinates'].get('x', 428)
            config.mp_bar_area['y'] = settings['mp_coordinates'].get('y', 139)
        
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
                        config.buffs_config[idx]['image_path'] = buff_data.get('image_path', None)
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
                        config.skill_sequence_config[idx]['image_path'] = skill_data.get('image_path', None)
                        config.skill_sequence_config[idx]['key'] = skill_data.get('key', '')
                        config.skill_sequence_config[idx]['bypass'] = skill_data.get('bypass', False)
                except (ValueError, KeyError):
                    continue
            print("Loaded skill sequence configuration")
        
        print(f"Settings loaded from {config.SETTINGS_FILE}")
        return True
    except Exception as e:
        print(f"Error loading settings: {e}")
        return False
