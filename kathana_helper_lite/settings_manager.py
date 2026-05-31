"""Save and load settings_lite.json next to the app."""
import json
import os
import config


def _parse_slot_key(key_str):
    if isinstance(key_str, int):
        return key_str
    s = str(key_str)
    if s.isdigit():
        return int(s)
    if s.lower().startswith('f') and s[1:].isdigit():
        return s.lower()
    return s


def _valid_slot(slot_key):
    if isinstance(slot_key, int) and slot_key in list(range(10)):
        return True
    if isinstance(slot_key, str) and slot_key.startswith('f'):
        num = slot_key[1:]
        return num.isdigit() and 1 <= int(num) <= 10
    return False


def build_snapshot():
    clean_slots = {}
    for slot_key, data in config.skill_slots.items():
        clean_slots[str(slot_key)] = {
            'enabled': data['enabled'],
            'interval': data['interval'],
            'last_used': 0,
        }
    clean_actions = {}
    for name, data in config.action_slots.items():
        clean_actions[name] = {
            'enabled': data['enabled'],
            'interval': data['interval'],
            'last_used': 0,
            'key': data['key'],
        }
    return {
        'skill_slots': clean_slots,
        'action_slots': clean_actions,
        'auto_hp_enabled': config.auto_hp_enabled,
        'auto_mp_enabled': config.auto_mp_enabled,
        'hp_thresholds': list(config.hp_thresholds),
        'mp_threshold': config.mp_threshold,
        'mp_key': config.mp_key,
        'hp_bar_area': dict(config.hp_bar_area),
        'mp_bar_area': dict(config.mp_bar_area),
        'selected_window': config.selected_window or '',
        'mob_filter_enabled': config.mob_filter_enabled,
        'mob_scan_area': dict(config.mob_scan_area),
        'mob_match_threshold': config.mob_match_threshold,
        'mob_match_margin': config.mob_match_margin,
        'mob_templates': list(config.mob_templates),
    }


def save_settings():
    try:
        with open(config.SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(build_snapshot(), f, indent=2)
        print(f'[settings] saved {config.SETTINGS_FILE}')
        return True
    except Exception as exc:
        print(f'[settings] save failed: {exc}')
        return False


def load_settings():
    if not os.path.exists(config.SETTINGS_FILE):
        return False
    try:
        with open(config.SETTINGS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if 'skill_slots' in data:
            for key_str, slot_data in data['skill_slots'].items():
                slot_key = _parse_slot_key(key_str)
                if not _valid_slot(slot_key):
                    continue
                if slot_key not in config.skill_slots:
                    config.skill_slots[slot_key] = {
                        'enabled': False, 'interval': 1.0, 'last_used': 0.0,
                    }
                config.skill_slots[slot_key].update({
                    'enabled': slot_data.get('enabled', False),
                    'interval': float(slot_data.get('interval', 1.0)),
                    'last_used': 0.0,
                })

        if 'action_slots' in data:
            for name, slot_data in data['action_slots'].items():
                if name not in config.action_slots:
                    continue
                config.action_slots[name].update({
                    'enabled': slot_data.get('enabled', False),
                    'interval': float(slot_data.get('interval', 1.0)),
                    'last_used': 0.0,
                    'key': slot_data.get('key', config.action_slots[name]['key']),
                })

        if 'auto_hp_enabled' in data:
            config.auto_hp_enabled = bool(data['auto_hp_enabled'])
        if 'auto_mp_enabled' in data:
            config.auto_mp_enabled = bool(data['auto_mp_enabled'])
        if 'hp_thresholds' in data:
            config.hp_thresholds = data['hp_thresholds']
            config.hp_thresholds.sort(key=lambda x: x.get('threshold', 0), reverse=True)
        if 'mp_threshold' in data:
            config.mp_threshold = data['mp_threshold']
        if 'mp_key' in data:
            config.mp_key = data['mp_key']
        if 'hp_bar_area' in data:
            config.hp_bar_area.update(data['hp_bar_area'])
        if 'mp_bar_area' in data:
            config.mp_bar_area.update(data['mp_bar_area'])
        if 'selected_window' in data:
            config.selected_window = data['selected_window']
        if 'mob_filter_enabled' in data:
            config.mob_filter_enabled = bool(data['mob_filter_enabled'])
        if 'mob_scan_area' in data:
            config.mob_scan_area.update(data['mob_scan_area'])
        if 'mob_match_threshold' in data:
            config.mob_match_threshold = float(data['mob_match_threshold'])
        if 'mob_match_margin' in data:
            config.mob_match_margin = float(data['mob_match_margin'])
        if 'mob_templates' in data:
            config.mob_templates = list(data['mob_templates'])

        import mob_template_store
        mob_template_store.prune_missing_files()

        print(f'[settings] loaded {config.SETTINGS_FILE}')
        return True
    except Exception as exc:
        print(f'[settings] load failed: {exc}')
        return False
