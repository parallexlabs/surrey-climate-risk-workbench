"""Exposure of buildings, services and natural areas to each mapped hazard, by community."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from . import census, load
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
        # fire halls, emergency services and community-based organizations are shared on the City's ArcGIS Online but
        # are not in its open data catalogue, so they are withdrawn until the City confirms they may be reused
        self.services = {
            "drainage pump stations": load.points(raw, "pump_stations"),
            "water utility facilities": load.points(raw, "water_facilities"),
            "schools": load.points(raw, "schools"),
        }
        stat = raw / "statcan_2021"
        self.da_rings = {k: [[(x, y) for x, y in ring] for ring in rings]
                         for k, rings in json.loads((stat / "surrey_da_boundaries_utm10.json").read_text()).items()}
        self.da_vuln = census.vulnerability(json.loads((stat / "surrey_da_profile.json").read_text()))
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

    da_idx = PolygonIndex(cell=1000.0)
    for k, rings in layers.da_rings.items():
        da_idx.add(rings, k)
    by_da = defaultdict(Counter)
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
        hits = da_idx.hits(x, y)
        if hits:
            d = by_da[da_idx.tags[hits[0]]]
            d["buildings"] += 1
            d["community:" + name] += 1
            for k, v in f.items():
                d[k] += int(v)
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

    # residents exposed: each dissemination area's population times the share of its buildings in the hazard area
    people = {h: Counter() for h in ("flood", "low", "steep", "wildfire", "interface")}
    people_q5 = Counter()
    das_out = {}
    for d, v in layers.da_vuln.items():
        c = by_da.get(d, Counter())
        home = max((k for k in c if k.startswith("community:")), key=lambda k: c[k], default="community:")[10:] or None
        das_out[d] = {"population": v["population"], "quintile": v.get("quintile"), "index": None if v.get("index") is None else round(v["index"], 3),
                      "community": home, "buildings": c["buildings"],
                      **{k: round(v[k], 4) for k in ("age_65_plus", "age_0_4", "low_income", "one_person", "renter", "no_official_language", "recent_immigrants") if v.get(k) is not None}}
        if not c["buildings"]:
            continue
        for h in people:
            share = c[h] / c["buildings"]
            people[h][home] += v["population"] * share
            if v.get("quintile") == 5:
                people_q5[h] += v["population"] * share

    out = {"communities": {}, "services": services, "dissemination_areas": das_out,
           "people_exposed": {h: {n: round(x) for n, x in people[h].items()} for h in people},
           "people_exposed_most_vulnerable_fifth": {h: round(people_q5[h]) for h in people},
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
            "residents": round(sum(v["population"] for d, v in das_out.items() if v["community"] == name)),
            "natural_ha": round(natural[name]["ha"], 1),
            "natural_ha_wildfire": round(natural[name]["ha_wildfire"], 1),
            "natural_ha_flood": round(natural[name]["ha_flood"], 1),
            "natural_ha_steep": round(natural[name]["ha_steep"], 1),
        }
    return out
