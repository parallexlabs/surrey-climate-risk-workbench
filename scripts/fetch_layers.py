"""Fetch the public layers this workbench uses: the City of Surrey's open data and the provincial fire threat rating.

One request a second, with a plain user agent that names this project. Before the first request to a host the
script reads that host's robots.txt and obeys it, as RFC 9309 says: a 4xx answer means the host sets no rules,
while a 5xx answer or an unreachable host means the script fetches nothing from it. Each saved page gets a
provenance record: URL, fetch time and SHA-256.

    python3 scripts/fetch_layers.py data/raw                  # every layer
    python3 scripts/fetch_layers.py data/raw schools pump_stations
"""
import hashlib
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import datetime
from pathlib import Path

USER_AGENT = "surrey-climate-risk-workbench/0.3 (+https://parallexlabs.ca)"
CITY = "https://services5.arcgis.com/YRpe0VKTJytZSSIB/arcgis/rest/services"
PAGE = 2000
# polygon layers with heavy rings: smaller pages and a 1 m generalization keep each answer small
SMALL = {"cfas_boundary": 100, "natural_areas": 200}

# name in this repository -> City service name (layer 0 of each FeatureServer)
LAYERS = {
    "schools": "Schools",
    "firehalls": "firehalls",
    "emergency_services": "Emergency_Services",
    "community_organizations": "CommunityBasedOrganizations",
    "pump_stations": "Drainage Pump Stations",
    "water_facilities": "Water Utility Facilities",
    "cfas_boundary": "Coastal_Flood_Adaptation_Strategy_Boundary",
    "natural_areas": "Park Natural Areas",
}
# Surrey's extent in NAD83 / UTM zone 10N, from the City's boundary layer
SURREY_BOX = "503149,5427696,523408,5452013"
PSTA = ("https://openmaps.gov.bc.ca/geo/pub/wfs?service=WFS&version=2.0.0&request=GetFeature"
        "&typeName=pub:WHSE_LAND_AND_NATURAL_RESOURCE.PROT_PSTA_FIRE_THREAT_RTG_SP&outputFormat=application/json"
        f"&srsName=EPSG:26910&bbox={SURREY_BOX},urn:ogc:def:crs:EPSG::26910&count=5000")

_robots: dict = {}
_last = 0.0


def _get(url: str) -> bytes:
    global _last
    wait = 1.0 - (time.monotonic() - _last)
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.read()
    finally:
        _last = time.monotonic()


class RobotsUnavailable(Exception):
    """The host's robots.txt could not be read (5xx or unreachable): RFC 9309 says assume complete disallow."""


def robots_rules(host: str):
    """The host's robots rules; None when it answers 4xx (no rules); raises RobotsUnavailable on 5xx or no answer."""
    try:
        body = _get(host + "/robots.txt")
    except urllib.error.HTTPError as err:
        if 400 <= err.code < 500:
            return None
        raise RobotsUnavailable(f"{host}/robots.txt answered {err.code}") from err
    except urllib.error.URLError as err:
        raise RobotsUnavailable(f"{host}/robots.txt unreachable: {err.reason}") from err
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(body.decode("utf-8", "replace").splitlines())
    return rp


def allowed(url: str) -> bool:
    parts = urllib.parse.urlsplit(url)
    host = f"{parts.scheme}://{parts.netloc}"
    if host not in _robots:
        try:
            _robots[host] = robots_rules(host)
        except RobotsUnavailable:
            _robots[host] = False
    rp = _robots[host]
    if rp is False:
        return False
    return rp is None or rp.can_fetch(USER_AGENT, url)


def save(url: str, out: Path) -> dict:
    if not allowed(url):
        raise SystemExit(f"robots.txt disallows {url}, or it could not be read (5xx or unreachable)")
    body = _get(url)
    out.write_bytes(body)
    return {"url": url, "fetched_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}


def main(raw_dir: str, only: list[str]) -> None:
    raw = Path(raw_dir)
    raw.mkdir(parents=True, exist_ok=True)
    provenance = []
    for name, service in LAYERS.items():
        if only and name not in only:
            continue
        size = SMALL.get(name, PAGE)
        layer = f"{CITY}/{urllib.parse.quote(service)}/FeatureServer/0"
        offset, page = 0, 0
        while True:
            query = urllib.parse.urlencode({
                "where": "1=1", "outFields": "*", "outSR": "26910", "f": "json",
                "resultOffset": offset, "resultRecordCount": size, "orderByFields": "OBJECTID",
                **({"maxAllowableOffset": "1"} if name in SMALL else {}),
            })
            out = raw / f"{name}_{page:03d}.json"
            record = save(f"{layer}/query?{query}", out)
            data = json.loads(out.read_text())
            if "error" in data:
                raise SystemExit(f"{name}: service error {data['error']}")
            record.update({"layer": name, "service": service, "features": len(data.get("features", []))})
            provenance.append(record)
            print(name, page, record["features"], flush=True)
            if not data.get("exceededTransferLimit"):
                break
            offset += size
            page += 1
    if not only or "psta_fire_threat" in only:
        record = save(PSTA, raw / "psta_fire_threat_000.json")
        record.update({"layer": "psta_fire_threat", "features": len(json.loads((raw / "psta_fire_threat_000.json").read_text())["features"])})
        provenance.append(record)
        print("psta_fire_threat", record["features"], flush=True)
    stamp = datetime.now().strftime("%Y%m%d")
    (raw / f"PROVENANCE_FETCH_{stamp}.json").write_text(json.dumps(provenance, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
