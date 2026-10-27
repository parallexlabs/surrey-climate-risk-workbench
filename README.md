# Surrey Climate Risk Workbench

A public-data prototype of the data side of a climate risk and resilience assessment for Surrey, British Columbia: a climate hazard data inventory, a GIS exposure package, a screening ranking of hazard exposure on a 5 by 5 matrix, a vulnerability layer, and a site screening checklist. Every figure is computed by script from saved public inputs, each recorded with its address, retrieval time and SHA-256.

It is an exposure-screening prototype for discussion; the list below says what it does not do. It was not produced, reviewed or endorsed by the City of Surrey.

## What it shows

- Where the 137,647 building footprints the City publishes, 319 service sites, 673 park natural areas and 568,322 residents meet the 200-year floodplain, the steep slope hazard lands and moderate or higher provincial wildfire threat.
- Who is most vulnerable among those exposed: a vulnerability index for 666 dissemination areas from seven 2021 Census indicators. For example, about 31% of the residents near moderate or higher wildfire threat live in the most vulnerable fifth of dissemination areas, which holds 22% of all residents.
- A screening ranking of 18 hazard and value-area pairs on a 5 by 5 matrix, with the likelihoods as editable defaults.
- A screening checklist for any point in the city: the hazards there, the ground elevation nearby, the straight-line distance to a fire hall, the area's vulnerability, and the questions a project team answers itself.
- A data inventory: what each source is, its licence, how it is used and where it stops.

## Exposure by community

| Community | Residents | Residents in floodplain (about) | Building footprints | 200-year floodplain | Ground at or below 3 m | Steep slope | Near wildfire threat | Tree canopy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Grandview | 34,474 | 1,600 | 12,788 | 11.7% | 11.9% | 7.1% | 20.5% | 15.8% |
| Whalley | 75,494 | 3,000 | 18,006 | 10.1% | 6.7% | 10.4% | 0.0% | 24.8% |
| Cloverdale | 29,142 | 900 | 8,539 | 7.8% | 7.2% | 5.3% | 0.0% | 9.3% |
| South Surrey | 55,796 | 1,100 | 19,635 | 3.8% | 3.1% | 4.5% | 5.1% | 29.9% |
| Guildford | 65,453 | 400 | 15,056 | 2.2% | 1.0% | 9.3% | 8.3% | 31.7% |
| Clayton | 44,003 | 0 | 12,023 | 1.5% | 1.5% | 4.3% | 0.0% | 17.8% |
| Newton | 159,887 | 100 | 32,265 | 0.9% | 0.9% | 4.7% | 0.0% | 15.9% |
| Fleetwood | 66,787 | 800 | 15,312 | 0.1% | 0.0% | 4.3% | 0.0% | 27.6% |
| City Centre | 37,286 | 0 | 4,023 | 0.0% | 0.0% | 3.1% | 0.0% | 20.0% |

Built 2026-10-27. Footprints are counted at their centroid; City Centre is counted once, and Whalley's figures exclude it. Residents exposed are estimated from each dissemination area's population and its share of footprints in the hazard area, which assumes equal occupancy per footprint, so they are rounded.

## Screening ranking (default likelihoods)

