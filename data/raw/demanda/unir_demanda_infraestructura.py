import pandas as pd
import json
import re
import os

# 1. Definición de rutas basadas en la raíz de tu proyecto
RAIZ_PROYECTO = os.getcwd()
RUTA_DEMANDA = os.path.join(RAIZ_PROYECTO, "data", "processed", "demanda_troncal_2025_final.csv")
RUTA_GEOJSON = os.path.join(RAIZ_PROYECTO, "data", "raw", "infraestructura", "estaciones_troncales.geojson")

# Destinos finales procesados
NUEVA_DEMANDA_PROCESADA = os.path.join(RAIZ_PROYECTO, "data", "processed", "demanda_con_nodos.csv")
RUTA_NODOS_GRAFO = os.path.join(RAIZ_PROYECTO, "data", "processed", "nodos_infraestructura_gat.csv")

print("🌐 Iniciando la fusión de Demanda Espacial e Infraestructura...")

# 2. Cargar el GeoJSON de infraestructura y transformarlo a una tabla de Pandas
if not os.path.exists(RUTA_GEOJSON):
    print(f"❌ Error: No encontré el archivo GeoJSON en la ruta:\n👉 {RUTA_GEOJSON}")
else:
    print("📄 Leyendo capas geográficas del GeoJSON...")
    with open(RUTA_GEOJSON, 'r', encoding='utf-8') as f:
        geojson_data = json.load(f)
        
    # Extraemos las propiedades y la geometría de cada estación
    lista_estaciones = []
    for feature in geojson_data['features']:
        props = feature['properties'].copy()
        # Extraemos las coordenadas espaciales reales del Point [Longitud, Latitud]
        props['lon_real'] = feature['geometry']['coordinates'][0]
        props['lat_real'] = feature['geometry']['coordinates'][1]
        lista_estaciones.append(props)
        
    df_infra = pd.DataFrame(lista_estaciones)
    
    # Aseguramos que el num_est no tenga espacios y sea un texto limpio (ej: "07103")
    df_infra['num_est'] = df_infra['num_est'].astype(str).str.strip()
    
    # Guardamos un archivo limpio de solo NODOS con sus características físicas para la GAT
    df_nodos_features = df_infra[['num_est', 'nom_est', 'lon_real', 'lat_real', 'tipo_esta', 'area_est', 'num_vag', 'num_acc']].copy()
    os.makedirs(os.path.dirname(RUTA_NODOS_GRAFO), exist_ok=True)
    df_nodos_features.to_csv(RUTA_NODOS_GRAFO, index=False)
    print(f"✅ Archivo de características de NODOS creado con éxito ({df_nodos_features.shape[0]} estaciones).")

    # 3. Cargar tus 10 millones de filas de demanda
    if not os.path.exists(RUTA_DEMANDA):
        print(f"❌ Error: No se encuentra el archivo de demanda limpia en:\n👉 {RUTA_DEMANDA}")
    else:
        print("📊 Cargando dataset de 10 millones de pasajeros (esto puede tomar unos segundos)...")
        df_demanda = pd.read_csv(RUTA_DEMANDA)
        
        # TRUCO DE INGENIERÍA: Extraer el número dentro del paréntesis de la columna 'Estación'
        # Ejemplo: "(07103) AV. Chile" -> "07103"
        print("🧬 Extrayendo IDs numéricos de las estaciones de la demanda...")
        def extraer_id(texto):
            match = re.search(r'\((.*?)\)', str(texto))
            return match.group(1).strip() if match else None

        df_demanda['id_estacion_match'] = df_demanda['Estación'].apply(extraer_id)
        
        # 4. Fusionar la Demanda con las Coordenadas Geográficas (Merge)
        print("🔗 Cruzando bases de datos por ID de estación...")
        df_fusionado = pd.merge(
            df_demanda,
            df_infra[['num_est', 'lon_real', 'lat_real']],
            left_on='id_estacion_match',
            right_on='num_est',
            how='inner' # Solo conserva lo que coincida de forma exacta en el mapa
        )
        
        # Eliminar columnas temporales de cruce
        df_fusionado = df_fusionado.drop(columns=['id_estacion_match', 'num_est'])
        
        # 5. Guardar la nueva Súper Matriz de Demanda Georreferenciada
        print("💾 Guardando el archivo final unificado...")
        df_fusionado.to_csv(NUEVA_DEMANDA_PROCESADA, index=False)
        
        print("\n==================================================")
        print("🎉 ¡FUSIÓN DE INFRAESTRUCTURA Y DEMANDA EXITOSA!")
        print(f"💾 Demanda mapeada guardada en: {NUEVA_DEMANDA_PROCESADA}")
        print(f"📊 Filas georreferenciadas con éxito: {df_fusionado.shape[0]} de {df_demanda.shape[0]}")
        print("==================================================")
        print("\nMuestra del dataset listo para las Aristas del Grafo:")
        print(df_fusionado[['Línea', 'Estación', 'Fecha', 'Validaciones', 'lon_real', 'lat_real']].head())