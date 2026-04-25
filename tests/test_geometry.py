import pytest

from autompw.geometry import Anchor, BBox, bbox_from_anchor


def test_bbox_from_center_anchor():
    assert bbox_from_anchor((10, 20), (4, 6), Anchor.CENTER) == BBox(8, 17, 12, 23)


def test_bbox_from_top_right_anchor():
    assert bbox_from_anchor((10, 20), (4, 6), Anchor.TOP_RIGHT) == BBox(6, 14, 10, 20)


def test_overlap_and_spacing():
    a = BBox(0, 0, 10, 10)
    b = BBox(15, 0, 20, 10)
    c = BBox(9, 9, 12, 12)
    assert not a.overlaps(b)
    assert a.spacing_to(b) == pytest.approx(5)
    assert a.overlaps(c)
    assert a.spacing_to(c) == pytest.approx(0)
