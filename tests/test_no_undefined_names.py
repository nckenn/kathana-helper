"""Static check that every module resolves the names it uses.

This exists because of a real regression. Splitting gui.py into ui/panels/*
moved method bodies verbatim, and they were verified byte-identical -- but the
check only proved the code moved faithfully, not that what it *calls* moved
with it. create_tooltip is defined at module level in gui.py, so
mini_overlay.create_minimized_window raised NameError the first time a user
clicked minimise: the overlay appeared and the main window never hid.

Import alone does not catch this. A name used inside a function is only looked
up when that function runs, so a module with a missing helper imports fine and
fails later, in front of the user.
"""
import pathlib

import pytest

pyflakes_api = pytest.importorskip(
    'pyflakes.api', reason='pyflakes is needed for the undefined-name check')
REPO = pathlib.Path(__file__).resolve().parent.parent

# Every first-party module. Vendored code and build output are not ours to fix.
SKIP_DIRS = {'.venv', 'build', 'dist', 'decompiled', 'tests', '__pycache__',
             'kathana_helper_lite', 'easyocr_models', 'jobs', '.git'}

MODULES = sorted(
    p for p in REPO.rglob('*.py')
    if not SKIP_DIRS & set(p.relative_to(REPO).parts)
)


class _Collect:
    """Keep only undefined-name reports; other lint noise is not this test's job."""

    def __init__(self):
        self.found = []

    def unexpectedError(self, filename, msg):
        self.found.append(f'{filename}: {msg}')

    def syntaxError(self, filename, msg, lineno, offset, text):
        self.found.append(f'{filename}:{lineno}: syntax error: {msg}')

    def flake(self, message):
        if 'undefined name' in str(message).lower():
            self.found.append(str(message))


@pytest.mark.parametrize('path', MODULES, ids=lambda p: str(p.relative_to(REPO)))
def test_module_has_no_undefined_names(path):
    collector = _Collect()
    pyflakes_api.checkPath(str(path), collector)
    assert not collector.found, '\n'.join(collector.found)


def test_the_check_actually_detects_a_missing_name(tmp_path):
    """Guard the guard: a module using an undefined name must be reported."""
    broken = tmp_path / 'broken.py'
    broken.write_text('def go():\n    return not_defined_anywhere(1)\n', encoding='utf-8')

    collector = _Collect()
    pyflakes_api.checkPath(str(broken), collector)

    assert any('not_defined_anywhere' in f for f in collector.found)
