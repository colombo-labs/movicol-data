.PHONY: install download process load clean lint test

# Default env: local
ENV ?= local

install:
	pip install -e ".[dev]"

download:
	python scripts/download.py

process:
	python scripts/process.py

# Load to specific environment
load:
	@echo "📦 Loading data to [$(ENV)]..."
	@cp .env.$(ENV) .env
	python scripts/load_postgis.py
	@echo "✅ Done loading to $(ENV)"

load-local:
	$(MAKE) load ENV=local

load-dev:
	$(MAKE) load ENV=dev

clean:
	rm -rf data/raw/* data/processed/* data/graphs/*

lint:
	ruff check scripts/
	ruff format --check scripts/

format:
	ruff format scripts/

sitp-graph:
	python scripts/build_sitp_graph.py

enrich-siniestralidad:
	python scripts/enrich_siniestralidad.py
