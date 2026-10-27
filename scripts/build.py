"""Build every derived file and the site's data from data/raw.

    python3 scripts/build.py            # recompute the exposure metrics (about three minutes)
    python3 scripts/build.py --cached   # reuse data/derived/metrics.json
"""
import csv
import json
import statistics
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from surrey_risk import inventory, load, register  # noqa: E402
from surrey_risk.geom import simplify  # noqa: E402
from surrey_risk.metrics import COMMUNITIES, compute  # noqa: E402

RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "derived"
SITE = ROOT / "site"


def frame():
    city = next(r for a, r in load.polygons(RAW / "city_20261017", "boundaries_utm") if a["NAME"] == "SURREY")
    xs = [p[0] for ring in city for p in ring]
    ys = [p[1] for ring in city for p in ring]
    return min(xs) - 300, max(ys) + 300, max(xs) - min(xs) + 600, max(ys) - min(ys) + 600


def to_svg(rings, x0, y1, tol):
    out = []
    for ring in rings:
        r = simplify(ring, tol) if tol else ring
        out.append([[round(x - x0), round(y1 - y)] for x, y in r])
    return out


def main(cached: bool) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    mpath = OUT / "metrics.json"
    if cached and mpath.exists():
        metrics = json.loads(mpath.read_text())
    else:
        metrics = compute(RAW)
        metrics["built_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        mpath.write_text(json.dumps(metrics, indent=1))
    reg = register.build(metrics)
    (OUT / "register.json").write_text(json.dumps(reg, indent=1))
    with open(OUT / "register.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["priority", "hazard", "value area", "exposure", "unit", "likelihood", "consequence", "score", "class", "confidence"])
        for r in reg["rows"]:
            w.writerow([r["priority"], r["hazard_name"], r["value_area_name"], r["exposure"], r["unit"],
                        r["likelihood"], r["consequence"], r["score"], r["class"], r["confidence"]])
    (OUT / "inventory.json").write_text(json.dumps(inventory.RECORDS, indent=1))
    with open(OUT / "inventory.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(inventory.RECORDS[0].keys()))
        w.writeheader()
        w.writerows(inventory.RECORDS)

    x0, y1, width, height = frame()
    city17 = RAW / "city_20261017"
    layers = {
        "communities": [{"name": a["NAME"], "rings": to_svg(r, x0, y1, 15)} for a, r in load.polygons(city17, "boundaries_utm") if a["NAME"] in COMMUNITIES],
        "city": [to_svg(r, x0, y1, 15) for a, r in load.polygons(city17, "boundaries_utm") if a["NAME"] == "SURREY"],
        "floodplain": [to_svg(r, x0, y1, 8) for _, r in load.polygons(city17, "floodplain_utm")],
        "steep": [to_svg(r, x0, y1, 8) for a, r in load.polygons(city17, "steep_utm") if a.get("DESCRIPTION") != "Flood prone area"],
        "wildfire": [{"cls": int(p["FIRE_THREAT_CLASS"]), "rings": to_svg(r, x0, y1, 8)}
                     for p, r in load.geojson_polygons(RAW / "psta_fire_threat_000.json") if int(p.get("FIRE_THREAT_CLASS", -9)) >= 4],
        "natural": [to_svg(r, x0, y1, 8) for _, r in load.polygons(RAW, "natural_areas")],
        "dykes": [[round(x - x0), round(y1 - y)] for _, x, y in load.points(city17, "dykes_utm")],
    }
    services = [dict(s, sx=round(s["x"] - x0), sy=round(y1 - s["y"])) for s in metrics["services"]]
    # coarse ground elevation for the screening tool: the median of building elevations in each 250 m cell
    cells: dict = {}
    for attrs, x, y in load.points(city17, "buildings_centroids"):
        e = attrs.get("GROUND_ELEVATION")
        if e is not None:
            cells.setdefault((int((x - x0) // 250), int((y1 - y) // 250)), []).append(float(e))
    elev = {f"{i},{j}": round(statistics.median(v), 1) for (i, j), v in cells.items() if len(v) >= 3}
    payload = {
        "frame": {"width": round(width), "height": round(height), "x0": round(x0), "y1": round(y1)},
        "layers": layers, "services": services, "elevation_grid_m": 250, "elevation": elev,
        "metrics": metrics, "register": reg, "inventory": inventory.RECORDS,
    }
    SITE.mkdir(exist_ok=True)
    (SITE / "data.js").write_text("window.WORKBENCH = " + json.dumps(payload, separators=(",", ":")) + ";\n")
    print("site/data.js", round((SITE / "data.js").stat().st_size / 1e6, 2), "MB;", len(reg["rows"]), "register rows")


if __name__ == "__main__":
    main("--cached" in sys.argv)
