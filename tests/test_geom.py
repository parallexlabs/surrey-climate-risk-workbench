import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from surrey_risk.geom import PolygonIndex, Raster, centroid, point_in_rings, polygon_area, simplify  # noqa: E402

SQUARE = [(0.0, 0.0), (0.0, 10.0), (10.0, 10.0), (10.0, 0.0)]          # clockwise, as Esri writes outer rings
HOLE = [(4.0, 4.0), (6.0, 4.0), (6.0, 6.0), (4.0, 6.0)]               # counter-clockwise


def test_area_with_hole():
    assert polygon_area([SQUARE]) == 100.0
    assert polygon_area([SQUARE, HOLE]) == 96.0


def test_point_in_polygon_respects_holes():
    assert point_in_rings(1, 1, [SQUARE, HOLE])
    assert not point_in_rings(5, 5, [SQUARE, HOLE])
    assert not point_in_rings(11, 5, [SQUARE])


def test_index_returns_only_true_hits():
    idx = PolygonIndex(cell=4.0)
    idx.add([SQUARE], "a")
    idx.add([[(20.0, 20.0), (20.0, 30.0), (30.0, 30.0), (30.0, 20.0)]], "b")
    assert [idx.tags[k] for k in idx.hits(5, 1)] == ["a"]
    assert idx.hits(15, 15) == []
    assert idx.contains(25, 25)


def test_centroid_of_square():
    assert centroid([SQUARE]) == (5.0, 5.0)


def test_simplify_keeps_a_closed_shape():
    wiggly = [(float(x), 0.01 * (x % 2)) for x in range(50)] + [(49.0, 10.0), (0.0, 10.0)]
    out = simplify(wiggly, 0.5)
    assert len(out) >= 4 and len(out) < len(wiggly)


def test_raster_buffer_reaches_neighbours():
    idx = PolygonIndex(cell=50.0)
    idx.add([[(0.0, 0.0), (0.0, 25.0), (25.0, 25.0), (25.0, 0.0)]])
    r = Raster((0.0, 0.0, 200.0, 200.0), 25.0)
    r.burn(idx)
    assert r.on == {(0, 0)}
    near = r.buffered(2)
    assert r.cell_of(60, 10) in near and r.cell_of(110, 10) not in near
