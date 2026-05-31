import json
import os
import tempfile
import config
import settings_manager


def test_settings_round_trip():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, 'settings_lite.json')
        config.SETTINGS_FILE = path
        config.auto_hp_enabled = True
        config.mp_key = '8'
        config.hp_bar_area.update({'x': 10, 'y': 20, 'width': 100, 'height': 8})
        config.skill_slots[1]['enabled'] = True
        config.skill_slots[1]['interval'] = 2.5
        config.action_slots['attack']['enabled'] = True
        config.action_slots['attack']['interval'] = 1.5

        assert settings_manager.save_settings()

        config.auto_hp_enabled = False
        config.mp_key = '0'
        config.skill_slots[1]['enabled'] = False

        assert settings_manager.load_settings()
        assert config.auto_hp_enabled is True
        assert config.mp_key == '8'
        assert config.hp_bar_area['width'] == 100
        assert config.skill_slots[1]['enabled'] is True
        assert config.skill_slots[1]['interval'] == 2.5
        assert config.action_slots['attack']['enabled'] is True
        assert config.action_slots['attack']['interval'] == 1.5

        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        assert 'skill_slots' in data
        assert data['mp_key'] == '8'
