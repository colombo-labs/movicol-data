"""
Procesa siniestros viales y los georreferencia usando paraderos SITP por localidad.
Genera: data/processed/siniestralidad_georef.json
"""

import json
import openpyxl
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
SINIESTROS_FILE = DATA_DIR / "raw/siniestralidad/bogota_abiertos/siniestros_viales_consolidados_bogota.xlsx"
OUTPUT_FILE = DATA_DIR / "processed/siniestralidad_georef.json"

# Mapeo código localidad → nombre (Bogotá)
LOCALIDAD_MAP = {
    1: "Usaquén", 2: "Chapinero", 3: "Santa Fe", 4: "San Cristóbal",
    5: "Usme", 6: "Tunjuelito", 7: "Bosa", 8: "Kennedy",
    9: "Fontibón", 10: "Engativá", 11: "Suba", 12: "Barrios Unidos",
    13: "Teusaquillo", 14: "Los Mártires", 15: "Antonio Nariño",
    16: "Puente Aranda", 17: "La Candelaria", 18: "Rafael Uribe Uribe",
    19: "Ciudad Bolívar", 20: "Sumapaz",
}

# Gravedad: 1=fatal, 2=herido, 3=solo daños
GRAVEDAD_MAP = {1: "fatal", 2: "herido", 3: "solo_daños"}


def load_paraderos_by_localidad() -> dict[str, list[dict]]:
    """Carga paraderos SITP agrupados por localidad desde el backend."""
    import urllib.request

    url = "http://localhost:3001/graph/sitp/paraderos"
    with urllib.request.urlopen(url) as resp:
        data = json.loads(resp.read())

    by_loc: dict[str, list[dict]] = {}
    for f in data["features"]:
        loc = f["properties"].get("localidad", "")
        coords = f["geometry"]["coordinates"]  # [lon, lat]
        if loc:
            by_loc.setdefault(loc, []).append({
                "lat": coords[1],
                "lon": coords[0],
                "nombre": f["properties"].get("nombre", ""),
            })
    return by_loc


def normalize_localidad(nombre: str) -> str:
    """Normaliza nombres de localidad para matching."""
    replacements = {
        "Rafael Uribe Uribe": "Rafael Uribe",
        "Los Mártires": "Mártires",
    }
    return replacements.get(nombre, nombre)


def process_siniestros(paraderos_by_loc: dict[str, list[dict]]) -> dict:
    """Lee xlsx y genera estadísticas por localidad + puntos georef."""
    wb = openpyxl.load_workbook(SINIESTROS_FILE, read_only=True)
    ws = wb.active

    stats_by_loc: dict[str, dict] = {}
    total = 0

    for row in ws.iter_rows(min_row=2, values_only=True):
        codigo_acc, fecha, hora, gravedad, clase, choque, obj_fijo, direccion, cod_loc, diseno = row

        if cod_loc is None:
            continue

        cod_loc = int(cod_loc) if isinstance(cod_loc, (int, float)) else None
        if cod_loc not in LOCALIDAD_MAP:
            continue

        localidad = LOCALIDAD_MAP[cod_loc]
        grav_str = GRAVEDAD_MAP.get(int(gravedad) if gravedad else 3, "solo_daños")

        # Extraer hora (int)
        hora_int = None
        if hora:
            try:
                if hasattr(hora, 'hour'):
                    hora_int = hora.hour
                else:
                    hora_int = int(str(hora).split(":")[0])
            except (ValueError, IndexError):
                pass

        if localidad not in stats_by_loc:
            stats_by_loc[localidad] = {
                "total": 0, "fatal": 0, "herido": 0, "solo_daños": 0,
                "por_hora": [0] * 24, "clases": {},
            }

        s = stats_by_loc[localidad]
        s["total"] += 1
        s[grav_str] += 1
        if hora_int is not None:
            s["por_hora"][hora_int] += 1
        if clase:
            s["clases"][str(clase)] = s["clases"].get(str(clase), 0) + 1

        total += 1

    wb.close()

    # Generar puntos georef distribuidos en paraderos de cada localidad
    heatmap_points = []
    loc_scores = {}

    for loc, stats in stats_by_loc.items():
        # Buscar paraderos de esta localidad
        loc_normalized = normalize_localidad(loc)
        paraderos = paraderos_by_loc.get(loc, []) or paraderos_by_loc.get(loc_normalized, [])

        if not paraderos:
            continue

        # Score de peligrosidad: fatal*10 + herido*3 + daños*1, normalizado por # paraderos
        score = (stats["fatal"] * 10 + stats["herido"] * 3 + stats["solo_daños"]) / len(paraderos)
        loc_scores[loc] = {
            "score": round(score, 2),
            "nivel": "peligrosa" if score > 50 else "precaución" if score > 20 else "segura",
            "total_siniestros": stats["total"],
            "fatales": stats["fatal"],
            "heridos": stats["herido"],
            "paraderos": len(paraderos),
            "por_hora": stats["por_hora"],
            "top_clases": dict(sorted(stats["clases"].items(), key=lambda x: -x[1])[:5]),
        }

        # Distribuir siniestros proporcionalmente en paraderos para heatmap
        per_paradero = stats["total"] / len(paraderos)
        for p in paraderos:
            heatmap_points.append({
                "lat": p["lat"],
                "lon": p["lon"],
                "intensity": round(per_paradero, 1),
                "localidad": loc,
                "paradero": p["nombre"],
            })

    result = {
        "total_siniestros": total,
        "por_localidad": loc_scores,
        "heatmap_points": heatmap_points,
        "metadata": {
            "fuente": "datosabiertos.bogota.gov.co - Siniestros viales consolidados",
            "registros_procesados": total,
            "localidades": len(loc_scores),
            "paraderos_con_datos": len(heatmap_points),
        },
    }

    return result


def main():
    print("📍 Cargando paraderos SITP...")
    paraderos = load_paraderos_by_localidad()
    print(f"   {sum(len(v) for v in paraderos.values())} paraderos en {len(paraderos)} localidades")

    print("🚗 Procesando siniestros viales...")
    result = process_siniestros(paraderos)
    print(f"   {result['total_siniestros']} siniestros procesados")
    print(f"   {len(result['heatmap_points'])} puntos para heatmap")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"✅ Guardado en {OUTPUT_FILE}")

    # Resumen
    print("\n📊 Resumen por localidad:")
    for loc, data in sorted(result["por_localidad"].items(), key=lambda x: -x[1]["score"])[:10]:
        print(f"   {data['nivel'].upper():12s} | {loc:20s} | score={data['score']:6.1f} | {data['total_siniestros']} siniestros | {data['fatales']} fatales")


if __name__ == "__main__":
    main()
