"""Fetch the City of Surrey open-data layers this workbench uses, one request a second.

Every request goes through the seat's host-register gate (d355_fetch.sh), so a host
without an allowed register row is refused before any byte is read. Each saved page
gets a provenance record: URL, fetch time and SHA-256.

    python3 scripts/fetch_city_layers.py data/raw
"""
import hashlib
import json
import subprocess
import sys
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

GATE = Path.home() / "Developer/showcase/amir-private/_runs/lead_tools/d355_fetch.sh"
BASE = "https://services5.arcgis.com/YRpe0VKTJytZSSIB/arcgis/rest/services"
PAGE = 2000
# polygon layers with heavy rings: smaller pages and a 1 m generalization keep each answer under the 60 s gate limit
SMALL = {"flood_elevation_areas": 100, "cfas_boundary": 100, "natural_areas": 200}

# name in this repository -> City service name (layer 0 of each FeatureServer)
LAYERS = {
    "schools": "Schools",
    "firehalls": "firehalls",
    "emergency_services": "Emergency_Services",
    "community_organizations": "CommunityBasedOrganizations",
    "pump_stations": "Drainage Pump Stations",
    "water_facilities": "Water Utility Facilities",
    "flood_elevation_areas": "FloodElevationAreas",
    "cfas_boundary": "Coastal_Flood_Adaptation_Strategy_Boundary",
    "natural_areas": "Park Natural Areas",
}


def fetch(url: str, out: Path) -> dict:
    proc = subprocess.run(["zsh", str(GATE), url, str(out)], capture_output=True, text=True)
    if proc.returncode != 0 or not out.exists():
        raise SystemExit(f"gate refused or failed: {proc.stdout.strip()} {proc.stderr.strip()}")
    body = out.read_bytes()
    return {
        "url": url,
        "fetched_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "sha256": hashlib.sha256(body).hexdigest(),
        "bytes": len(body),
    }


def main(raw_dir: str, only: list[str]) -> None:
    raw = Path(raw_dir)
    raw.mkdir(parents=True, exist_ok=True)
    provenance = []
    for name, service in LAYERS.items():
        if only and name not in only:
            continue
        size = SMALL.get(name, PAGE)
        layer = f"{BASE}/{urllib.parse.quote(service)}/FeatureServer/0"
        offset, page = 0, 0
        while True:
            query = urllib.parse.urlencode({
                "where": "1=1", "outFields": "*", "outSR": "26910", "f": "json",
                "resultOffset": offset, "resultRecordCount": size, "orderByFields": "OBJECTID",
                **({"maxAllowableOffset": "1"} if name in SMALL else {}),
            })
            out = raw / f"{name}_{page:03d}.json"
            record = fetch(f"{layer}/query?{query}", out)
            data = json.loads(out.read_text())
            if "error" in data:
                raise SystemExit(f"{name}: service error {data['error']}")
            record.update({"layer": name, "service": service, "features": len(data.get("features", []))})
            provenance.append(record)
            print(name, page, record["features"], flush=True)
            time.sleep(1)
            if not data.get("exceededTransferLimit"):
                break
            offset += size
            page += 1
    prov = raw / "PROVENANCE_CITY_20261027.json"
    old = json.loads(prov.read_text()) if prov.exists() else []
    prov.write_text(json.dumps(old + provenance, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
