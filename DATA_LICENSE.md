# Data licences

## City of Surrey data

The City layers here come from the City of Surrey Open Data Catalog (opendata-surrey.hub.arcgis.com): community boundaries, 200-year floodplain, Hazard Lands development permit area, drainage dyke infrastructure, building footprints, tree canopy statistics, schools, drainage pump stations, water utility facilities and park natural areas.

What we have read about their licence:

- The catalogue's site-wide licence page (read 2026-10-17) is the Open Government License - City of Surrey. It is the only licence text we have found for these layers.
- The dataset pages for schools, drainage pump stations, park natural areas and water utility facilities (read 2026-10-27) say "No License Provided". The item records of the other six layers, saved on 2026-10-17, carry no licence either.
- On 2026-10-27 we asked the City's GIS section whether the site-wide licence covers these layers, whether the four withdrawn layers below may be reused, and whether the layers may be read by script at one request a second. Until it answers, treat their licence as unconfirmed. This file will be updated when the City answers.

Attribution, as the site-wide licence asks: Contains information licensed under the Open Government License - City of Surrey.

Withdrawn on 2026-10-27: fire halls, emergency services, community-based organizations and the Coastal Flood Adaptation Strategy boundary. They are shared on the City's ArcGIS Online but are not listed in its open data catalogue, so they were removed from the current files and the page until the City confirms they may be reused.

Retrieval times and SHA-256 of every page used: `data/raw/city_20261017/PROVENANCE_CITY_20261017.json` and `data/raw/PROVENANCE_CITY_20261027.json`.

## Province of British Columbia

Contains information licensed under the Open Government Licence - British Columbia: BC Wildfire Service PSTA fire threat rating, from the BC Geographic Warehouse web feature service (`data/raw/psta_fire_threat_000.json`, retrieved 2026-10-27).

## Statistics Canada

Adapted from Statistics Canada, 2021 Census of Population: Census Profile, comprehensive download for British Columbia (98-401-X2021006), and the 2021 cartographic boundary file for dissemination areas (lda_000b21a_e). This does not constitute an endorsement by Statistics Canada of this product. Used under the Statistics Canada Open Licence. The Surrey subset, the indicator IDs and the SHA-256 of both downloads are in `data/raw/statcan_2021/`.
