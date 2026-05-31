"""Tests for CV mob filter."""
import numpy as np
import config
import mob_filter
import mob_template_store


def _make_entry(entry_id='t1'):
    return {'id': entry_id, 'name': 'Goblin', 'file': f'mob_{entry_id}.png'}


def test_match_in_image_exact_size():
    template = np.zeros((20, 40, 3), dtype=np.uint8)
    template[5:15, 10:30] = (0, 255, 0)
    scan = template.copy()
    entry = _make_entry()
    mob_filter._template_cache['t1'] = template
    match = mob_filter.match_in_image(scan, templates=[entry])
    assert match is not None
    assert match['name'] == 'Goblin'
    mob_filter.invalidate_cache()


def test_match_in_image_below_threshold():
    template = np.zeros((20, 40, 3), dtype=np.uint8)
    template[5:15, 10:30] = (0, 255, 0)
    scan = np.zeros((20, 40, 3), dtype=np.uint8)
    entry = _make_entry()
    mob_filter._template_cache['t1'] = template
    match = mob_filter.match_in_image(scan, templates=[entry])
    assert match is None
    mob_filter.invalidate_cache()


def test_should_allow_action_gating():
    config.mob_detection_enabled = True
    config.mob_scan_area = {'x': 0, 'y': 0, 'width': 10, 'height': 10}
    config.mob_templates = [_make_entry()]
    config.current_mob_match = {'id': 't1', 'name': 'Goblin', 'confidence': 0.9}
    assert mob_filter.should_allow_action('attack', 123) is True
    assert mob_filter.should_allow_action('target', 123) is False
    assert mob_filter.should_allow_combat(123) is True
    config.current_mob_match = None
    assert mob_filter.should_allow_action('attack', 123) is False
    assert mob_filter.should_allow_action('target', 123) is True
    assert mob_filter.should_allow_combat(123) is False
    config.mob_detection_enabled = False


def test_is_active_requires_templates_and_region():
    config.mob_detection_enabled = True
    config.mob_templates = []
    config.mob_scan_area = {'x': 0, 'y': 0, 'width': 0, 'height': 0}
    config.calibrator = None
    assert mob_filter.is_active() is False
    config.mob_templates = [_make_entry()]
    assert mob_filter.is_active() is False
    config.mob_scan_area = {'x': 0, 'y': 0, 'width': 10, 'height': 10}
    assert mob_filter.is_active() is True
    config.mob_detection_enabled = False


def test_renumber_templates_after_remove():
    config.mob_templates = [
        {'id': 'a', 'name': 'Monster 1', 'file': 'a.png'},
        {'id': 'b', 'name': 'Monster 2', 'file': 'b.png'},
    ]
    mob_template_store.remove_template('a')
    assert [e['name'] for e in config.mob_templates] == ['Monster 1']
    config.mob_templates.append({'id': 'c', 'name': 'Monster 9', 'file': 'c.png'})
    mob_template_store.renumber_templates()
    assert [e['name'] for e in config.mob_templates] == ['Monster 1', 'Monster 2']
    config.mob_templates = []


def test_get_scan_area_from_calibration():
    class FakeCal:
        enemy_name_area = (105, 9, 210, 18)

    config.calibrator = FakeCal()
    area = mob_filter.get_scan_area()
    assert area == {'x': 0, 'y': 0, 'width': 210, 'height': 18}
    config.calibrator = None
