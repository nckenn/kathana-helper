import types

import capture_regions
import config


class DummyCalibrator:
    hp_position = (10, 20)
    hp_dimensions = (100, 10)
    mp_position = (200, 300)
    mp_dimensions = (120, 12)


def test_union_rect_basic():
    rects = [(10, 20, 100, 30), (50, 40, 80, 50)]
    assert capture_regions.union_rect(rects) == (10, 20, 120, 70)


def test_compute_capture_rects_includes_skill_and_buff_strip(monkeypatch):
    monkeypatch.setattr(config, "area_skills", (400, 500, 600, 560))
    monkeypatch.setattr(
        config,
        "system_message_area",
        {"x": 500, "y": 700, "width": 200, "height": 100},
    )

    rects = capture_regions.compute_capture_rects(DummyCalibrator())
    # HP, MP, enemy strip, skills, buff strip
    assert len(rects) >= 5

