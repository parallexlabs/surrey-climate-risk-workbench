.PHONY: data build cached test serve

data:   ## fetch the City layers again, through the host-register gate
	python3 scripts/fetch_city_layers.py data/raw

build:  ## recompute every figure from data/raw (about three minutes)
	python3 scripts/build.py

cached: ## rebuild the site from data/derived/metrics.json
	python3 scripts/build.py --cached

test:
	python3 -m pytest -q tests

serve:  ## open site/index.html from a local server
	cd site && python3 -m http.server 8000
