"""Download datasets from datos.gov.co (Socrata API) and other sources."""

import os
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://www.datos.gov.co/resource"
RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
CONFIG_DIR = Path(__file__).parent.parent / "config"
SOCRATA_TOKEN = os.getenv("SOCRATA_APP_TOKEN", "")
LIMIT = 50000


def load_catalog() -> dict:
    """Load dataset catalog from YAML config."""
    with open(CONFIG_DIR / "datasets.yaml") as f:
        return yaml.safe_load(f)


def download_socrata(dataset: dict) -> None:
    """Download a dataset from Socrata API (datos.gov.co)."""
    if not dataset.get("id"):
        return

    fmt = dataset["format"]
    url = f"{BASE_URL}/{dataset['id']}.{fmt}?$limit={LIMIT}"
    headers = {}
    if SOCRATA_TOKEN:
        headers["X-App-Token"] = SOCRATA_TOKEN

    output_path = RAW_DIR / dataset["path"]
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"  ⬇️  {dataset['name']} ({fmt})...")
    response = requests.get(url, headers=headers, timeout=120)
    response.raise_for_status()

    output_path.write_bytes(response.content)
    size_kb = len(response.content) / 1024
    print(f"  ✅ {output_path.name} ({size_kb:.0f} KB)")


def main() -> None:
    """Download all datasets from catalog."""
    catalog = load_catalog()

    # Skip 'graphs' and 'pendientes' sections
    skip_sections = {"graphs", "pendientes"}

    for category, datasets in catalog.items():
        if category in skip_sections:
            continue

        print(f"\n📂 {category}")
        for dataset in datasets:
            # Only download from Socrata (has ID) and not already downloaded
            if not dataset.get("id"):
                print(f"  ⏭️  {dataset['name']} — no Socrata ID (manual download)")
                continue
            if dataset.get("source") != "datos_gov_co":
                print(f"  ⏭️  {dataset['name']} — source: {dataset.get('source')}")
                continue

            output_path = RAW_DIR / dataset["path"]
            if output_path.exists():
                print(f"  ✓  {dataset['name']} — already exists")
                continue

            try:
                download_socrata(dataset)
            except Exception as e:
                print(f"  ❌ {dataset['name']}: {e}")


if __name__ == "__main__":
    main()
