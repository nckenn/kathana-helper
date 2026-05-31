import time
import config
import action_timer


def test_action_interval(monkeypatch):
    sent = []
    monkeypatch.setattr('action_timer.input_handler.send_input', lambda k: sent.append(k))
    for name in config.action_slots:
        config.action_slots[name]['enabled'] = False
    config.action_slots['target']['enabled'] = True
    config.action_slots['target']['interval'] = 0.2
    config.action_slots['target']['last_used'] = 0.0
    config.action_slots['target']['key'] = 'e'

    action_timer.check_action_slots()
    assert sent == ['e']

    sent.clear()
    action_timer.check_action_slots()
    assert sent == []

    time.sleep(0.25)
    action_timer.check_action_slots()
    assert sent == ['e']
