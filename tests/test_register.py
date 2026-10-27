import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from surrey_risk import register  # noqa: E402

METRICS = {
    "communities": {
        "A": {"buildings": 1000, "flood": 100, "steep": 0, "wildfire": 5,
              "natural_ha_flood": 12.0, "natural_ha_steep": 0.0, "natural_ha_wildfire": 0.0},
        "B": {"buildings": 3000, "flood": 0, "steep": 30, "wildfire": 0,
              "natural_ha_flood": 0.0, "natural_ha_steep": 160.0, "natural_ha_wildfire": 2.0},
    },
    "people_exposed": {"flood": {"A": 900, "B": 0}, "steep": {"A": 0, "B": 1200}, "wildfire": {"A": 40, "B": 0}},
    "people_exposed_most_vulnerable_fifth": {"flood": 300, "steep": 0, "wildfire": 0},
    "services": [
        {"kind": "fire halls", "community": "A", "flood": True, "steep": False, "wildfire": False},
        {"kind": "schools", "community": "B", "flood": False, "steep": True, "wildfire": False},
        {"kind": "schools", "community": "B", "flood": False, "steep": True, "wildfire": False},
    ],
}


def test_consequence_bins():
    bins = [0.5, 2, 5, 10]
    assert [register.consequence(v, bins) for v in (0, 0.5, 1.9, 2, 7, 10, 40)] == [1, 2, 2, 3, 4, 5, 5]


def test_classes_cover_the_matrix():
    assert [register.risk_class(s) for s in (1, 4, 5, 9, 10, 16, 17, 25)] == [
        "Low", "Low", "Medium", "Medium", "High", "High", "Very high", "Very high"]


def test_exposure_counts_and_shares():
    share, by = register.exposure(METRICS, "flood", "buildings")
    assert share == 2.5 and by == {"A": 100, "B": 0}
    sites, by = register.exposure(METRICS, "steep", "community")
    assert sites == 2.0 and by == {"B": 2}
    ha, _ = register.exposure(METRICS, "steep", "natural")
    assert ha == 160.0


def test_residents_row_and_note():
    rows = register.build(METRICS)["rows"]
    flood_people = next(r for r in rows if r["hazard"] == "flood" and r["value_area"] == "people")
    assert flood_people["exposure"] == 900.0 and flood_people["consequence"] == 2
    assert "33%" in flood_people["note"]


def test_ties_share_a_rank():
    rows = register.build(METRICS)["rows"]
    for a, b in zip(rows, rows[1:]):
        same = (a["class"] == register.NONE_FOUND) == (b["class"] == register.NONE_FOUND) and a["score"] == b["score"] and a["confidence"] == b["confidence"]
        assert (a["priority"] == b["priority"]) == same


def test_register_is_ranked_and_complete():
    out = register.build(METRICS)
    rows = out["rows"]
    expected = sum(1 for h in register.HAZARDS for a in register.VALUE_AREAS.values() if h in a.get("hazards", register.HAZARDS))
    assert len(rows) == expected
    rated = [r for r in rows if r["class"] != register.NONE_FOUND]
    assert all(rated[i]["score"] >= rated[i + 1]["score"] for i in range(len(rated) - 1))
    assert all(r["exposure"] == 0 for r in rows if r["class"] == register.NONE_FOUND)
    ranks = [r["priority"] for r in rows]
    assert ranks == sorted(ranks) and ranks[0] == 1
    flood_buildings = next(r for r in rows if r["hazard"] == "flood" and r["value_area"] == "buildings")
    assert flood_buildings["consequence"] == 3 and flood_buildings["score"] == 6 and flood_buildings["class"] == "Medium"
