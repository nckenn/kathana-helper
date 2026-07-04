"""Tests for per-profile mob template folders."""
import json
import os
import tempfile

import numpy as np
import cv2

import config
import mob_template_store
import settings_manager


def _write_png(path):
    img = np.zeros((8, 24, 3), dtype=np.uint8)
    img[:, :] = (40, 200, 40)
    cv2.imwrite(path, img)


def test_profiles_use_separate_mob_template_dirs():
    settings_manager.reset_settings_path()
    with tempfile.TemporaryDirectory() as tmp:
        profile_a = os.path.join(tmp, 'warrior.json')
        profile_b = os.path.join(tmp, 'mage.json')

        settings_manager.set_settings_path(profile_a)
        dir_a = config.MOB_TEMPLATES_DIR
        entry_a = mob_template_store.add_template(img := np.zeros((8, 24, 3), dtype=np.uint8))
        assert entry_a is not None
        assert os.path.isfile(mob_template_store.resolve_path(entry_a['file']))
        assert 'warrior' in dir_a.replace('\\', '/')

        with open(profile_b, 'w', encoding='utf-8') as f:
            json.dump({'mob_templates': []}, f)
        assert settings_manager.load_settings(path=profile_b)
        dir_b = config.MOB_TEMPLATES_DIR
        assert dir_a != dir_b
        assert 'mage' in dir_b.replace('\\', '/')
        assert config.mob_templates == []


def test_save_as_copies_templates_into_new_profile_folder():
    settings_manager.reset_settings_path()
    with tempfile.TemporaryDirectory() as tmp:
        profile_a = os.path.join(tmp, 'hunt_a.json')
        profile_b = os.path.join(tmp, 'hunt_b.json')

        settings_manager.set_settings_path(profile_a)
        entry = mob_template_store.add_template(np.zeros((8, 24, 3), dtype=np.uint8))
        config.mob_templates = [entry]
        assert settings_manager.save_settings(path=profile_a)

        dir_a = config.mob_templates_dir_for_settings(profile_a)
        assert os.path.isfile(os.path.join(dir_a, entry['file']))

        assert settings_manager.save_settings(path=profile_b)
        dir_b = config.mob_templates_dir_for_settings(profile_b)
        assert os.path.isfile(os.path.join(dir_b, entry['file']))


def test_load_migrates_legacy_flat_template_into_profile_folder():
    settings_manager.reset_settings_path()
    with tempfile.TemporaryDirectory() as tmp:
        legacy = config.legacy_mob_templates_dir()
        os.makedirs(legacy, exist_ok=True)
        legacy_file = os.path.join(legacy, 'mob_legacy01.png')
        _write_png(legacy_file)

        profile = os.path.join(tmp, 'legacy_profile.json')
        with open(profile, 'w', encoding='utf-8') as f:
            json.dump({
                'mob_templates': [{'id': 'legacy01', 'name': 'Monster 1', 'file': 'mob_legacy01.png'}],
            }, f)

        assert settings_manager.load_settings(path=profile)
        profile_dir = config.mob_templates_dir_for_settings(profile)
        migrated = os.path.join(profile_dir, 'mob_legacy01.png')
        assert os.path.isfile(migrated)
