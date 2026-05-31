"""
Settings management - save and load bot configuration
"""
import json
import os
import sys
import config
import logger

_gui_overlay_provider = None


def register_gui_overlay_provider(provider):
    """Register callable() -> dict for GUI-only fields on save."""
    global _gui_overlay_provider
    _gui_overlay_provider = provider


def convert_to_relative_path(absolute_path):
    """Convert an absolute path to relative path for saving in configuration"""
    if not absolute_path:
        return None

    if not os.path.isabs(absolute_path):
        return os.path.normpath(absolute_path)

    try:
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))

        absolute_path = os.path.normpath(absolute_path)
        base_path = os.path.normpath(base_path)

        try:
            relative_path = os.path.relpath(absolute_path, base_path)
            return os.path.normpath(relative_path)
        except ValueError:
            path_parts = absolute_path.split(os.sep)
            if 'jobs' in path_parts:
                jobs_idx = path_parts.index('jobs')
                relative_parts = path_parts[jobs_idx:]
                return os.path.join(*relative_parts)
            return None
    except Exception as e:
        logger.warn(f"Could not convert path {absolute_path} to relative: {e}", "Settings")
        return None


def build_settings_snapshot(gui_overlay=None):
    """Build a JSON-serializable settings dict from config and optional GUI overlay."""
    clean_skill_slots = {}
    for slot_key in config.skill_slots:
        clean_skill_slots[slot_key] = {
            'enabled': config.skill_slots[slot_key]['enabled'],
            'interval': config.skill_slots[slot_key]['interval'],
            'last_used': 0,
        }

    clean_action_slots = {}
    for action_key in config.action_slots:
        if action_key == 'pick':
            clean_action_slots[action_key] = {
                'enabled': config.action_slots[action_key]['enabled'],
                'interval': config.action_slots[action_key]['interval'],
                'last_used': 0,
                'key': config.action_slots[action_key]['key'],
            }

    settings = {
        'skill_slots': clean_skill_slots,
        'action_slots': clean_action_slots,
        'mob_detection_enabled': config.mob_detection_enabled,
        'mob_scan_area': dict(config.mob_scan_area),
        'mob_match_threshold': config.mob_match_threshold,
        'mob_match_margin': config.mob_match_margin,
        'mob_elite_skip_enabled': config.mob_elite_skip_enabled,
        'mob_templates': [dict(entry) for entry in config.mob_templates],
        'auto_attack_enabled': config.auto_attack_enabled,
        'auto_hp_enabled': config.auto_hp_enabled,
        'hp_thresholds': config.hp_thresholds,
        'auto_mp_enabled': config.auto_mp_enabled,
        'mp_threshold': config.mp_threshold,
        'mp_key': config.mp_key,
        'mouse_clicker_enabled': config.mouse_clicker_enabled,
        'mouse_clicker_interval': config.mouse_clicker_interval,
        'mouse_clicker_use_cursor': config.mouse_clicker_use_cursor,
        'mouse_clicker_coords': config.mouse_clicker_coords.copy(),
        'looting_duration': config.LOOTING_DURATION,
        'auto_repair_enabled': config.auto_repair_enabled,
        'repair_key': config.repair_key,
        'break_warning_trigger_count': config.BREAK_WARNING_TRIGGER_COUNT,
        'auto_change_target_enabled': config.auto_change_target_enabled,
        'unstuck_timeout': config.unstuck_timeout,
        'is_mage': config.is_mage,
        'assist_only_enabled': config.assist_only_enabled,
        'assist_key': config.assist_key,
        'selected_window': config.selected_window if config.selected_window else "",
        'buffs_config': {
            str(i): {
                'enabled': config.buffs_config[i]['enabled'],
                'image_path': convert_to_relative_path(config.buffs_config[i].get('image_path')),
                'key': config.buffs_config[i]['key'],
            }
            for i in range(8)
        },
        'skill_sequence_config': {
            str(i): {
                'enabled': config.skill_sequence_config[i]['enabled'],
                'image_path': convert_to_relative_path(config.skill_sequence_config[i].get('image_path')),
                'key': config.skill_sequence_config[i].get('key', ''),
                'bypass': config.skill_sequence_config[i].get('bypass', False),
            }
            for i in range(8)
        },
    }

    if gui_overlay:
        settings.update(gui_overlay)
    return settings


def save_settings(gui_overlay=None):
    """Save all bot settings to a JSON file."""
    try:
        if gui_overlay is None and _gui_overlay_provider:
            try:
                gui_overlay = _gui_overlay_provider()
            except (ValueError, AttributeError) as e:
                logger.warn(f"Could not read GUI overlay for save: {e}", "Settings")

        settings = build_settings_snapshot(gui_overlay=gui_overlay)
        with open(config.SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)

        logger.info(f"Settings saved to {config.SETTINGS_FILE}", "Settings")
        return True
    except Exception as e:
        logger.error(f"Error saving settings: {e}", "Settings")
        return False


