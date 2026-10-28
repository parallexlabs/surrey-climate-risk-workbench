"""Climate risk register and prioritization matrix from the exposure metrics.

Every rating rule here is a stated default that the assessment team replaces: the
likelihood of each hazard, the consequence bins for each value area and the 5 x 5
matrix classes. The page recomputes the register when any of them changes.
"""
from __future__ import annotations

HAZARDS = {
    "flood": {
        "name": "Riverine and coastal flooding",
        "layer": "City of Surrey 200-year floodplain (with ground at or below 3 m as a sea-level-rise flag)",
        "likelihood": 2,
        "likelihood_note": "The mapped event has a 0.5% chance in any year; sea level rise and heavier rain raise that over time.",
        "confidence": "High",
    },
    "steep": {
        "name": "Steep slope instability",
        "layer": "City of Surrey Hazard Lands development permit area (steep slopes and their 10 to 30 m buffer)",
        "likelihood": 2,
        "likelihood_note": "Mapped steep ground; heavier rain raises the chance of slope failure.",
        "confidence": "High",
    },
    "wildfire": {
        "name": "Wildfire at the urban interface",
        "layer": "BC Wildfire Service PSTA fire threat, moderate or high, within 200 m (public land only; private land is not rated)",
        "likelihood": 2,
        "likelihood_note": "Moderate and high provincial threat ratings exist on public land in Grandview, Guildford and South Surrey.",
        "confidence": "Medium",
    },
}

VALUE_AREAS = {
    "people": {"name": "Residents", "unit": "residents (estimated)", "bins": [100, 1000, 5000, 20000]},
    "buildings": {"name": "Buildings and property", "unit": "share of the city's buildings", "bins": [0.5, 2, 5, 10]},
    "utilities": {"name": "Drainage and water infrastructure", "unit": "sites", "bins": [0.5, 3, 10, 25],
                  "kinds": ["drainage pump stations", "water utility facilities"]},
    "community": {"name": "Schools", "unit": "sites", "bins": [0.5, 2.5, 5.5, 10.5],
                  "kinds": ["schools"]},
    "natural": {"name": "Natural areas", "unit": "hectares of park natural area", "bins": [0.5, 10, 50, 150]},
}

NOTES = {
    ("flood", "utilities"): "Drainage pump stations sit in the floodplain they drain, by design: the rating flags them for a resilience check (power, controls and access during a flood), not as misplaced.",
    ("flood", "natural"): "Much of this is riparian area that floods naturally; the consequence for ecosystem services needs an ecological review.",
    ("steep", "natural"): "Much of this is ravine forest that is steep by nature; erosion and loss of ecosystem services need an ecological review.",
}

NOT_ASSESSED = [
    {"hazard": "Extreme heat", "why": "A current hazard in Surrey; not rated here because no heat layer (surface temperature or projected hot days by area) is in the prototype. The vulnerability layer and tree canopy show where heat would harm most."},
    {"hazard": "Wildfire smoke", "why": "A current hazard; it reaches the whole city, but harm differs by person and building, which needs health and indoor-air data this prototype does not have."},
    {"hazard": "Drought and water supply", "why": "No spatial City layer; listed in the data inventory."},
    {"hazard": "Extreme rainfall and drainage", "why": "Needs the City's drainage model results; pump stations in the floodplain are counted under flooding."},
    {"hazard": "Emergency response sites and community-based organizations (all hazards)", "why": "Fire halls, emergency services and community-based organizations are shared on the City's ArcGIS Online but are not listed in its open data catalogue, so they are withdrawn until the City confirms they may be reused."},
]

CLASSES = [(4, "Low"), (9, "Medium"), (16, "High"), (25, "Very high")]
NONE_FOUND = "No exposure found"


def consequence(value: float, bins: list[float]) -> int:
    """1 to 5: one more for each bin edge the value reaches."""
    return 1 + sum(value >= edge for edge in bins)


def risk_class(score: int) -> str:
    return next(label for top, label in CLASSES if score <= top)


def exposure(metrics: dict, hazard: str, area: str) -> tuple[float, dict]:
    comms = metrics["communities"]
    if area == "people":
        by = metrics["people_exposed"][hazard]
        return float(round(sum(by.values()))), by
    if area == "buildings":
        total = sum(c["buildings"] for c in comms.values())
        exposed = {n: c[hazard] for n, c in comms.items()}
        return round(100 * sum(exposed.values()) / total, 2), exposed
    if area in ("emergency", "utilities", "community"):
        kinds = VALUE_AREAS[area]["kinds"]
        hits = [s for s in metrics["services"] if s["kind"] in kinds and s[hazard]]
        by: dict = {}
        for s in hits:
            by[s["community"]] = by.get(s["community"], 0) + 1
        return float(len(hits)), by
    if area == "natural":
        by = {n: c[f"natural_ha_{hazard}"] for n, c in comms.items()}
        return round(sum(by.values()), 1), by
    raise ValueError(area)


def people_note(metrics: dict, hazard: str) -> str:
    total = sum(metrics["people_exposed"][hazard].values())
    q5 = metrics["people_exposed_most_vulnerable_fifth"][hazard]
    share = f"{100 * q5 / total:.0f}%" if total else "none"
    return (f"Estimated from each dissemination area's population and its share of buildings in the hazard area; "
            f"{share} of them live in the most vulnerable fifth of dissemination areas (2021 Census, public reconstruction).")


def build(metrics: dict) -> dict:
    rows = []
    for hk, h in HAZARDS.items():
        for ak, a in VALUE_AREAS.items():
            if hk not in a.get("hazards", HAZARDS):
                continue
            value, by_community = exposure(metrics, hk, ak)
            c = consequence(value, a["bins"])
            score = h["likelihood"] * c
            label = risk_class(score) if value > 0 else NONE_FOUND
            rows.append({
                "hazard": hk, "hazard_name": h["name"], "value_area": ak, "value_area_name": a["name"],
                "exposure": value, "unit": a["unit"], "by_community": by_community,
                "likelihood": h["likelihood"], "consequence": c, "score": score, "class": label,
                "confidence": h["confidence"] if ak != "people" else "Medium",
                "note": NOTES.get((hk, ak), "") or (people_note(metrics, hk) if ak == "people" else ""),
            })
    rows.sort(key=lambda r: (r["class"] == NONE_FOUND, -r["score"], {"High": 0, "Medium": 1, "Low": 2}[r["confidence"]], r["hazard_name"]))
    # rows with the same score and confidence share a rank: the ordering between them carries no meaning
    rank, prev = 0, None
    for i, r in enumerate(rows, 1):
        key = (r["class"] == NONE_FOUND, r["score"], r["confidence"])
        if key != prev:
            rank, prev = i, key
        r["priority"] = rank
    return {"hazards": HAZARDS, "value_areas": VALUE_AREAS, "classes": CLASSES, "rows": rows, "not_assessed": NOT_ASSESSED}
