"""Planar geometry in metres (NAD83 / UTM zone 10N), standard library only."""
from __future__ import annotations

from dataclasses import dataclass, field

Ring = list[tuple[float, float]]


def ring_signed_area(ring: Ring) -> float:
    total = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        total += x1 * y2 - x2 * y1
    return total / 2.0


def polygon_area(rings: list[Ring]) -> float:
    """Area of a polygon whose holes run opposite to its outer rings (Esri JSON and GeoJSON both do)."""
    return abs(sum(ring_signed_area(r) for r in rings))


def point_in_rings(x: float, y: float, rings: list[Ring]) -> bool:
    """Even-odd rule over every ring, so holes and multipart outer rings both work."""
    inside = False
    for ring in rings:
        n = len(ring)
        j = n - 1
        for i in range(n):
            xi, yi = ring[i]
            xj, yj = ring[j]
            if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                inside = not inside
            j = i
    return inside


def bbox(rings: list[Ring]) -> tuple[float, float, float, float]:
    xs = [p[0] for r in rings for p in r]
    ys = [p[1] for r in rings for p in r]
    return min(xs), min(ys), max(xs), max(ys)


def centroid(rings: list[Ring]) -> tuple[float, float]:
    """Area-weighted centroid of the outer rings; falls back to the vertex mean for degenerate rings."""
    ax = ay = a = 0.0
    for ring in rings:
        for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
            cross = x1 * y2 - x2 * y1
            a += cross
            ax += (x1 + x2) * cross
            ay += (y1 + y2) * cross
    if abs(a) < 1e-9:
        pts = [p for r in rings for p in r]
        return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
    return ax / (3.0 * a), ay / (3.0 * a)


@dataclass
class PolygonIndex:
    """Grid of polygon bounding boxes; a point is tested only against polygons whose box covers its cell."""

    cell: float = 500.0
    polygons: list[list[Ring]] = field(default_factory=list)
    tags: list[object] = field(default_factory=list)
    boxes: list[tuple[float, float, float, float]] = field(default_factory=list)
    grid: dict[tuple[int, int], list[int]] = field(default_factory=dict)

    def add(self, rings: list[Ring], tag: object = None) -> None:
        k = len(self.polygons)
        self.polygons.append(rings)
        self.tags.append(tag)
        b = bbox(rings)
        self.boxes.append(b)
        for gx in range(int(b[0] // self.cell), int(b[2] // self.cell) + 1):
            for gy in range(int(b[1] // self.cell), int(b[3] // self.cell) + 1):
                self.grid.setdefault((gx, gy), []).append(k)

    def hits(self, x: float, y: float) -> list[int]:
        out = []
        for k in self.grid.get((int(x // self.cell), int(y // self.cell)), ()):
            b = self.boxes[k]
            if b[0] <= x <= b[2] and b[1] <= y <= b[3] and point_in_rings(x, y, self.polygons[k]):
                out.append(k)
        return out

    def contains(self, x: float, y: float) -> bool:
        return bool(self.hits(x, y))


def simplify(ring: Ring, tolerance: float) -> Ring:
    """Douglas-Peucker on one ring, keeping at least four points so the ring stays closed."""
    if len(ring) < 5:
        return ring

    def dp(pts: Ring) -> Ring:
        if len(pts) < 3:
            return pts
        (x1, y1), (x2, y2) = pts[0], pts[-1]
        dx, dy = x2 - x1, y2 - y1
        norm = (dx * dx + dy * dy) ** 0.5
        best, idx = -1.0, 0
        for i in range(1, len(pts) - 1):
            px, py = pts[i]
            d = abs(dy * px - dx * py + x2 * y1 - y2 * x1) / norm if norm else ((px - x1) ** 2 + (py - y1) ** 2) ** 0.5
            if d > best:
                best, idx = d, i
        if best <= tolerance:
            return [pts[0], pts[-1]]
        return dp(pts[: idx + 1])[:-1] + dp(pts[idx:])

    out = dp(list(ring))
    return out if len(out) >= 4 else ring


class Raster:
    """A boolean grid over a box, used to buffer polygons by whole cells (distance to a polygon, cheaply)."""

    def __init__(self, box: tuple[float, float, float, float], cell: float) -> None:
        self.x0, self.y0, self.cell = box[0], box[1], cell
        self.nx = int((box[2] - box[0]) // cell) + 1
        self.ny = int((box[3] - box[1]) // cell) + 1
        self.on: set[tuple[int, int]] = set()

    def burn(self, index: PolygonIndex) -> None:
        for k, b in enumerate(index.boxes):
            for ix in range(max(0, int((b[0] - self.x0) // self.cell)), min(self.nx, int((b[2] - self.x0) // self.cell) + 1)):
                cx = self.x0 + (ix + 0.5) * self.cell
                for iy in range(max(0, int((b[1] - self.y0) // self.cell)), min(self.ny, int((b[3] - self.y0) // self.cell) + 1)):
                    cy = self.y0 + (iy + 0.5) * self.cell
                    if (ix, iy) not in self.on and point_in_rings(cx, cy, index.polygons[k]):
                        self.on.add((ix, iy))

    def buffered(self, cells: int) -> set[tuple[int, int]]:
        out: set[tuple[int, int]] = set()
        r2 = cells * cells
        offsets = [(dx, dy) for dx in range(-cells, cells + 1) for dy in range(-cells, cells + 1) if dx * dx + dy * dy <= r2]
        for ix, iy in self.on:
            for dx, dy in offsets:
                out.add((ix + dx, iy + dy))
        return out

    def cell_of(self, x: float, y: float) -> tuple[int, int]:
        return int((x - self.x0) // self.cell), int((y - self.y0) // self.cell)
