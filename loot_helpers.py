"""Smart-loot decision helpers (pure logic, easy to test)."""
import config


def should_skip_loot(current_time=None):
    """True when looting is already in progress."""
    if current_time is None:
        import time
        current_time = time.time()
    if not config.is_looting:
        return False
    return (current_time - config.looting_start_time) < config.LOOTING_DURATION


def can_start_loot():
    """True when pick action is enabled and a key is configured."""
    pick = config.action_slots.get('pick', {})
    return bool(pick.get('enabled')) and bool(pick.get('key'))


def get_loot_key():
    """Return configured pick key or empty string."""
    return config.action_slots.get('pick', {}).get('key') or ''


def begin_loot(current_time=None):
    """Mark loot in progress and return the pick key."""
    if current_time is None:
        import time
        current_time = time.time()
    key = get_loot_key()
    config.last_smart_loot_time = current_time
    config.is_looting = True
    config.looting_start_time = current_time
    return key


def end_loot():
    """Clear loot-in-progress flag."""
    config.is_looting = False
