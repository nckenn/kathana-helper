import config


def test_effective_intervals_low_cpu_always_true():
    # low_cpu_mode is forced True by default in this repo
    assert config.low_cpu_mode is True
    assert config.get_enemy_hp_capture_interval() == 0.35
    assert config.get_hp_capture_interval() == 0.45
    assert config.get_mp_capture_interval() == 0.45
    assert config.get_bot_loop_sleep() == 0.20

