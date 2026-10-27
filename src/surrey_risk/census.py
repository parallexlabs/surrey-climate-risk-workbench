"""Statistics Canada 2021 dissemination areas for Surrey: boundaries, a public vulnerability index, residents exposed.

Standard library only: a shapefile and dBASE reader, the Statistics Canada Lambert projection (EPSG:3347,
parameters read from the file's own .prj) inverted to NAD83 latitude and longitude, and UTM zone 10N forward.
"""
from __future__ import annotations

import csv
import io
import math
import statistics
import struct
import zipfile
from pathlib import Path

from .geom import PolygonIndex, centroid

# GRS80
A = 6378137.0
F = 1 / 298.257222101
E2 = F * (2 - F)
E = math.sqrt(E2)

# NAD83 / Statistics Canada Lambert, as in lda_000b21a_e.prj
LCC = {"lat1": 49.0, "lat2": 77.0, "lat0": 63.390675, "lon0": -91.86666666666666, "x0": 6200000.0, "y0": 3000000.0}


def _m(phi: float) -> float:
    return math.cos(phi) / math.sqrt(1 - E2 * math.sin(phi) ** 2)


def _t(phi: float) -> float:
    s = math.sin(phi)
    return math.tan(math.pi / 4 - phi / 2) / ((1 - E * s) / (1 + E * s)) ** (E / 2)


_p1, _p2, _p0 = (math.radians(LCC[k]) for k in ("lat1", "lat2", "lat0"))
_N = (math.log(_m(_p1)) - math.log(_m(_p2))) / (math.log(_t(_p1)) - math.log(_t(_p2)))
_F = _m(_p1) / (_N * _t(_p1) ** _N)
_R0 = A * _F * _t(_p0) ** _N


def lcc_to_lonlat(x: float, y: float) -> tuple[float, float]:
    dx, dy = x - LCC["x0"], _R0 - (y - LCC["y0"])
    r = math.copysign(math.hypot(dx, dy), _N)
    t = (r / (A * _F)) ** (1 / _N)
    theta = math.atan2(dx, dy) if _N > 0 else math.atan2(-dx, -dy)
    phi = math.pi / 2 - 2 * math.atan(t)
    for _ in range(10):
        s = math.sin(phi)
        phi = math.pi / 2 - 2 * math.atan(t * ((1 - E * s) / (1 + E * s)) ** (E / 2))
    return math.degrees(theta / _N) + LCC["lon0"], math.degrees(phi)


def lonlat_to_utm10(lon: float, lat: float) -> tuple[float, float]:
    """Transverse Mercator, zone 10 (central meridian 123 W), Kruger series to the sixth order."""
    k0, lon0 = 0.9996, math.radians(-123.0)
    n = F / (2 - F)
    a_ = A / (1 + n) * (1 + n ** 2 / 4 + n ** 4 / 64)
    al = [n / 2 - 2 * n ** 2 / 3 + 5 * n ** 3 / 16, 13 * n ** 2 / 48 - 3 * n ** 3 / 5, 61 * n ** 3 / 240]
    phi, lam = math.radians(lat), math.radians(lon) - lon0
    t = math.sinh(math.atanh(math.sin(phi)) - 2 * math.sqrt(n) / (1 + n) * math.atanh(2 * math.sqrt(n) / (1 + n) * math.sin(phi)))
    xi, eta = math.atan2(t, math.cos(lam)), math.atanh(math.sin(lam) / math.sqrt(1 + t * t))
    x = eta + sum(al[j] * math.cos(2 * (j + 1) * xi) * math.sinh(2 * (j + 1) * eta) for j in range(3))
    y = xi + sum(al[j] * math.sin(2 * (j + 1) * xi) * math.cosh(2 * (j + 1) * eta) for j in range(3))
    return 500000.0 + k0 * a_ * x, k0 * a_ * y


def read_dbf(path: Path) -> list[dict]:
    raw = path.read_bytes()
    nrec, hlen, rlen = struct.unpack("<IHH", raw[4:12])
    fields, pos = [], 32
    while raw[pos] != 0x0D:
        name = raw[pos:pos + 11].split(b"\0")[0].decode()
        fields.append((name, raw[pos + 16]))
        pos += 32
    out = []
    for i in range(nrec):
        rec, off = raw[hlen + i * rlen: hlen + (i + 1) * rlen], 1
        row = {}
        for name, size in fields:
            row[name] = rec[off:off + size].decode("latin-1").strip()
            off += size
        out.append(row)
    return out


def read_polygons(shp: Path, shx: Path, wanted: set[int]) -> dict[int, list[list[tuple[float, float]]]]:
    index = shx.read_bytes()[100:]
    out = {}
    with open(shp, "rb") as fh:
        for i in sorted(wanted):
            off = struct.unpack(">i", index[i * 8:i * 8 + 4])[0] * 2
            fh.seek(off + 8)
            shape_type = struct.unpack("<i", fh.read(4))[0]
            if shape_type != 5:
                continue
            fh.seek(32, 1)
            nparts, npts = struct.unpack("<ii", fh.read(8))
            parts = list(struct.unpack(f"<{nparts}i", fh.read(4 * nparts))) + [npts]
            pts = struct.unpack(f"<{2 * npts}d", fh.read(16 * npts))
            rings = []
            for a, b in zip(parts, parts[1:]):
                rings.append([lonlat_to_utm10(*lcc_to_lonlat(pts[2 * k], pts[2 * k + 1])) for k in range(a, b)])
            out[i] = rings
    return out


