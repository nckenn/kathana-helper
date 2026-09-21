"""Tests for where each region picker stores its result.

The five region pickers were ~181-line copies differing in about 20 lines.
Collapsing them into one _pick_region left the varying part as a small
_commit_* method each -- which is exactly the part that must not change, since
it decides what lands in config and what the user is told.

The commits are pure: they take a rectangle, write it somewhere, and return the
summary string. So they can be driven directly, without Tk or a game window.
"""
import copy

import pytest

import config
from ui.panels.region_pickers import RegionPickerMixin


class _Var:
    """Stands in for a tk.StringVar."""

    def __init__(self):
        self.value = None

    def set(self, value):
        self.value = value


class _Picker(RegionPickerMixin):
    """A bare mixin instance: the commits touch only vars and config."""

    def __init__(self):
        for prefix in ('hp', 'mp', 'enemy_hp'):
            for suffix in ('x', 'y', 'width', 'height', 'coords'):
                setattr(self, f'{prefix}_{suffix}_var', _Var())
        for suffix in ('coords', 'width', 'height'):
            setattr(self, f'mob_{suffix}_var', _Var())


@pytest.fixture
def picker():
    areas = ('hp_bar_area', 'mp_bar_area', 'target_hp_bar_area',
             'target_name_area', 'system_message_area')
    saved = {name: copy.deepcopy(getattr(config, name)) for name in areas}
    try:
        yield _Picker()
    finally:
        for name, value in saved.items():
            getattr(config, name).update(value)


@pytest.mark.parametrize('commit,area,prefix', [
    ('_commit_hp_area', 'hp_bar_area', 'hp'),
    ('_commit_mp_area', 'mp_bar_area', 'mp'),
    ('_commit_enemy_hp_area', 'target_hp_bar_area', 'enemy_hp'),
])
def test_bar_pickers_store_the_top_left_corner(picker, commit, area, prefix):
    summary = getattr(picker, commit)(12, 34, 200, 20)

    assert getattr(config, area)['x'] == 12
    assert getattr(config, area)['y'] == 34
    assert getattr(config, area)['width'] == 200
    assert getattr(config, area)['height'] == 20

    assert getattr(picker, f'{prefix}_x_var').value == '12'
    assert getattr(picker, f'{prefix}_y_var').value == '34'
    assert getattr(picker, f'{prefix}_width_var').value == '200'
    assert getattr(picker, f'{prefix}_height_var').value == '20'
    assert getattr(picker, f'{prefix}_coords_var').value == '12,34'

    assert summary == 'Position: (12, 34)\nSize: 200x20 pixels'


def test_mob_picker_stores_the_centre_not_the_corner(picker):
    """The odd one out, and the reason each commit stayed separate."""
    summary = picker._commit_mob_area(100, 200, 50, 20)

    assert config.target_name_area['x'] == 125   # 100 + 50 // 2
    assert config.target_name_area['y'] == 210   # 200 + 20 // 2
    assert config.target_name_area['width'] == 50
    assert config.target_name_area['height'] == 20

    assert picker.mob_coords_var.value == '125,210'
    assert picker.mob_width_var.value == '50'
    assert picker.mob_height_var.value == '20'

    assert summary == 'Center: (125, 210)\nSize: 50x20 pixels'


def test_mob_centre_rounds_the_same_way_for_odd_sizes(picker):
    picker._commit_mob_area(0, 0, 7, 5)
    assert config.target_name_area['x'] == 3     # floor, as before
    assert config.target_name_area['y'] == 2


def test_system_message_picker_writes_config_only(picker):
    summary = picker._commit_system_message_area(5, 6, 300, 40)

    assert config.system_message_area['x'] == 5
    assert config.system_message_area['y'] == 6
    assert config.system_message_area['width'] == 300
    assert config.system_message_area['height'] == 40
    assert summary == 'Top-left: (5, 6)\nSize: 300x40 pixels'


def test_each_picker_passes_its_own_commit_and_colours(monkeypatch):
    """The public methods must still differ in the ways that matter."""
    calls = []

    def fake_pick(self, what, title, hint_color, outline, commit):
        calls.append((what, title, hint_color, outline, commit.__name__))

    monkeypatch.setattr(RegionPickerMixin, '_pick_region', fake_pick)
    p = _Picker()
    for method in ('pick_hp_coordinates', 'pick_mp_coordinates',
                   'pick_enemy_hp_coordinates', 'pick_mob_coordinates',
                   'pick_system_message_coordinates'):
        getattr(p, method)()

    assert calls == [
        ('HP bar', 'HP Bar Area', 'yellow', 'red', '_commit_hp_area'),
        ('MP bar', 'MP Bar Area', 'cyan', 'blue', '_commit_mp_area'),
        ('enemy HP bar', 'Enemy HP Bar Area', 'orange', 'orange', '_commit_enemy_hp_area'),
        ('mob name', 'Mob Detection Area', 'lime', 'white', '_commit_mob_area'),
        ('system message', 'System Message Area', 'orange', 'orange',
         '_commit_system_message_area'),
    ]


def test_license_date_helpers_match_the_old_inline_parsing():
    """The six copies each did fromisoformat -> '%B %d, %Y', raw value on failure."""
    from ui.widgets import format_license_date, license_days_left

    assert format_license_date('2027-01-24T00:00:00') == 'January 24, 2027'
    assert format_license_date('2026-09-21') == 'September 21, 2026'

    # Unparseable input fell through to the raw string before; it still does.
    assert format_license_date('Never') == 'Never'
    assert format_license_date('') == ''
    assert format_license_date(None, 'Unknown') == 'Unknown'

    # days_left reports None instead of raising, and the callers' try/except
    # still catches the TypeError that comparing None produces.
    assert isinstance(license_days_left('2027-01-24T00:00:00'), int)
    assert license_days_left('Never') is None
    with pytest.raises(TypeError):
        _ = license_days_left('Never') < 0
