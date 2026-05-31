"""Tests for HP number strip analysis."""
import cv2
import numpy as np
import hp_number_reader as hr

FIXTURE_NORMAL = 'tests/fixtures/buchin_normal.png'
FIXTURE_ELITE = 'tests/fixtures/buchin_elite.png'


def _hp_strip(path):
    img = cv2.imread(path)
    h = img.shape[0]
    return img[h // 2 + 2:, :]


def test_build_max_hp_signature_differs_normal_vs_elite():
    normal_sig = hr.build_max_hp_signature(_hp_strip(FIXTURE_NORMAL))
    elite_sig = hr.build_max_hp_signature(_hp_strip(FIXTURE_ELITE))
    assert normal_sig is not None
    assert elite_sig is not None
    score = hr.match_hp_signatures(normal_sig, elite_sig)
    assert score < hr.HP_SIG_MATCH_THRESHOLD


def test_build_max_hp_signature_matches_self():
    normal_sig = hr.build_max_hp_signature(_hp_strip(FIXTURE_NORMAL))
    score = hr.match_hp_signatures(normal_sig, normal_sig)
    assert score >= 0.99


def test_analyze_hp_text_has_signature():
    result = hr.analyze_hp_text(_hp_strip(FIXTURE_NORMAL))
    assert result['has_text'] is True
    assert result['sig_match_ready'] is True
    assert result['max_hp_sig'] is not None


def test_analyze_hp_text_empty_strip():
    strip = np.zeros((14, 80, 3), dtype=np.uint8)
    result = hr.analyze_hp_text(strip)
    assert result['has_text'] is False