def surrey_das(boundary_dir: Path, city_rings: list) -> dict[str, list]:
    """Dissemination areas in Greater Vancouver (DAUID 5915...) whose centroid lies inside Surrey."""
    stem = next(boundary_dir.glob("*.shp")).with_suffix("")
    rows = read_dbf(stem.with_suffix(".dbf"))
    wanted = {i for i, r in enumerate(rows) if r.get("DAUID", "").startswith("5915")}
    polys = read_polygons(stem.with_suffix(".shp"), stem.with_suffix(".shx"), wanted)
    city = PolygonIndex(cell=5000.0)
    city.add(city_rings)
    return {rows[i]["DAUID"]: rings for i, rings in polys.items() if city.contains(*centroid(rings))}


# indicator -> characteristic ID in the 2021 Census Profile (names checked on 2026-10-27 against the file itself)
INDICATORS = {
    "population": ("1", "Population, 2021"),
    "age_0_4": ("10", "0 to 4 years"),
    "age_65_plus": ("24", "65 years and over"),
    "households": ("50", "Total - Private households by household size - 100% data"),
    "one_person": ("110", "One-person households"),
    "low_income_pct": ("345", "Prevalence of low income based on the Low-income measure, after tax (LIM-AT) (%)"),
    "no_official_language": ("387", "Neither English nor French"),
    "renter": ("1416", "Renter"),
    "recent_immigrants": ("1536", "2016 to 2021"),
}


def read_profile(zip_path: Path, dauids: set[str]) -> dict[str, dict[str, float]]:
    """Stream the BC comprehensive profile; stop once every wanted DA has been read and the block is passed."""
    out: dict[str, dict[str, float]] = {d: {} for d in dauids}
    by_id = {cid: (key, name) for key, (cid, name) in INDICATORS.items()}
    seen: set[str] = set()
    with zipfile.ZipFile(zip_path) as z:
        member = next(n for n in z.namelist() if n.lower().endswith(".csv") and "data" in n.lower())
        with z.open(member) as raw:
            reader = csv.DictReader(io.TextIOWrapper(raw, encoding="latin-1", newline=""))
            for row in reader:
                code = row.get("ALT_GEO_CODE", "")
                if code not in out:
                    if seen == dauids:
                        break
                    continue
                seen.add(code)
                hit = by_id.get(row.get("CHARACTERISTIC_ID", ""))
                if not hit:
                    continue
                key, name = hit
                if (row.get("CHARACTERISTIC_NAME") or "").strip() != name:
                    raise ValueError(f"characteristic {row['CHARACTERISTIC_ID']} is {row['CHARACTERISTIC_NAME']!r}, expected {name!r}")
                try:
                    out[code][key] = float((row.get("C1_COUNT_TOTAL") or "").strip())
                except ValueError:
                    pass  # suppressed for confidentiality or data quality; left out, never counted as zero
    return out


def vulnerability(profile: dict[str, dict[str, float]]) -> dict[str, dict]:
    """Shares per DA, z-scored across Surrey's DAs and averaged over the indicators the DA has; quintile 5 is the most vulnerable fifth."""
    shares = {}
    for d, p in profile.items():
        pop, hh = p.get("population") or 0, p.get("households") or 0
        if pop <= 0:
            continue
        def share(key: str, base: float, scale: float = 1.0):
            return p[key] * scale / base if key in p and base else None
        shares[d] = {
            "population": pop,
            "age_65_plus": share("age_65_plus", pop),
            "age_0_4": share("age_0_4", pop),
            "low_income": p["low_income_pct"] / 100 if "low_income_pct" in p else None,
            "one_person": share("one_person", hh),
            "renter": share("renter", hh),
            "no_official_language": share("no_official_language", pop),
            "recent_immigrants": share("recent_immigrants", pop),
        }
    keys = [k for k in next(iter(shares.values())) if k != "population"]
    stats = {}
    for k in keys:
        vals = [s[k] for s in shares.values() if s[k] is not None]
        stats[k] = (statistics.mean(vals), statistics.pstdev(vals) or 1.0)
    for s in shares.values():
        zs = [(s[k] - stats[k][0]) / stats[k][1] for k in keys if s[k] is not None]
        s["indicators_used"] = len(zs)
        s["index"] = sum(zs) / len(zs) if len(zs) >= 4 else None
    ranked = sorted((d for d in shares if shares[d]["index"] is not None), key=lambda d: shares[d]["index"])
    for rank, d in enumerate(ranked):
        shares[d]["quintile"] = 1 + rank * 5 // len(ranked)
    return shares
