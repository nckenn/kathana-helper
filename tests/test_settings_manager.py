"""Tests for settings profile save/load."""
import json
import os
import tempfile

import config
import settings_manager


def _minimal_settings():
    return {
        'skill_slots': {},
        'action_slots': {'pick': {'enabled': False, 'interval': 1, 'last_used': 0, 'key': 'f'}},
        'mob_detection_enabled': False,
        'mob_scan_area': dict(config.mob_scan_area),
        'mob_match_threshold': config.mob_match_threshold,
        'mob_match_margin': config.mob_match_margin,
        'mob_elite_skip_enabled': False,
        'mob_templates': [],
        'auto_attack_enabled': True,
        'auto_hp_enabled': False,
        'hp_thresholds': [{'threshold': 70, 'key': '0'}],
        'auto_mp_enabled': False,
        'mp_threshold': 50,
        'mp_key': '9',
        'mouse_clicker_enabled': False,
        'mouse_clicker_interval': 1.0,
        'mouse_clicker_use_cursor': True,
        'mouse_clicker_coords': {'x': 0, 'y': 0},
        'looting_duration': config.LOOTING_DURATION,
        'auto_repair_enabled': False,
        'repair_key': 'f10',
        'break_warning_trigger_count': config.BREAK_WARNING_TRIGGER_COUNT,
        'auto_change_target_enabled': True,
        'unstuck_timeout': config.unstuck_timeout,
        'is_mage': False,
        'assist_only_enabled': False,
        'assist_key': 'f9',
        'selected_window': '',
        'buffs_config': {
            str(i): {'enabled': False, 'image_path': None, 'key': ''}
            for i in range(8)
        },
        'skill_sequence_config': {
            str(i): {'enabled': False, 'image_path': None, 'key': '', 'bypass': False}
            for i in range(8)
        },
        'hp_bar_area': dict(config.hp_bar_area),
        'mp_bar_area': dict(config.mp_bar_area),
        'target_name_area': dict(config.target_name_area),
        'target_hp_bar_area': dict(config.target_hp_bar_area),
        'system_message_area': dict(config.system_message_area),
        'skill_area': dict(config.skill_area),
        'buff_area': dict(config.buff_area),
        'low_cpu_mode': config.low_cpu_mode,
        'mob_match_shift_px': config.mob_match_shift_px,
        'buff_match_threshold': config.buff_match_threshold,
    }


def test_save_and_load_custom_profile_path():
    settings_manager.reset_settings_path()
    with tempfile.TemporaryDirectory() as tmp:
        profile_a = os.path.join(tmp, 'profile_a.json')
        profile_b = os.path.join(tmp, 'profile_b.json')

        config.mp_key = '7'
        assert settings_manager.save_settings(path=profile_a)
        assert os.path.isfile(profile_a)
        assert settings_manager.get_settings_path() == os.path.normpath(profile_a)

        config.mp_key = '3'
        assert settings_manager.save_settings(path=profile_b)

        assert settings_manager.load_settings(path=profile_a)
        assert config.mp_key == '7'
        assert settings_manager.get_settings_path() == os.path.normpath(profile_a)

        assert settings_manager.load_settings(path=profile_b)
        assert config.mp_key == '3'


def test_apply_settings_dict_roundtrip():
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8') as f:
        data = _minimal_settings()
        data['mp_key'] = '5'
        data['repair_key'] = 'f8'
        json.dump(data, f)
        path = f.name

    try:
        assert settings_manager.load_settings(path=path)
        assert config.mp_key == '5'
        assert config.repair_key == 'f8'
    finally:
        os.unlink(path)


def test_sync_gui_to_config_uses_dict_vars():
    from types import SimpleNamespace
    from ui.settings_overlays import sync_gui_to_config

    class FakeVar:
        def __init__(self, value):
            self._value = value

        def get(self):
            return self._value

        def strip(self):
            return str(self._value).strip()

    gui = SimpleNamespace(
        buffs_vars={0: FakeVar(True), 1: FakeVar(False)},
        buffs_key_vars={0: FakeVar('f1'), 1: FakeVar('f2')},
        skill_sequence_vars={0: FakeVar(True)},
        skill_sequence_bypass_vars={0: FakeVar(True)},
        skill_sequence_key_vars={0: FakeVar('1')},
    )

    sync_gui_to_config(gui)

    assert config.buffs_config[0]['enabled'] is True
    assert config.buffs_config[1]['enabled'] is False
    assert config.buffs_config[0]['key'] == 'f1'
    assert config.skill_sequence_config[0]['enabled'] is True
    assert config.skill_sequence_config[0]['bypass'] is True
    assert config.skill_sequence_config[0]['key'] == '1'
