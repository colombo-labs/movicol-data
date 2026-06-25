"""Enrich siniestralidad.json with datos.gov.co datasets.

Combines:
- Existing siniestralidad.json (localidad-level from xlsx, if available)
- sectores_criticos_siniestralidad.csv (316 tramos ANSV with lat/lon)
- vehiculos_accidentes_bogota.csv (50K RUNT records with type/date/gravity)
- red_semaforica_bogota.geojson (1,462 traffic signals with location)

Generates: exports/siniestralidad.json (enriched)
"""

import csv
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
EXPORTS_DIR = Path(__file__).parent.parent / "exports"

SECTORES_CSV = RAW_DIR / "siniestralidad/datos_gov_co/sectores_criticos_siniestralidad.csv"
ACCIDENTES_CSV = RAW_DIR / "siniestralidad/fuentes_alternativas/vehiculos_accidentes_bogota.csv"
SEMAFOROS_GEOJSON = RAW_DIR / "semaforos/red_semaforica_bogota.geojson"
EXISTING_JSON = EXPORTS_DIR / "siniestralidad.json"
OUTPUT_FILE = EXPORTS_DIR / "siniestralidad.json"

BOGOTA_BOUNDS = {"lat_min": 4.45, "lat_max": 4.85, "lon_min": -74.25, "lon_max": -73.95}

HOUR_RISK_PROFILE = [
    0.15,
    0.10,
    0.08,
    0.07,
    0.08,
    0.12,
    0.25,
    0.45,
    0.55,
    0.50,
    0.42,
    0.40,
    0.48,
    0.45,
    0.42,
    0.45,
    0.52,
    0.62,
    0.65,
    0.55,
    0.45,
    0.35,
    0.28,
    0.20,
]


def load_existing() -> dict:
    """Load existing siniestralidad.json if available."""
    if EXISTING_JSON.exists():
        with open(EXISTING_JSON, encoding="utf-8") as f:
            return json.load(f)
    return {"total_siniestros": 0, "por_localidad": {}, "heatmap_points": [], "metadata": {}}


