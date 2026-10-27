"""Check the projection chain and count Surrey's dissemination areas in the boundary file.

    python3 scripts/check_census_geometry.py BOUNDARY_DIR
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from surrey_risk import census, load  # noqa: E402
from surrey_risk.geom import centroid, polygon_area  # noqa: E402

# Surrey City Hall, 13450 104 Avenue, about 49.1907 N, 122.8492 W [CONFIRM to the metre]: expect roughly 511,000 E, 5,448,700 N
print("city hall utm", [round(v) for v in census.lonlat_to_utm10(-122.8492, 49.1907)])
# the projection's own origin must map back to its stated latitude and central meridian
print("lcc origin", [round(v, 6) for v in census.lcc_to_lonlat(census.LCC["x0"], census.LCC["y0"])])
city = next(r for a, r in load.polygons(ROOT / "data/raw/city_20261017", "boundaries_utm") if a["NAME"] == "SURREY")
das = census.surrey_das(Path(sys.argv[1]), city)
area = sum(polygon_area(r) for r in das.values()) / 1e6
print(len(das), "dissemination areas;", round(area, 1), "km2 (city", round(polygon_area(city) / 1e6, 1), "km2)")
first = next(iter(das.items()))
print("example", first[0], [round(v) for v in centroid(first[1])])
