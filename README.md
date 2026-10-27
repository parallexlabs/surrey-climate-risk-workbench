# Surrey Climate Risk Workbench

A public-data prototype of the data side of a climate risk and resilience assessment for Surrey, British Columbia: a climate hazard data inventory, a GIS exposure package, a climate risk register with a prioritization matrix, and a site screening checklist. Every figure is computed by script from saved public inputs, each recorded with its address, retrieval time and SHA-256.

It is a prototype for discussion, not a climate risk assessment. It was not produced, reviewed or endorsed by the City of Surrey.

## What it shows

- Where the City's 137,647 buildings, 319 service sites and 673 park natural areas meet the 200-year floodplain, the steep slope hazard lands and moderate or high provincial wildfire threat.
- A risk register of 13 hazard and value-area pairs, rated on a 5 by 5 likelihood and consequence matrix, with the likelihoods as editable defaults.
- A screening checklist for any point in the city: the hazards there, the ground elevation nearby, the distance to a fire hall, and the questions a project team answers itself.
- A data inventory: what each source is, its licence, how it is used and where it stops.

## Exposure by community

| Community | Buildings | 200-year floodplain | Ground at or below 3 m | Steep slope | Near wildfire threat | Near natural areas | Tree canopy |
|---|---:|---:|---:|---:|---:|---:|---:|
| Grandview | 12,788 | 11.7% | 11.9% | 7.1% | 20.5% | 15.0% | 15.8% |
| Whalley | 18,006 | 10.1% | 6.7% | 10.4% | 0.0% | 20.5% | 24.8% |
| Cloverdale | 8,539 | 7.8% | 7.2% | 5.3% | 0.0% | 9.3% | 9.3% |
| South Surrey | 19,635 | 3.8% | 3.1% | 4.5% | 5.1% | 26.8% | 29.9% |
| Guildford | 15,056 | 2.2% | 1.0% | 9.3% | 8.3% | 24.7% | 31.7% |
| Clayton | 12,023 | 1.5% | 1.5% | 4.3% | 0.0% | 12.1% | 17.8% |
| Newton | 32,265 | 0.9% | 0.9% | 4.7% | 0.0% | 21.0% | 15.9% |
| Fleetwood | 15,312 | 0.1% | 0.0% | 4.3% | 0.0% | 24.8% | 27.6% |
| City Centre | 4,023 | 0.0% | 0.0% | 3.1% | 0.0% | 7.8% | 20.0% |

Built 2026-10-27. Buildings are counted at their footprint centroid; City Centre is counted once, not again inside Whalley.

## Risk register (default likelihoods)

| Rank | Hazard | Value area | Exposure | Score | Class |
|---:|---|---|---:|---:|---|
| 1 | Riverine and coastal flooding | Drainage and water infrastructure | 40 sites | 10 | High |
| 2 | Steep slope instability | Buildings and property | 6.07% | 8 | Medium |
| 3 | Steep slope instability | Emergency response sites | 2 sites | 8 | Medium |
| 4 | Wildfire at the urban interface | Emergency response sites | 2 sites | 8 | Medium |
| 5 | Wildfire at the urban interface | Schools and community services | 6 sites | 8 | Medium |
| 6 | Wildfire at the urban interface | Natural areas | 68.5 ha | 8 | Medium |
| 7 | Riverine and coastal flooding | Buildings and property | 4.03% | 6 | Medium |
| 8 | Riverine and coastal flooding | Schools and community services | 5 sites | 6 | Medium |
| 9 | Steep slope instability | Schools and community services | 4 sites | 6 | Medium |
| 10 | Wildfire at the urban interface | Buildings and property | 3.55% | 6 | Medium |
| 11 | Wildfire at the urban interface | Drainage and water infrastructure | 3 sites | 6 | Medium |
| 12 | Riverine and coastal flooding | Emergency response sites | 0 sites | 2 | Low |
| 13 | Steep slope instability | Drainage and water infrastructure | 0 sites | 2 | Low |

Drainage pump stations sit in the floodplain they drain, by design: the first row flags them for a resilience check, not as misplaced. Natural areas are rated only for wildfire, because flooding and steep ground are the natural state of riparian areas and ravines.

## How it works

1. `scripts/fetch_city_layers.py` reads the City's open layers one request a second, through the seat's host-register gate, and saves every page with its provenance. The provincial wildfire layer comes from the BC Geographic Warehouse the same way.
2. `src/surrey_risk/metrics.py` places each building and site, tests it against each hazard (point in polygon; a 25 m grid for the distance tests) and sums by community.
3. `src/surrey_risk/register.py` turns exposure into consequence through stated bins and multiplies by the default likelihood.
4. `scripts/build.py` writes `data/derived/` (metrics, register and inventory, in JSON and CSV) and `site/data.js`.
5. `site/` is a static page with no third-party requests.

```
make build    # recompute everything from data/raw (about three minutes)
make test     # unit tests
make serve    # view site/ locally
```

Python 3.11 or later, standard library only.

## Limits

- No flood depth, damage, duration or future-climate likelihood is modelled. The floodplain is the City's mapped 200-year layer.
- People are not in this version: dissemination-area census data come next, and in an assessment the City's own Social Vulnerability Index replaces any public reconstruction.
- The provincial wildfire layer does not rate private land, so interface exposure on private land is not measured.
- Likelihoods are stated defaults for demonstration; an assessment sets them with the City for its chosen time horizons and scenarios.

## Data licences

Contains information licensed under the Open Government License - City of Surrey, and under the Open Government Licence - British Columbia. See `DATA_LICENSE.md`.

## Licence

Code: Apache-2.0. ParalleX Labs Inc., Burnaby, BC.
