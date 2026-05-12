"""Load processed data into PostGIS database."""

import os
from pathlib import Path

import geopandas as gpd
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"
RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://movicol:movicol_dev@localhost:5432/movicol")


def get_engine():
    """Create SQLAlchemy engine."""
    return create_engine(DATABASE_URL)


def ensure_postgis(engine) -> None:
    """Enable PostGIS extension."""
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
    print("  ✅ PostGIS extension enabled")


def load_geojson_files(engine) -> None:
    """Load GeoJSON files into PostGIS tables."""
    for geojson_file in RAW_DIR.glob("*.geojson"):
        table_name = geojson_file.stem
        gdf = gpd.read_file(geojson_file)

        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326")
        elif gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs("EPSG:4326")

        gdf.to_postgis(table_name, engine, if_exists="replace", index=False)
        print(f"  🗺️  {table_name}: {len(gdf)} features loaded")


def load_csv_files(engine) -> None:
    """Load CSV files into PostgreSQL tables."""
    for csv_file in RAW_DIR.glob("*.csv"):
        table_name = csv_file.stem
        df = pd.read_csv(csv_file)
        df.to_sql(table_name, engine, if_exists="replace", index=False)
        print(f"  📄 {table_name}: {len(df)} rows loaded")


def main() -> None:
    """Load all data into PostGIS."""
    print("\n🔌 Connecting to PostGIS...")
    engine = get_engine()
    ensure_postgis(engine)

    print("\n📤 Loading GeoJSON files...")
    load_geojson_files(engine)

    print("\n📤 Loading CSV files...")
    load_csv_files(engine)

    print("\n✅ All data loaded into PostGIS!")


if __name__ == "__main__":
    main()
