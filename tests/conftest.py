import os
import sys


# Ensure repo root is on sys.path so tests can import top-level modules like `config.py`.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


# Imported below the sys.path fix above so `config` resolves from the repo root.
import copy

import pytest

import config


# Per-slot feature settings live in module-level dicts on `config`, so a test that
# flips one (a bypass flag, a hotkey, an interval) leaks into every test that runs
# after it. Snapshot them around each test so ordering cannot change an outcome.
_SLOT_CONFIG_ATTRS = (
    'skill_sequence_config',
    'buffs_config',
    'skill_slots',
    'action_slots',
)


@pytest.fixture(autouse=True)
def restore_slot_config():
    saved = {name: copy.deepcopy(getattr(config, name)) for name in _SLOT_CONFIG_ATTRS}
    try:
        yield
    finally:
        for name, value in saved.items():
            # Replace contents rather than rebinding: other modules hold references.
            live = getattr(config, name)
            live.clear()
            live.update(copy.deepcopy(value))
