"""Tests that one failing subsystem cannot kill the bot thread.

bot_loop() runs on a daemon thread nothing joins or inspects, so an unhandled
exception used to end the run silently while the GUI still said "Running".
These drive the real loop with its subsystems stubbed out, stopping it from the
patched sleep so each test runs a fixed number of ticks.
"""
import types

import pytest

import bot_logic
import config


class _FakeWindow:
    handle = 1234


@pytest.fixture
def loop_env(monkeypatch):
    """Run bot_loop with every subsystem stubbed and a bounded tick count."""
    monkeypatch.setattr(config, 'connected_window', _FakeWindow(), raising=False)
    monkeypatch.setattr(config, 'bot_regions_ready', lambda: True)
    monkeypatch.setattr(config, 'buffs_manager', None, raising=False)
    monkeypatch.setattr(config, 'autopots_instance',
                        types.SimpleNamespace(check_auto_pots=lambda: None), raising=False)
    monkeypatch.setattr(config, 'force_initial_target', False, raising=False)
    for flag in ('auto_hp_enabled', 'auto_mp_enabled', 'auto_attack_enabled',
                 'assist_only_enabled', 'auto_change_target_enabled',
                 'auto_rotate_enabled', 'auto_repair_enabled',
                 'mouse_clicker_enabled', 'is_looting', 'is_buffing'):
        monkeypatch.setattr(config, flag, False, raising=False)
    monkeypatch.setattr(bot_logic.mob_filter, 'is_active', lambda: False)

    ticks = {'count': 0, 'limit': 3}

    def stop_after_limit(_seconds):
        ticks['count'] += 1
        if ticks['count'] >= ticks['limit']:
            config.bot_running = False

    monkeypatch.setattr(bot_logic.time, 'sleep', stop_after_limit)

    bot_logic.reset_tick_error_state()
    config.bot_running = True
    try:
        yield ticks
    finally:
        config.bot_running = False
        bot_logic.reset_tick_error_state()


def _capture_logs(monkeypatch):
    logged = []
    monkeypatch.setattr(bot_logic.logger, 'error',
                        lambda msg, mod='App': logged.append(('error', msg)))
    monkeypatch.setattr(bot_logic.logger, 'info',
                        lambda msg, mod='App': logged.append(('info', msg)))
    return logged


def test_a_failing_subsystem_does_not_kill_the_loop(loop_env, monkeypatch):
    logged = _capture_logs(monkeypatch)
    calls = {'n': 0}

    def boom():
        calls['n'] += 1
        raise RuntimeError('subsystem exploded')

    monkeypatch.setattr(bot_logic, 'check_skill_slots', boom)

    bot_logic.bot_loop()  # must return normally, not propagate

    # Every tick ran despite the failure, rather than the thread dying on tick 1.
    assert calls['n'] == loop_env['limit']
    errors = [msg for level, msg in logged if level == 'error']
    assert errors, 'the failure should be logged, not swallowed'
    assert 'subsystem exploded' in errors[0]
    assert 'Traceback' in errors[0], 'first report should carry the traceback'


def test_a_repeating_failure_is_throttled(loop_env, monkeypatch):
    """A permanent fault must not flood the log at loop speed."""
    logged = _capture_logs(monkeypatch)
    loop_env['limit'] = 50
    monkeypatch.setattr(bot_logic, 'check_skill_slots',
                        lambda: (_ for _ in ()).throw(RuntimeError('same every time')))

    bot_logic.bot_loop()

    errors = [msg for level, msg in logged if level == 'error']
    assert len(errors) == 1, f'50 identical failures logged {len(errors)} times'


def test_a_different_failure_is_always_reported(loop_env, monkeypatch):
    """Throttling must not hide a new fault behind an ongoing one."""
    logged = _capture_logs(monkeypatch)
    loop_env['limit'] = 4
    seq = iter([RuntimeError('first fault'), RuntimeError('first fault'),
                ValueError('second fault'), ValueError('second fault')])

    def raise_next():
        raise next(seq)

    monkeypatch.setattr(bot_logic, 'check_skill_slots', raise_next)

    bot_logic.bot_loop()

    errors = [msg for level, msg in logged if level == 'error']
    assert len(errors) == 2
    assert 'first fault' in errors[0]
    assert 'second fault' in errors[1]


def test_recovery_is_reported_and_clears_the_streak(loop_env, monkeypatch):
    logged = _capture_logs(monkeypatch)
    loop_env['limit'] = 4
    calls = {'n': 0}

    def fail_twice_then_work():
        calls['n'] += 1
        if calls['n'] <= 2:
            raise RuntimeError('transient')

    monkeypatch.setattr(bot_logic, 'check_skill_slots', fail_twice_then_work)

    bot_logic.bot_loop()

    infos = [msg for level, msg in logged if level == 'info']
    assert any('Recovered after 2 failed loops' in msg for msg in infos)
    assert bot_logic._tick_error_state['consecutive'] == 0


def test_reset_bot_state_clears_a_failure_streak():
    bot_logic._tick_error_state['signature'] = ('RuntimeError', 'x', None)
    bot_logic._tick_error_state['consecutive'] = 7

    bot_logic.reset_tick_error_state()

    assert bot_logic._tick_error_state['signature'] is None
    assert bot_logic._tick_error_state['consecutive'] == 0