def load_settings():
    """Load all bot settings from a JSON file."""
    try:
        if not os.path.exists(config.SETTINGS_FILE):
            logger.info(f"No settings file found: {config.SETTINGS_FILE}", "Settings")
            return False

        with open(config.SETTINGS_FILE, 'r', encoding='utf-8') as f:
            settings = json.load(f)

        if 'skill_slots' in settings:
            for slot_key_str in settings['skill_slots']:
                if slot_key_str.isdigit():
                    slot_key = int(slot_key_str)
                elif isinstance(slot_key_str, str) and slot_key_str.lower().startswith('f'):
                    slot_key = slot_key_str.lower()
                else:
                    slot_key = slot_key_str

                if (isinstance(slot_key, int) and 1 <= slot_key <= 8) or (
                    isinstance(slot_key, str) and slot_key.startswith('f')
                    and slot_key[1:].isdigit() and 1 <= int(slot_key[1:]) <= 10
                ):
                    if slot_key not in config.skill_slots:
                        config.skill_slots[slot_key] = {'enabled': False, 'interval': 1, 'last_used': 0}
                    slot_data = settings['skill_slots'][slot_key_str]
                    config.skill_slots[slot_key].update({
                        'enabled': slot_data.get('enabled', False),
                        'interval': slot_data.get('interval', 1),
                        'last_used': 0,
                    })

        if 'action_slots' in settings and 'pick' in settings['action_slots']:
            config.action_slots['pick'] = settings['action_slots']['pick']

        if 'mob_detection_enabled' in settings:
            config.mob_detection_enabled = settings['mob_detection_enabled']
        if 'mob_scan_area' in settings:
            config.mob_scan_area.update(settings['mob_scan_area'])
        if 'mob_match_threshold' in settings:
            config.mob_match_threshold = float(settings['mob_match_threshold'])
        if 'mob_match_margin' in settings:
            config.mob_match_margin = float(settings['mob_match_margin'])
        if 'mob_elite_skip_enabled' in settings:
            config.mob_elite_skip_enabled = bool(settings['mob_elite_skip_enabled'])
        if 'mob_templates' in settings:
            config.mob_templates = [dict(entry) for entry in settings['mob_templates']]

        import mob_template_store
        mob_template_store.sync_templates_after_load()

        if 'auto_attack_enabled' in settings:
            config.auto_attack_enabled = settings['auto_attack_enabled']
        if 'looting_duration' in settings:
            config.LOOTING_DURATION = settings['looting_duration']
        if 'auto_repair_enabled' in settings:
            config.auto_repair_enabled = settings['auto_repair_enabled']
        if 'repair_key' in settings:
            config.repair_key = settings['repair_key']
        # break_warning_trigger_count is fixed at 10 (not loaded from legacy saves)
        if 'auto_change_target_enabled' in settings:
            config.auto_change_target_enabled = settings['auto_change_target_enabled']
        if 'unstuck_timeout' in settings:
            config.unstuck_timeout = settings['unstuck_timeout']

        if 'auto_hp_enabled' in settings:
            config.auto_hp_enabled = settings['auto_hp_enabled']

        if 'hp_thresholds' in settings:
            config.hp_thresholds = settings['hp_thresholds']
            if isinstance(config.hp_thresholds, list) and len(config.hp_thresholds) > 0:
                config.hp_thresholds.sort(key=lambda x: x.get('threshold', 0), reverse=True)
            else:
                config.hp_thresholds = [{'threshold': 70, 'key': '0'}]
        else:
            config.hp_thresholds = [{'threshold': 70, 'key': '0'}]

        if 'auto_mp_enabled' in settings:
            config.auto_mp_enabled = settings['auto_mp_enabled']
        if 'mp_threshold' in settings:
            config.mp_threshold = settings['mp_threshold']
        if 'mp_key' in settings:
            config.mp_key = settings['mp_key']

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
        if 'assist_only_enabled' in settings:
            config.assist_only_enabled = settings['assist_only_enabled']
        if 'assist_key' in settings:
            config.assist_key = settings['assist_key']

        config.low_cpu_mode = True

        if 'selected_window' in settings:
            config.selected_window = settings['selected_window']

        if 'buffs_config' in settings:
            for idx_str, buff_data in settings['buffs_config'].items():
                try:
                    idx = int(idx_str)
                    if 0 <= idx < 8:
                        config.buffs_config[idx]['enabled'] = buff_data.get('enabled', False)
                        image_path = buff_data.get('image_path', None)
                        if image_path and os.path.isabs(image_path):
                            image_path = convert_to_relative_path(image_path)
                        config.buffs_config[idx]['image_path'] = image_path
                        config.buffs_config[idx]['key'] = buff_data.get('key', '')
                except (ValueError, KeyError):
                    continue

        if 'skill_sequence_config' in settings:
            for idx_str, skill_data in settings['skill_sequence_config'].items():
                try:
                    idx = int(idx_str)
                    if 0 <= idx < 8:
                        config.skill_sequence_config[idx]['enabled'] = skill_data.get('enabled', False)
                        image_path = skill_data.get('image_path', None)
                        if image_path and os.path.isabs(image_path):
                            image_path = convert_to_relative_path(image_path)
                        config.skill_sequence_config[idx]['image_path'] = image_path
                        config.skill_sequence_config[idx]['key'] = skill_data.get('key', '')
                        config.skill_sequence_config[idx]['bypass'] = skill_data.get('bypass', False)
                except (ValueError, KeyError):
                    continue

        logger.info(f"Settings loaded from {config.SETTINGS_FILE}", "Settings")
        return True
    except Exception as e:
        logger.error(f"Error loading settings: {e}", "Settings")
        return False
