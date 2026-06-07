"""Unit tests for region editor coordinate helpers."""


class _FakeEditor:
    def __init__(self, scale=0.5, img_w=800, img_h=600):
        self._zoom = scale
        self._img_w = img_w
        self._img_h = img_h


def _c2w(editor, x1, y1, x2, y2):
    from ui.region_editor import RegionEditorWindow
    return RegionEditorWindow._c2w(editor, x1, y1, x2, y2)


def _w2c(editor, area):
    from ui.region_editor import RegionEditorWindow
    return RegionEditorWindow._w2c(editor, area)


def test_canvas_window_roundtrip():
    ed = _FakeEditor(scale=0.5, img_w=400, img_h=300)
    area = {'x': 40, 'y': 60, 'width': 100, 'height': 20}
    box = _w2c(ed, area)
    assert box is not None
    x, y, w, h = _c2w(ed, box[0], box[1], box[2], box[3])
    assert x == 40
    assert y == 60
    assert w == 100
    assert h == 20
