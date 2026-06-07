"""Tests for CV mob filter."""
import cv2
import numpy as np
import config
import mob_filter
import mob_template_store
import hp_number_reader


def _make_entry(entry_id='t1'):
    return {'id': entry_id, 'name': 'Goblin', 'file': f'mob_{entry_id}.png'}


def _white_text_template():
    """Synthetic target strip: corner name/level text + red HP row."""
    template = np.zeros((35, 40, 3), dtype=np.uint8)
    template[2:16, 2:16] = (245, 245, 245)
    template[2:16, 28:38] = (245, 245, 245)
    template[22:26, 12:34] = (0, 0, 200)
    return template


def test_normalize_rejects_center_terrain_blob():
    template = np.zeros((35, 210, 3), dtype=np.uint8)
    template[2:16, 5:50] = (245, 245, 245)
    template[2:16, 150:200] = (245, 245, 245)
    template[22:26, 20:190] = (0, 0, 200)
    noisy = template.copy()
    noisy[3:15, 95:118] = (220, 220, 220)
    norm = mob_filter.normalize_for_match(noisy)
    assert int(norm[3:15, 95:118].max()) == 0
    assert int(norm[2:16, 8:25].max()) == 255


def test_match_in_image_exact_size():
    template = _white_text_template()
    scan = template.copy()
    entry = _make_entry()
    prep = mob_filter.normalize_for_match(template)
    mob_filter._template_cache['prep_t1'] = prep
    match = mob_filter.match_in_image(scan, templates=[entry])
    assert match is not None
    assert match['name'] == 'Goblin'
    mob_filter.invalidate_cache()


def test_match_in_image_below_threshold():
    template = _white_text_template()
    scan = np.zeros((35, 40, 3), dtype=np.uint8)
    entry = _make_entry()
    prep = mob_filter.normalize_for_match(template)
    mob_filter._template_cache['prep_t1'] = prep
    match = mob_filter.match_in_image(scan, templates=[entry])
    assert match is None
    mob_filter.invalidate_cache()


def test_normalize_match_bg_invariant():
    """Terrain behind transparent nameplate should not change the match signature."""
    fixture = cv2.imread('tests/fixtures/buchin_normal.png')
    assert fixture is not None
    fixture = mob_filter._crop_name_bar(fixture)
    norm_a = mob_filter.normalize_for_match(fixture)
    noisy = fixture.copy()
    rng = np.random.default_rng(0)
    noise = rng.integers(0, 120, noisy.shape, dtype=np.uint8)
    # Only corrupt pixels that normalize to background (transparent terrain).
    bg = norm_a == 0
    for c in range(3):
        noisy[:, :, c][bg] = noise[:, :, c][bg]
    norm_b = mob_filter.normalize_for_match(noisy)
    score = mob_filter._match_score_gray(norm_a, norm_b)
    assert score >= 0.75


def test_normalize_crops_tall_capture_to_name_bar():
    """Tall captures (old templates) only use the top name row."""
    tall = np.zeros((35, 210, 3), dtype=np.uint8)
    tall[4:12, 10:30] = (245, 245, 245)
    tall[22:26, 12:34] = (0, 0, 200)
    norm = mob_filter.normalize_for_match(tall)
    assert norm.shape[0] == hp_number_reader.NAME_AREA_HEIGHT
    assert int(norm[4:12, 10:30].max()) == 255


def test_butu_fixture_pair_matches():
    """Regression: two live captures of the same mob must match (was 0% before fix)."""
    import os
    learn = cv2.imread(os.path.join('tests', 'fixtures', 'butu_learn.png'))
    live = cv2.imread(os.path.join('tests', 'fixtures', 'butu_live.png'))
    if learn is None or live is None:
        return
    tmpl = mob_filter.normalize_for_match(learn)
    mob_filter._template_cache['prep_butu'] = tmpl
    entry = {'id': 'butu', 'name': 'Monster 1', 'file': 'f.png', 'normalized': True}
    match = mob_filter.match_in_image(live, templates=[entry])
    score = mob_filter._match_score_gray(mob_filter._prepare_scan_image(live), tmpl)
    assert score >= 0.80
    assert match is not None


