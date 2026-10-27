"""Exposure of buildings, services and natural areas to each mapped hazard, by community."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from . import load
from .geom import PolygonIndex, Raster, centroid, polygon_area

COMMUNITIES = ["CITY CENTRE", "CLAYTON", "CLOVERDALE", "FLEETWOOD", "GRANDVIEW", "GUILDFORD", "NEWTON", "SOUTH SURREY", "WHALLEY"]
LOW_GROUND_M = 3.0          # published ground elevation at or below this, datum as published by the City
WILDFIRE_NEAR_M = 200       # distance to a moderate or high provincial fire-threat polygon
INTERFACE_NEAR_M = 100      # distance to a park natural area
CELL_M = 25                 # raster cell for the two distance tests


class Layers:
    def __init__(self, raw: Path) -> None:
        city17 = raw / "city_20261017"
        self.boundaries = [(a["NAME"], r) for a, r in load.polygons(city17, "boundaries_utm")]
        self.floodplain = PolygonIndex()
        for _, r in load.polygons(city17, "floodplain_utm"):
            self.floodplain.add(r)
        self.steep = PolygonIndex()
        for a, r in load.polygons(city17, "steep_utm"):
            # the layer's one "Flood prone area" polygon is the 200-year floodplain itself; counting it would double the flood
            if a.get("DESCRIPTION") != "Flood prone area":
                self.steep.add(r, a.get("DESCRIPTION"))
        # cfas_boundary is published inverted (a 294,075 km2 outer ring with the study area as its hole), so it is
        # recorded in the inventory and not used as a hazard area; the 200-year floodplain carries the flood test
        self.fire_mod = PolygonIndex()
        self.fire_classes: Counter = Counter()
        for p, r in load.geojson_polygons(raw / "psta_fire_threat_000.json"):
            cls = int(p.get("FIRE_THREAT_CLASS", -9))
            self.fire_classes[(p.get("FIRE_THREAT_CLASS_DESC"), cls)] += 1
            if cls >= 4:
                self.fire_mod.add(r, cls)
        self.natural = PolygonIndex()
        self.natural_records = []
        for a, r in load.polygons(raw, "natural_areas"):
            self.natural.add(r, a.get("NATURAL_AREA_TYPE"))
            self.natural_records.append((a, r))
        self.buildings = load.points(city17, "buildings_centroids")
        self.services = {
            "fire halls": load.points(raw, "firehalls"),
            "emergency services": load.points(raw, "emergency_services"),
            "drainage pump stations": load.points(raw, "pump_stations"),
            "water utility facilities": load.points(raw, "water_facilities"),
            "schools": load.points(raw, "schools"),
            "community-based organizations": load.points(raw, "community_organizations"),
        }
        self.canopy = {}
        for name in COMMUNITIES:
            path = city17 / f"canopy_{name.lower().replace(' ', '_')}.json"
            if path.exists():
                self.canopy[name] = json.loads(path.read_text())


def community_index(layers: Layers) -> tuple[PolygonIndex, dict[str, float]]:
    """Communities from smallest to largest, so City Centre wins over the Whalley polygon that contains it."""
    parts = [(n, r, polygon_area(r)) for n, r in layers.boundaries if n in COMMUNITIES]
    parts.sort(key=lambda t: t[2])
    idx = PolygonIndex(cell=1000.0)
    for n, r, _ in parts:
        idx.add(r, n)
    return idx, {n: a for n, _, a in parts}


def assign(idx: PolygonIndex, x: float, y: float) -> str | None:
    hits = idx.hits(x, y)
    return idx.tags[min(hits)] if hits else None


def near_raster(index: PolygonIndex, box: tuple[float, float, float, float], metres: int) -> tuple[Raster, set]:
    r = Raster(box, CELL_M)
    r.burn(index)
    return r, r.buffered(max(1, round(metres / CELL_M)))


def compute(raw: Path) -> dict:
    layers = Layers(raw)
    cidx, carea = community_index(layers)
    city = next(r for n, r in layers.boundaries if n == "SURREY")
    xs = [p[0] for ring in city for p in ring]
    ys = [p[1] for ring in city for p in ring]
    box = (min(xs) - 500, min(ys) - 500, max(xs) + 500, max(ys) + 500)
    fire_r, fire_near = near_raster(layers.fire_mod, box, WILDFIRE_NEAR_M)
    nat_r, nat_near = near_raster(layers.natural, box, INTERFACE_NEAR_M)

    def flags(x: float, y: float, elev: float | None) -> dict:
        return {
            "flood": layers.floodplain.contains(x, y),
            "low": elev is not None and elev <= LOW_GROUND_M,
            "steep": layers.steep.contains(x, y),
            "wildfire": fire_r.cell_of(x, y) in fire_near,
            "interface": nat_r.cell_of(x, y) in nat_near,
        }

    b = defaultdict(Counter)
    no_elev = 0
    for attrs, x, y in layers.buildings:
        name = assign(cidx, x, y)
        if not name:
            continue
        elev = attrs.get("GROUND_ELEVATION")
        if elev is None:
            no_elev += 1
        f = flags(x, y, elev)
        b[name]["buildings"] += 1
        for k, v in f.items():
            b[name][k] += int(v)
        if attrs.get("CIVIC_FACILITY") == "Yes":
            b[name]["civic"] += 1
            for k, v in f.items():
                b[name]["civic_" + k] += int(v)

    services = []
    for kind, recs in layers.services.items():
        for attrs, x, y in recs:
            name = assign(cidx, x, y)
            elev = attrs.get("GROUND_ELEVATION")
            label = attrs.get("NAME") or attrs.get("TITLE") or attrs.get("LOCATION") or attrs.get("FACILITYID") or ""
            services.append({"kind": kind, "name": str(label).strip(), "community": name,
                             "x": round(x, 1), "y": round(y, 1), **flags(x, y, elev)})

    natural = defaultdict(lambda: Counter())
    for attrs, rings in layers.natural_records:
        x, y = centroid(rings)
        name = assign(cidx, x, y)
        ha = polygon_area(rings) / 10_000
        natural[name]["ha"] += ha
        if fire_r.cell_of(x, y) in fire_near:
            natural[name]["ha_wildfire"] += ha
        if layers.floodplain.contains(x, y):
            natural[name]["ha_flood"] += ha
        if layers.steep.contains(x, y):
            natural[name]["ha_steep"] += ha

    # City Centre lies inside the Whalley polygon: Whalley's area and canopy exclude it, as its buildings do
    canopy_m2 = {n: float((layers.canopy.get(n, {}).get("features") or [{}])[0].get("attributes", {}).get("total") or 0) for n in COMMUNITIES}
    area_m2 = dict(carea)
    if "WHALLEY" in area_m2 and "CITY CENTRE" in area_m2:
        area_m2["WHALLEY"] -= area_m2["CITY CENTRE"]
        canopy_m2["WHALLEY"] -= canopy_m2["CITY CENTRE"]

    out = {"communities": {}, "services": services,
           "fire_classes": {f"{d} ({c})": n for (d, c), n in sorted(layers.fire_classes.items(), key=lambda t: t[0][1])},
           "buildings_without_elevation": no_elev,
           "parameters": {"low_ground_m": LOW_GROUND_M, "wildfire_near_m": WILDFIRE_NEAR_M,
                          "interface_near_m": INTERFACE_NEAR_M, "raster_cell_m": CELL_M}}
    for name in COMMUNITIES:
        c = b[name]
        out["communities"][name] = {
            "area_km2": round(area_m2.get(name, 0) / 1e6, 2),
            "canopy_pct": round(100 * canopy_m2[name] / area_m2[name], 1) if area_m2.get(name) else None,
            **{k: c[k] for k in ("buildings", "flood", "low", "steep", "wildfire", "interface", "civic",
                                 "civic_flood", "civic_low", "civic_steep", "civic_wildfire", "civic_interface")},
            "natural_ha": round(natural[name]["ha"], 1),
            "natural_ha_wildfire": round(natural[name]["ha_wildfire"], 1),
            "natural_ha_flood": round(natural[name]["ha_flood"], 1),
            "natural_ha_steep": round(natural[name]["ha_steep"], 1),
        }
    return out