| Screening rank | Hazard | Value area | Exposure | Screening score | Class |
|---:|---|---|---:|---:|---|
| 1 | Riverine and coastal flooding | Drainage and water infrastructure | 40 sites | 10 | High |
| 1 | Riverine and coastal flooding | Natural areas | 286.5 ha | 10 | High |
| 1 | Steep slope instability | Natural areas | 564.1 ha | 10 | High |
| 4 | Steep slope instability | Residents | about 29,800 residents | 10 | High |
| 5 | Steep slope instability | Buildings and property | 6.07% of footprints | 8 | Medium |
| 5 | Steep slope instability | Emergency response sites | 2 sites | 8 | Medium |
| 7 | Riverine and coastal flooding | Residents | about 8,000 residents | 8 | Medium |
| 7 | Wildfire at the urban interface | Residents | about 13,000 residents | 8 | Medium |
| 7 | Wildfire at the urban interface | Emergency response sites | 2 sites | 8 | Medium |
| 7 | Wildfire at the urban interface | Schools and community services | 6 sites | 8 | Medium |
| 7 | Wildfire at the urban interface | Natural areas | 68.5 ha | 8 | Medium |
| 12 | Riverine and coastal flooding | Buildings and property | 4.03% of footprints | 6 | Medium |
| 12 | Riverine and coastal flooding | Schools and community services | 5 sites | 6 | Medium |
| 12 | Steep slope instability | Schools and community services | 4 sites | 6 | Medium |
| 15 | Wildfire at the urban interface | Buildings and property | 3.55% of footprints | 6 | Medium |
| 15 | Wildfire at the urban interface | Drainage and water infrastructure | 3 sites | 6 | Medium |
| 17 | Riverine and coastal flooding | Emergency response sites | 0 sites | 2 | No exposure found |
| 17 | Steep slope instability | Drainage and water infrastructure | 0 sites | 2 | No exposure found |

Screening score = default likelihood × exposure class (from stated bins). Rows with equal scores and data confidence share a rank. Drainage pump stations sit in the floodplain they drain, by design: their row flags them for a resilience check of power, controls and access during a flood. Much of the natural area in the floodplain and on steep slopes is riparian and ravine land that is so by nature; its consequence needs an ecological review.

## How it works

1. `scripts/fetch_layers.py` reads the City's open layers and the provincial fire threat layer one request a second, obeying each host's robots.txt, and saves every page with its provenance.
2. `scripts/extract_census.py` cuts Surrey's 666 dissemination areas and seven indicators out of the two Statistics Canada downloads (boundaries reprojected from Statistics Canada Lambert to UTM zone 10N in plain Python) and records their SHA-256. The Semiahmoo First Nation reserve, an enclave inside the City's boundary that is not part of the City, is left out, so the total equals the City's 2021 count, 568,322.
3. `src/surrey_risk/metrics.py` places each footprint, site and dissemination area, tests each against each hazard (point in polygon; a 25 m grid for the distance tests) and sums by community.
4. `src/surrey_risk/register.py` turns exposure into an exposure class through stated bins and multiplies by the default likelihood.
5. `scripts/build.py` writes `data/derived/` (metrics, ranking and inventory, in JSON and CSV) and `site/data.js`.
6. `site/` is a static page with no third-party requests.

```
make build    # recompute everything from data/raw (a few minutes)
make test     # unit tests
make serve    # view site/ locally
```

Python 3.11 or later, standard library only.

## What this does not do

- Rate consequence. The ranking counts what sits inside a mapped hazard area; its likelihoods are defaults that an assessment sets with the City for its own time horizons and scenarios.
- Model inundation, depth, damage or future climate. The floodplain is the City's mapped 200-year design event (0.5% annual exceedance); ground at or below 3 m is a screening flag for low-lying land.
- Give a landslide likelihood or runout. Steep slopes are the City's Hazard Lands classes as published.
- Give an annual wildfire probability. PSTA is a relative threat class; private land is a no-data class, so fuels there are unrated, while footprints on private land near rated public-land polygons are counted. The 200 m distance is a screening choice.
- Give fire response times. The checklist shows the straight-line distance to the nearest fire hall.
- Rate extreme heat or wildfire smoke, both current hazards in Surrey, or drought and drainage, which need layers this prototype does not have.
- Identify vulnerable individuals. The index is a simple public stand-in from seven census indicators with equal weights; the City's own vulnerability work takes its place in an assessment.

## Data licences

Contains information licensed under the Open Government License - City of Surrey, and under the Open Government Licence - British Columbia. Adapted from Statistics Canada, 2021 Census of Population; this does not constitute an endorsement by Statistics Canada of this product. See `DATA_LICENSE.md`.

## Licence

Code: Apache-2.0. ParalleX Labs Inc., Burnaby, BC.
