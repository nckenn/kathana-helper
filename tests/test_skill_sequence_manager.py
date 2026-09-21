"""Tests for the strict skill-sequence rotation.

`_run_rotation` normally reads the skill bar with OpenCV; here `_match_skill` is
replaced with a scripted lookup so the ordering logic can be tested without a
screen capture. `area` is likewise a stand-in, since only `_match_skill` reads it.
"""
import config
from skill_sequence_manager import SkillSequenceManager


class _FakeArea:
    """Stands in for the skill-bar crop; big enough to pass the size guards."""
    shape = (64, 512, 3)
    size = 64 * 512 * 3


class _FakeTemplate:
    shape = (32, 32, 3)


def _make_manager(num_skills, ready, skip_on_cooldown=()):
    """Build a manager over `num_skills` slots with a scripted ready-state map.

    `ready` maps slot index -> bool (is the icon visible, i.e. off cooldown).
    `skip_on_cooldown` lists the slots that have "Skip if on cooldown" ticked.
    Returns (manager, valid_skills, pressed) where `pressed` records key presses.
    """
    mgr = SkillSequenceManager(num_skills=num_skills)
    valid_skills = [(i, f'skill{i}.png') for i in range(num_skills)]
    pressed = []

    for i in range(num_skills):
        config.skill_sequence_config[i]['bypass'] = i in skip_on_cooldown

    mgr._match_skill = lambda area, tmpl, path: (
        ready[int(path[5:-4])], (0, 0), 1.0,
    )
    mgr._press_skill = lambda original_idx: pressed.append(original_idx)
    return mgr, valid_skills, pressed


def _patch_template(monkeypatch):
    """Every slot resolves to a usable template."""
    import skill_sequence_manager as ssm
    monkeypatch.setattr(ssm.template_cache, 'get_template', lambda path, flags: _FakeTemplate())
    monkeypatch.setattr(ssm, 'cv2', type('cv2', (), {'IMREAD_COLOR': 1}), raising=False)


def _tick(mgr, valid_skills, n):
    mgr._run_rotation(valid_skills, n, _FakeArea())


def test_rotation_waits_for_a_skill_on_cooldown(monkeypatch):
    """Strict order: slot 1 down and not skippable means nothing else casts."""
    _patch_template(monkeypatch)
    # Slot 0 on cooldown, 1 and 2 ready — but none may jump the queue.
    mgr, skills, pressed = _make_manager(3, ready={0: False, 1: True, 2: True})

    for _ in range(3):
        _tick(mgr, skills, 3)

    assert pressed == []
    assert mgr.skill_sequence_index == 0  # parked on the skill it is waiting for


def test_rotation_skips_a_slot_that_opted_in(monkeypatch):
    """Slot 0 is down but ticked "skip if cd", so the lap moves on to slot 1."""
    _patch_template(monkeypatch)
    mgr, skills, pressed = _make_manager(
        3, ready={0: False, 1: True, 2: True}, skip_on_cooldown=(0,),
    )

    _tick(mgr, skills, 3)

    assert pressed == [1]
    assert mgr.skill_sequence_index == 1


def test_rotation_advances_once_the_cast_is_confirmed(monkeypatch):
    """Pressing holds the slot; the icon going dark releases it to the next one."""
    _patch_template(monkeypatch)
    ready = {0: True, 1: True, 2: True}
    mgr, skills, pressed = _make_manager(3, ready=ready)

    _tick(mgr, skills, 3)
    assert pressed == [0] and mgr.skill_sequence_index == 0

    # Icon still lit -> still the same skill, pressed again.
    _tick(mgr, skills, 3)
    assert pressed == [0, 0] and mgr.skill_sequence_index == 0

    # Icon goes dark -> cast landed, rotation moves to slot 1 in the same tick.
    ready[0] = False
    _tick(mgr, skills, 3)
    assert pressed == [0, 0, 1]
    assert mgr.skill_sequence_index == 1


def test_rotation_gives_up_on_a_ready_skill_that_never_casts(monkeypatch):
    """A lit icon that never goes dark must not wedge the rotation forever."""
    _patch_template(monkeypatch)
    mgr, skills, pressed = _make_manager(2, ready={0: True, 1: True})

    for _ in range(SkillSequenceManager.MAX_CAST_ATTEMPTS):
        _tick(mgr, skills, 2)

    assert pressed == [0] * SkillSequenceManager.MAX_CAST_ATTEMPTS
    assert mgr.skill_sequence_index == 1  # escaped to the next slot

    _tick(mgr, skills, 2)
    assert pressed[-1] == 1


def test_rotation_scans_past_several_skipped_slots_in_one_tick(monkeypatch):
    """A run of skipped cooldowns should not cost a tick each."""
    _patch_template(monkeypatch)
    mgr, skills, pressed = _make_manager(
        4,
        ready={0: False, 1: False, 2: False, 3: True},
        skip_on_cooldown=(0, 1, 2),
    )

    _tick(mgr, skills, 4)

    assert pressed == [3]
    assert mgr.skill_sequence_index == 3


def test_rotation_presses_at_most_one_key_per_tick(monkeypatch):
    """Even with everything ready, a tick fires a single skill."""
    _patch_template(monkeypatch)
    mgr, skills, pressed = _make_manager(4, ready={i: True for i in range(4)})

    _tick(mgr, skills, 4)

    assert pressed == [0]
