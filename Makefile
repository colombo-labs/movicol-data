.PHONY: install download process load clean lint test

install:
	pip install -e ".[dev]"

download:
	python scripts/download.py

process:
	python scripts/process.py

load:
	python scripts/load_postgis.py

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

test:
	pytest tests/ -v