def test_butu_user_samples_and_height_mismatch():
    """User Butu crops + 18px template vs 35px live scan must still match."""
    import os
    a = cv2.imread(os.path.join('tests', 'fixtures', 'butu_user_a.png'))
    b = cv2.imread(os.path.join('tests', 'fixtures', 'butu_user_b.png'))
    full = cv2.imread(os.path.join('tests', 'fixtures', 'butu_learn.png'))
    if a is None or b is None:
        return
    tmpl = mob_filter.normalize_for_match(a)
    mob_filter._template_cache['prep_butu_a'] = tmpl
    entry = {'id': 'butu_a', 'name': 'Butu', 'file': 'a.png', 'normalized': True}
    match = mob_filter.match_in_image(b, templates=[entry])
    assert match is not None
    assert match['confidence'] >= config.mob_match_threshold
    if full is not None and full.shape[0] > a.shape[0]:
        match_full = mob_filter.match_in_image(full, templates=[entry])
        assert match_full is not None
    mob_filter.invalidate_cache()


def test_shared_prefix_mobs_do_not_cross_match():
    """Different mobs with a shared name prefix must not cross-match (Ban* regression)."""
    import os
    z_path = os.path.join('tests', 'fixtures', 'ban_zangkun.png')
    d_path = os.path.join('tests', 'fixtures', 'ban_dopang.png')
    zangkun = cv2.imread(z_path)
    dopang = cv2.imread(d_path)
    if zangkun is None or dopang is None:
        return
    nz = mob_filter.normalize_for_match(zangkun)
    nd = mob_filter.normalize_for_match(dopang)
    cross = mob_filter._match_score_gray(nz, nd)
    assert cross < 0.78, f'Ban* cross-match too high: {cross:.0%}'
    self_z = mob_filter._match_score_gray(nz, nz)
    assert self_z >= config.mob_match_threshold


def test_dissimilar_mob_names_score_low():
    """Different mob names must not match from shared level text or short-template bias."""
    import os
    chandi = cv2.imread(os.path.join('tests', 'fixtures', 'chandi_user.png'))
    butu = cv2.imread(os.path.join('tests', 'fixtures', 'butu_user_a.png'))
    assert chandi is not None and butu is not None
    nc = mob_filter.normalize_for_match(chandi)
    nb = mob_filter.normalize_for_match(butu)
    cross = mob_filter._match_score_gray(nc, nb)
    assert cross < 0.55


def test_different_normalized_templates_score_low(monkeypatch):
    """Different name layouts must not score ~80% from shared black background."""
    monkeypatch.setattr(config, 'mob_match_shift_px', 0)
    tmpl_a = np.zeros((35, 210), dtype=np.uint8)
    tmpl_b = np.zeros((35, 210), dtype=np.uint8)
    tmpl_a[4:14, 10:28] = 255
    tmpl_b[4:14, 55:73] = 255
    cross = mob_filter._match_score_gray(tmpl_b, tmpl_a)
    self_score = mob_filter._match_score_gray(tmpl_a, tmpl_a)
    assert cross < 0.55
    assert self_score >= 0.95


def test_match_fixture_self():
    fixture = cv2.imread('tests/fixtures/buchin_normal.png')
    entry = {'id': 'buchin', 'name': 'Buchin', 'file': 'buchin.png', 'normalized': True}
    prep = mob_filter.normalize_for_match(fixture)
    mob_filter._template_cache['prep_buchin'] = prep
    match = mob_filter.match_in_image(fixture, templates=[entry])
    assert match is not None
    assert match['confidence'] >= config.mob_match_threshold
    mob_filter.invalidate_cache()


def test_clear_match_clears_target_names():
    config.current_mob_match = {'id': 't1', 'name': 'Goblin'}
    config.current_target_mob = 'Goblin'
    config.current_enemy_name = 'Goblin'
    mob_filter.clear_match()
    assert config.current_mob_match is None
    assert config.current_target_mob is None
    assert config.current_enemy_name is None


def test_should_allow_action_gating():
    config.mob_detection_enabled = True
    config.mob_scan_area = {'x': 0, 'y': 0, 'width': 10, 'height': 10}
    config.mob_templates = [_make_entry()]
    config.current_mob_match = {'id': 't1', 'name': 'Goblin', 'confidence': 0.9}
    assert mob_filter.should_allow_action('attack', 123) is True
    assert mob_filter.should_allow_action('target', 123) is False
    assert mob_filter.should_allow_combat(123) is True
    config.current_mob_match = None
    assert mob_filter.should_allow_action('attack', 123) is False
    assert mob_filter.should_allow_action('target', 123) is True
    assert mob_filter.should_allow_combat(123) is False
    config.mob_detection_enabled = False


def test_is_active_requires_templates_and_region():
    config.mob_detection_enabled = True
    config.mob_templates = []
    config.mob_scan_area = {'x': 0, 'y': 0, 'width': 0, 'height': 0}
    config.calibrator = None
    assert mob_filter.is_active() is False
    config.mob_templates = [_make_entry()]
    assert mob_filter.is_active() is False
    config.mob_scan_area = {'x': 0, 'y': 0, 'width': 10, 'height': 10}
    assert mob_filter.is_active() is True
    config.mob_detection_enabled = False


