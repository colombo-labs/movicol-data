import json
import random
from pathlib import Path

# Paths
EXPORTS_DIR = Path(__file__).parent.parent / "exports" / "backend"
PARADEROS_FILE = EXPORTS_DIR / "sitp_paraderos.geojson"
RUTAS_PARADEROS_FILE = EXPORTS_DIR / "sitp_rutas_paraderos.geojson"
FRECUENCIAS_FILE = EXPORTS_DIR / "sitp_rutas_frecuencias.json"

def process_paraderos():
    print("⏳ Processing paraderos...")
    if not PARADEROS_FILE.exists():
        print(f"❌ {PARADEROS_FILE} no existe.")
        return

    with open(PARADEROS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Añadir demanda y nivel de infraestructura a cada paradero
    infra_levels = ["Basico", "Estandar", "Completo"]
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        
        # Demanda aleatoria con distribución (mayoría media-baja, algunos muy altos)
        demanda = int(random.triangular(10, 100, 30))
        props["demanda_score"] = demanda
        
        # Clasificar demanda en string para facilitar Frontend
        if demanda < 40:
            props["demanda_nivel"] = "Baja"
        elif demanda < 75:
            props["demanda_nivel"] = "Media"
        else:
            props["demanda_nivel"] = "Alta"
            
        # Nivel de infra
        props["infra_level"] = random.choices(infra_levels, weights=[60, 30, 10])[0]

    # Guardar sobreescribiendo
    with open(PARADEROS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)
        
    print(f"✅ {len(data.get('features', []))} paraderos actualizados con demanda_score.")


def generate_frequencies():
    print("⏳ Generando frecuencias sintéticas por ruta...")
    if not RUTAS_PARADEROS_FILE.exists():
        print(f"❌ {RUTAS_PARADEROS_FILE} no existe.")
        return

    # Leer las rutas que existen en el sistema
    with open(RUTAS_PARADEROS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    rutas = set()
    for feature in data.get("features", []):
        ruta = feature.get("properties", {}).get("ruta")
        if ruta:
            rutas.add(ruta)

    frecuencias = {}
    for ruta in rutas:
        # Frecuencia base en minutos (ej. entre 5 y 30 min)
        base_freq = random.randint(5, 30)
        frecuencias[ruta] = {
            "frecuencia_base_min": base_freq,
            "tipo_servicio": "Urbano" if len(ruta) > 2 else "Troncal"
        }

    with open(FRECUENCIAS_FILE, "w", encoding="utf-8") as f:
        json.dump(frecuencias, f, indent=2)
        
    print(f"✅ Frecuencias generadas para {len(rutas)} rutas.")

if __name__ == "__main__":
    random.seed(42)  # Determinismo
    process_paraderos()
    generate_frequencies()
