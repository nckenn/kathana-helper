"""Smart-loot decision helpers (pure logic, easy to test)."""
import config


def loot_lockout_remaining(current_time=None):
    """Seconds left in the post-kill loot lockout (0 when not looting or expired)."""
    if not config.is_looting:
        return 0.0
    if current_time is None:
        import time
        current_time = time.time()
    elapsed = current_time - config.looting_start_time
    return max(0.0, float(config.LOOTING_DURATION) - elapsed)


def should_skip_loot(current_time=None):
    """True when loot should not start again yet."""
    if current_time is None:
        import time
        current_time = time.time()
    if config.is_looting and loot_lockout_remaining(current_time) > 0:
        return True
    cooldown = float(getattr(config, 'SMART_LOOT_COOLDOWN', 0.2))
    if current_time - float(getattr(config, 'last_smart_loot_time', 0)) < cooldown:
        return True
    return False


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


def clear_expired_loot_lockout(current_time=None):
    """Clear loot flag when lockout expired. Returns True if loot just finished."""
    if current_time is None:
        import time
        current_time = time.time()
    if not config.is_looting:
        return False
    if loot_lockout_remaining(current_time) > 0:
        return False
    config.is_looting = False
    return True


def end_loot():
    """Clear loot-in-progress flag."""
    config.is_looting = False