def process_sectores_criticos() -> tuple[list[dict], int, int]:
    """Process ANSV critical sectors (with geolocation)."""
    if not SECTORES_CSV.exists():
        return [], 0, 0

    points = []
    total_fallecidos = 0
    bogota_count = 0

    with open(SECTORES_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lat = float(row["latitud"]) if row.get("latitud") else None
            lon = float(row["longitud"]) if row.get("longitud") else None
            if lat is None or lon is None:
                continue

            fallecidos = int(row.get("fallecidos", 0) or 0)
            gizscore = float(row.get("gizscore", 0) or 0)
            total_fallecidos += fallecidos

            in_bogota = (
                BOGOTA_BOUNDS["lat_min"] <= lat <= BOGOTA_BOUNDS["lat_max"]
                and BOGOTA_BOUNDS["lon_min"] <= lon <= BOGOTA_BOUNDS["lon_max"]
            )
            if in_bogota:
                bogota_count += 1

            intensity = min(100.0, fallecidos * 5 + gizscore * 10)
            points.append(
                {
                    "lat": lat,
                    "lon": lon,
                    "intensity": round(intensity, 1),
                    "source": "sectores_criticos_ansv",
                    "tramo": row.get("tramo", ""),
                    "nombre": row.get("nombre", ""),
                    "fallecidos": fallecidos,
                    "municipio": row.get("municipio", ""),
                    "departamento": row.get("departamento", ""),
                }
            )

    return points, total_fallecidos, bogota_count


def process_accidentes() -> dict:
    """Process 50K RUNT vehicle accident records."""
    if not ACCIDENTES_CSV.exists():
        return {}

    stats = {
        "total": 0,
        "por_gravedad": {},
        "por_tipo_vehiculo": {},
        "por_mes": {},
        "por_marca": {},
    }

    with open(ACCIDENTES_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stats["total"] += 1

            gravedad = row.get("gravedad_accidente", "DESCONOCIDO")
            stats["por_gravedad"][gravedad] = stats["por_gravedad"].get(gravedad, 0) + 1

            tipo = row.get("tipo_vehiculo", "DESCONOCIDO")
            stats["por_tipo_vehiculo"][tipo] = stats["por_tipo_vehiculo"].get(tipo, 0) + 1

            fecha = row.get("fecha_accidente", "")
            if "/" in fecha:
                mes = fecha.split("/")[0]
                stats["por_mes"][mes] = stats["por_mes"].get(mes, 0) + 1

            marca = row.get("marca_vehiculo", "DESCONOCIDO")
            stats["por_marca"][marca] = stats["por_marca"].get(marca, 0) + 1

    stats["por_tipo_vehiculo"] = dict(
        sorted(stats["por_tipo_vehiculo"].items(), key=lambda x: -x[1])
    )
    stats["por_marca"] = dict(sorted(stats["por_marca"].items(), key=lambda x: -x[1])[:20])
    stats["por_gravedad"] = dict(sorted(stats["por_gravedad"].items(), key=lambda x: -x[1]))

    return stats


def process_semaforos() -> list[dict]:
    """Process traffic signals as safety infrastructure points."""
    if not SEMAFOROS_GEOJSON.exists():
        return []

    with open(SEMAFOROS_GEOJSON, encoding="utf-8") as f:
        data = json.load(f)

    semaforos = []
    for feat in data.get("features", []):
        geom = feat.get("geometry", {})
        props = feat.get("properties", {})
        coords = geom.get("coordinates")
        if not coords or geom.get("type") != "Point":
            continue
        semaforos.append(
            {
                "lat": coords[1],
                "lon": coords[0],
                "localidad": props.get("LOCALIDAD", ""),
                "tipo": props.get("TIPO_INTER", ""),
                "direccion": props.get("DIRECCION", ""),
                "infra_cicl": props.get("INFRA_CICL", ""),
            }
        )
    return semaforos


def generate_hourly_risk(por_localidad: dict) -> dict:
    """Generate hourly risk predictions for each localidad."""
    risk_by_hour = {}
    for hour in range(24):
        base_risk = HOUR_RISK_PROFILE[hour]
        risk_by_hour[str(hour)] = {}
        for loc, data in por_localidad.items():
            score = data.get("score", 0)
            max_score = max(d.get("score", 1) for d in por_localidad.values()) or 1
            loc_factor = score / max_score
            risk = round(min(1.0, base_risk * (0.4 + 0.6 * loc_factor)), 3)
            label = (
                "bajo"
                if risk < 0.25
                else "moderado"
                if risk < 0.50
                else "alto"
                if risk < 0.75
                else "critico"
            )
            risk_by_hour[str(hour)][loc] = {"risk": risk, "nivel": label}
    return risk_by_hour


def main() -> None:
    print("Loading existing siniestralidad data...")
    existing = load_existing()

    print("Processing sectores criticos ANSV...")
    sector_points, total_fallecidos, bogota_sectors = process_sectores_criticos()
    print(f"  {len(sector_points)} sectors, {total_fallecidos} fatalities")
    print(f"  {bogota_sectors} in Bogota")

    print("Processing 50K vehicle accidents RUNT...")
    accident_stats = process_accidentes()
    print(f"  {accident_stats.get('total', 0)} records processed")

    print("Processing traffic signals...")
    semaforos = process_semaforos()
    print(f"  {len(semaforos)} traffic signals loaded")

    print("Generating hourly risk predictions...")
    por_localidad = existing.get("por_localidad", {})
    risk_by_hour = generate_hourly_risk(por_localidad) if por_localidad else {}

    all_heatmap = existing.get("heatmap_points", [])
    existing_coords = {(round(p["lat"], 4), round(p["lon"], 4)) for p in all_heatmap}
    added = 0
    for sp in sector_points:
        key = (round(sp["lat"], 4), round(sp["lon"], 4))
        if key not in existing_coords:
            all_heatmap.append(sp)
            existing_coords.add(key)
            added += 1
    print(f"  Added {added} new heatmap points from sectores criticos")

    semaforos_by_localidad = {}
    for s in semaforos:
        loc = s.get("localidad", "")
        if loc:
            semaforos_by_localidad[loc] = semaforos_by_localidad.get(loc, 0) + 1

    for loc in por_localidad:
        por_localidad[loc]["semaforos"] = semaforos_by_localidad.get(loc, 0)

    total_accidentes_runt = accident_stats.get("total", 0)
    total_existing = existing.get("total_siniestros", 0)
    combined_total = (
        max(total_existing, total_accidentes_runt) if total_existing else total_accidentes_runt
    )

    result = {
        "total_siniestros": combined_total,
        "total_fallecidos_sectores_criticos": total_fallecidos,
        "por_localidad": por_localidad,
        "heatmap_points": all_heatmap,
        "risk_by_hour": risk_by_hour,
        "vehiculos_stats": accident_stats,
        "semaforos": {
            "total": len(semaforos),
            "por_localidad": semaforos_by_localidad,
        },
        "sectores_criticos": {
            "total": len(sector_points),
            "en_bogota": bogota_sectors,
            "fallecidos": total_fallecidos,
        },
        "metadata": {
            "fuentes": [
                "datos.gov.co/rs3u-8r4q (Sectores Criticos ANSV)",
                "datos.gov.co/6jmc-vaxk (Vehiculos Accidentes RUNT Ley 2251-2022)",
                "ArcGIS Hub SDM (Red Semaforica Bogota)",
            ],
            "registros_procesados": combined_total + len(sector_points),
            "localidades": len(por_localidad),
            "paraderos_con_datos": len(all_heatmap),
            "sectores_criticos": len(sector_points),
            "semaforos": len(semaforos),
        },
    }

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    size_kb = OUTPUT_FILE.stat().st_size / 1024
    print(f"\nSaved to {OUTPUT_FILE} ({size_kb:.0f} KB)")
    print(f"  Total siniestros: {combined_total:,}")
    print(f"  Heatmap points: {len(all_heatmap)}")
    print(f"  Hourly risk: {len(risk_by_hour)} hours x {len(por_localidad)} localidades")
    print(f"  Vehicle stats: {accident_stats.get('total', 0):,} records")
    print(f"  Semaforos: {len(semaforos)}")

    top_types = list(accident_stats.get("por_tipo_vehiculo", {}).items())[:5]
    if top_types:
        print("\nTop vehicle types in accidents:")
        for tipo, count in top_types:
            print(f"  {tipo}: {count:,}")

    top_gravity = list(accident_stats.get("por_gravedad", {}).items())[:3]
    if top_gravity:
        print("\nGravity distribution:")
        for grav, count in top_gravity:
            pct = count / accident_stats["total"] * 100
            print(f"  {grav}: {count:,} ({pct:.1f}%)")


if __name__ == "__main__":
    main()
