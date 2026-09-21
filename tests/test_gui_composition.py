"""Guards for the BotGUI mixin composition.

gui.py was split by moving method clusters into ui/panels/* mixins. These check
the composition itself -- that every panel method still reaches BotGUI and that
no two panels define the same name -- without constructing a Tk window, so they
run headlessly in CI.
"""
import inspect

import pytest

import gui
from ui.panels.debug_window import DebugWindowMixin
from ui.panels.license_panel import LicensePanelMixin
from ui.panels.mini_overlay import MiniOverlayMixin
from ui.panels.mob_filter_panel import MobFilterPanelMixin
from ui.panels.region_pickers import RegionPickerMixin
from ui.panels.skill_selector import SkillSelectorMixin

PANELS = (
    DebugWindowMixin,
    LicensePanelMixin,
    MiniOverlayMixin,
    MobFilterPanelMixin,
    RegionPickerMixin,
    SkillSelectorMixin,
)


def _own_methods(klass):
    return {name for name, value in vars(klass).items()
            if callable(value) and not name.startswith('__')}


@pytest.mark.parametrize('panel', PANELS, ids=lambda p: p.__name__)
def test_every_panel_method_reaches_bot_gui(panel):
    for name in _own_methods(panel):
        assert hasattr(gui.BotGUI, name), f'{panel.__name__}.{name} is unreachable'


def test_panels_are_all_mixed_in():
    for panel in PANELS:
        assert panel in gui.BotGUI.__mro__, f'{panel.__name__} is not a base of BotGUI'


def test_no_two_panels_define_the_same_method():
    """A silent override is the one real hazard of splitting a class this way."""
    owners = {}
    clashes = {}
    for klass in gui.BotGUI.__mro__:
        if klass is object:
            continue
        for name in _own_methods(klass):
            if name in owners:
                clashes.setdefault(name, [owners[name]]).append(klass.__name__)
            else:
                owners[name] = klass.__name__
    assert not clashes, f'method names defined more than once: {clashes}'


def test_panel_methods_all_take_self():
    """They were moved verbatim out of a class; each must still be a method."""
    for panel in PANELS:
        for name in _own_methods(panel):
            func = vars(panel)[name]
            if isinstance(func, staticmethod):
                continue
            params = list(inspect.signature(func).parameters)
            assert params and params[0] == 'self', f'{panel.__name__}.{name}'
