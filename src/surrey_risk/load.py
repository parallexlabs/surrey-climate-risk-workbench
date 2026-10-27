"""Read the saved raw pages (ArcGIS JSON from the City, GeoJSON from the Province) into plain records."""
from __future__ import annotations

import json
from pathlib import Path

from .geom import Ring, centroid


def _pages(raw: Path, stem: str) -> list[dict]:
    feats: list[dict] = []
    for page in sorted(raw.glob(f"{stem}_[0-9][0-9][0-9].json")):
        feats.extend(json.loads(page.read_text()).get("features", []))
    return feats


def _rings(geometry: dict) -> list[Ring]:
    return [[(float(x), float(y)) for x, y, *_ in ring] for ring in geometry.get("rings", [])]


def polygons(raw: Path, stem: str) -> list[tuple[dict, list[Ring]]]:
    return [(f["attributes"], _rings(f["geometry"])) for f in _pages(raw, stem) if f.get("geometry", {}).get("rings")]


def points(raw: Path, stem: str) -> list[tuple[dict, float, float]]:
    out = []
    for f in _pages(raw, stem):
        g = f.get("geometry") or f.get("centroid") or {}
        if "x" in g and "y" in g:
            out.append((f["attributes"], float(g["x"]), float(g["y"])))
        elif g.get("rings"):
            x, y = centroid(_rings(g))
            out.append((f["attributes"], x, y))
    return out


def geojson_polygons(path: Path) -> list[tuple[dict, list[Ring]]]:
    out = []
    for f in json.loads(path.read_text()).get("features", []):
        g = f.get("geometry") or {}
        parts = [g["coordinates"]] if g.get("type") == "Polygon" else g.get("coordinates", []) if g.get("type") == "MultiPolygon" else []
        rings = [[(float(x), float(y)) for x, y, *_ in ring] for part in parts for ring in part]
        if rings:
            out.append((f.get("properties", {}), rings))
    return out
