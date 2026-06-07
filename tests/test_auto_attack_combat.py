"""Combat edge-case tests for auto_attack mob match logic."""
import config
import auto_attack
import mob_filter


def test_mob_match_lost_during_combat_detects_cleared_match():
    config.mob_detection_enabled = True
    config.mob_templates = [{'id': 't1', 'name': 'Goblin', 'file': 'g.png'}]
    config.mob_scan_area.update({'x': 1, 'y': 2, 'width': 40, 'height': 18})
    config.current_mob_match = {'id': 't1', 'name': 'Goblin', 'confidence': 0.9}
    config.enemy_target_time = 100.0
    config.is_looting = False

    prev = dict(config.current_mob_match)
    config.current_mob_match = None

    assert auto_attack._mob_match_lost_during_combat(prev) is True

    config.current_mob_match = prev
    assert auto_attack._mob_match_lost_during_combat(prev) is False

    config.mob_detection_enabled = False
    assert auto_attack._mob_match_lost_during_combat(prev) is False


def test_refresh_scan_combat_tolerates_single_miss(monkeypatch):
    config.mob_detection_enabled = True
    config.mob_templates = [{'id': 't1', 'name': 'Goblin', 'file': 'g.png'}]
    config.mob_scan_area.update({'x': 1, 'y': 2, 'width': 40, 'height': 18})
    config.enemy_target_time = 50.0
    config.mob_combat_miss_required = 2
    config.current_mob_match = {'id': 't1', 'name': 'Goblin', 'confidence': 0.9}
    config.current_mob_match_time = 0.0

    calls = {'n': 0}

    def fake_run_scan(hwnd):
        calls['n'] += 1
        return None

    monkeypatch.setattr(mob_filter, '_run_scan', fake_run_scan)
    result = mob_filter.refresh_scan_combat(12345)
    assert result is not None
    assert result['id'] == 't1'
    assert config.mob_match_miss_streak == 1

    result = mob_filter.refresh_scan_combat(12345)
    assert result is None
    assert config.current_mob_match is None
