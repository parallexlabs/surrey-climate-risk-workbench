"""Cut Surrey's dissemination areas and profile indicators out of the two Statistics Canada downloads.

    python3 scripts/extract_census.py BOUNDARY_ZIP BOUNDARY_DIR PROFILE_ZIP

The downloads themselves (about 500 MB) stay outside the repository; their SHA-256 are recorded so the cut can be
checked against the published files.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from surrey_risk import census, load  # noqa: E402

# The Semiahmoo First Nation reserve (Semiahmoo IRI, 71 residents in 2021) is an enclave inside the City's boundary
# polygon but is not part of the City; without it the total equals the City's census count, 568,322.
EXCLUDED = {"59152579": "Semiahmoo First Nation reserve (Semiahmoo IRI), not part of the City of Surrey"}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main(boundary_zip: str, boundary_dir: str, profile_zip: str) -> None:
    out = ROOT / "data" / "raw" / "statcan_2021"
    out.mkdir(parents=True, exist_ok=True)
    city = next(r for a, r in load.polygons(ROOT / "data/raw/city_20261017", "boundaries_utm") if a["NAME"] == "SURREY")
    das = {k: v for k, v in census.surrey_das(Path(boundary_dir), city).items() if k not in EXCLUDED}
    profile = census.read_profile(Path(profile_zip), set(das))
    (out / "surrey_da_boundaries_utm10.json").write_text(json.dumps({k: [[[round(x, 1), round(y, 1)] for x, y in ring] for ring in rings] for k, rings in das.items()}))
    (out / "surrey_da_profile.json").write_text(json.dumps(profile, indent=0))
    prov = {
        "boundary_file": {"name": Path(boundary_zip).name, "sha256": sha(Path(boundary_zip)), "product": "2021 Census cartographic boundary file, dissemination areas (lda_000b21a_e)"},
        "profile_file": {"name": Path(profile_zip).name, "sha256": sha(Path(profile_zip)), "product": "2021 Census Profile, comprehensive download, British Columbia (98-401-X2021006)"},
        "downloaded": "2026-10-27, by hand in a browser (www12.statcan.gc.ca allows hand reads only)",
        "licence": "Statistics Canada Open Licence",
        "indicators": census.INDICATORS,
        "excluded": EXCLUDED,
        "dissemination_areas": len(das),
        "population": sum(p.get("population", 0) for p in profile.values()),
    }
    (out / "PROVENANCE_STATCAN_2021.json").write_text(json.dumps(prov, indent=1))
    print(len(das), "dissemination areas; population", int(prov["population"]))


if __name__ == "__main__":
    main(*sys.argv[1:4])
