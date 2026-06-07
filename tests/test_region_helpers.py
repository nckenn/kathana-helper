"""Tests for region preflight checks."""
import config
import region_helpers


def test_bot_start_preflight_requires_hp_mp():
    config.hp_bar_area.update({'x': 0, 'y': 0, 'width': 0, 'height': 0})
    config.mp_bar_area.update({'x': 0, 'y': 0, 'width': 0, 'height': 0})
    issues = region_helpers.bot_start_preflight_issues()
    assert any('HP and MP' in item for item in issues)


def test_bot_start_preflight_mob_filter_needs_scan_area():
    config.hp_bar_area.update({'x': 1, 'y': 2, 'width': 10, 'height': 8})
    config.mp_bar_area.update({'x': 1, 'y': 20, 'width': 10, 'height': 8})
    config.mob_detection_enabled = True
    config.mob_templates = []
    config.target_name_area.update({'x': 0, 'y': 0, 'width': 0, 'height': 0})
    config.mob_scan_area.update({'x': 0, 'y': 0, 'width': 0, 'height': 0})

    issues = region_helpers.bot_start_preflight_issues()
    assert any('Enemy Name' in item for item in issues)
    assert any('learn at least one' in item.lower() for item in issues)
