import ocr_utils


def test_check_item_break_warning_matches_variants():
    assert ocr_utils.check_item_break_warning({"lines": ["Foo is about to break"], "full": "", "space": ""})
    assert ocr_utils.check_item_break_warning({"lines": ["Foo is    about   to   break"], "full": "", "space": ""})
    assert ocr_utils.check_item_break_warning({"lines": ["FOO IS ABOUT TO BREAK"], "full": "", "space": ""})


def test_check_item_break_warning_requires_keywords():
    assert not ocr_utils.check_item_break_warning({"lines": ["Foo will break"], "full": "", "space": ""})
    assert not ocr_utils.check_item_break_warning({"lines": ["about to"], "full": "", "space": ""})

