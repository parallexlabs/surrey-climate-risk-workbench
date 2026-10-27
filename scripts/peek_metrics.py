"""Print the community exposure table, for a quick check while building."""
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from surrey_risk.metrics import compute  # noqa: E402

r = compute(Path(sys.argv[1] if len(sys.argv) > 1 else "data/raw"))
for name, c in r["communities"].items():
    b = c["buildings"] or 1
    pct = {k: round(100 * c[k] / b, 1) for k in ("flood", "low", "steep", "wildfire", "interface")}
    print(f"{name:13s} {c['buildings']:6d} {pct} canopy {c['canopy_pct']} natural {c['natural_ha']} ha, near fire {c['natural_ha_wildfire']} ha")
print(r["fire_classes"])
print("buildings without elevation", r["buildings_without_elevation"])
print(collections.Counter((s["kind"], bool(s["flood"] or s["low"])) for s in r["services"]))