def test_renumber_templates_after_remove():
    config.mob_templates = [
        {'id': 'a', 'name': 'Monster 1', 'file': 'a.png'},
        {'id': 'b', 'name': 'Monster 2', 'file': 'b.png'},
    ]
    mob_template_store.remove_template('a')
    assert [e['name'] for e in config.mob_templates] == ['Monster 1']
    config.mob_templates.append({'id': 'c', 'name': 'Monster 9', 'file': 'c.png'})
    mob_template_store.renumber_templates()
    assert [e['name'] for e in config.mob_templates] == ['Monster 1', 'Monster 2']
    config.mob_templates = []


def test_get_scan_area_is_name_bar_only():
    class FakeCal:
        enemy_name_area = (105, 9, 210, 18)
        mp_position = None

    config.calibrator = FakeCal()
    config.mob_scan_area = {'x': 0, 'y': 0, 'width': 0, 'height': 0}
    config.target_name_area = {'x': 0, 'y': 0, 'width': 0, 'height': 0}
    area = mob_filter.get_scan_area()
    assert area == {
        'x': 0,
        'y': 0,
        'width': 210,
        'height': hp_number_reader.NAME_AREA_HEIGHT,
    }
    config.calibrator = None


def test_get_scan_area_uses_full_picked_height():
    config.calibrator = None
    config.target_name_area = {'x': 0, 'y': 0, 'width': 0, 'height': 0}
    config.mob_scan_area = {'x': 1, 'y': 2, 'width': 210, 'height': 35}
    area = mob_filter.get_scan_area()
    assert area['height'] == 35


def test_prepare_template_for_storage_keeps_capture_size():
    img = np.zeros((28, 200, 3), dtype=np.uint8)
    img[5:20, 10:80] = (255, 255, 255)
    saved = mob_filter.prepare_template_for_storage(img)
    assert saved is not None
    assert saved.shape[0] == 28 and saved.shape[1] == 200


def test_get_scan_area_prefers_target_name_over_mob_scan():
    config.calibrator = None
    config.target_name_area = {'x': 10, 'y': 20, 'width': 200, 'height': 18}
    config.mob_scan_area = {'x': 99, 'y': 88, 'width': 50, 'height': 18}
    area = mob_filter.get_scan_area()
    assert area['x'] == 10 and area['y'] == 20 and area['width'] == 200


def test_is_elite_variant_signature_mismatch(monkeypatch):
    entry = {
        'id': 't1',
        'name': 'Goblin',
        'file': 'mob_t1.png',
        'hp_max_file': 'hpmax_t1.png',
    }
    ref = hp_number_reader.build_max_hp_signature(
        cv2.imread('tests/fixtures/buchin_normal.png')[17:, :]
    )
    elite = hp_number_reader.build_max_hp_signature(
        cv2.imread('tests/fixtures/buchin_elite.png')[18:, :]
    )

    monkeypatch.setattr(mob_filter.mob_template_store, 'load_hp_max_sig', lambda _e: ref)
    monkeypatch.setattr(
        mob_filter.hp_number_reader,
        'capture_enemy_hp_text_area',
        lambda _hwnd, screen=None: np.zeros((14, 80, 3), dtype=np.uint8),
    )
    monkeypatch.setattr(
        mob_filter.hp_number_reader,
        'build_max_hp_signature',
        lambda _strip: elite,
    )
    assert mob_filter.is_elite_variant(1, entry) is True

    monkeypatch.setattr(
        mob_filter.hp_number_reader,
        'build_max_hp_signature',
        lambda _strip: ref.copy(),
    )
    assert mob_filter.is_elite_variant(1, entry) is False
    config.mob_elite_skip_enabled = False


def test_apply_elite_filter_drops_elite_match(monkeypatch):
    config.mob_elite_skip_enabled = True
    config.mob_templates = [{
        'id': 't1',
        'name': 'Goblin',
        'file': 'mob_t1.png',
        'hp_digit_count': 4,
        'hp_text_span': 28,
    }]
    match = {'id': 't1', 'name': 'Goblin', 'confidence': 0.95}

    monkeypatch.setattr(
        mob_filter,
        'is_elite_variant',
        lambda _hwnd, _entry, screen=None: True,
    )
    assert mob_filter.apply_elite_filter(1, match) is None

    monkeypatch.setattr(
        mob_filter,
        'is_elite_variant',
        lambda _hwnd, _entry, screen=None: False,
    )
    assert mob_filter.apply_elite_filter(1, match) == match
    config.mob_elite_skip_enabled = False
    config.mob_templates = []
