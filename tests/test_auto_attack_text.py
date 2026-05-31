import auto_attack


def test_normalize_text():
    # normalize_text lowercases and removes non-letter characters; spacing is preserved.
    assert auto_attack.normalize_text("  Avara   Kara ").strip() == "avara   kara"
    assert auto_attack.normalize_text("D@dati!!") == "ddati"


def test_enemy_name_stability_requires_two_reads():
    v = auto_attack.EnemyNameValidator
    # Reset stability state
    v._stable_last_name = ''
    v._stable_last_time = 0.0
    v._stable_count = 0

    assert v.update_stability("Borangi", now=1.0) is False
    assert v.update_stability("Borangi", now=1.2) is True


def test_enemy_name_stability_resets_on_change_or_gap():
    v = auto_attack.EnemyNameValidator
    v._stable_last_name = ''
    v._stable_last_time = 0.0
    v._stable_count = 0

    assert v.update_stability("Avara Kara", now=1.0) is False
    # Different name resets count
    assert v.update_stability("Dadati", now=1.1) is False
    assert v.update_stability("Dadati", now=1.2) is True

    # Large gap resets count
    v._stable_last_name = ''
    v._stable_last_time = 0.0
    v._stable_count = 0
    assert v.update_stability("Borangi", now=1.0) is False
    assert v.update_stability("Borangi", now=5.0) is False

