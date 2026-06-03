import os
import geopandas as gpd
import pandas as pd
from shapely.ops import nearest_points

# 1. Configurar rutas relativas basadas en tu estructura de carpetas
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else os.getcwd()
INFRA_DIR = os.path.join(BASE_DIR, "data", "raw", "infraestructura")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "graphs")

os.makedirs(OUTPUT_DIR, exist_ok=True)

PATH_ESTACIONES = os.path.join(INFRA_DIR, "estaciones_troncales.geojson")
PATH_TRAZADOS = os.path.join(INFRA_DIR, "trazados_troncales.geojson")

print("⏳ Cargando datos geométricos de Transmilenio...")
# Cargar GeoDataFrames
estaciones = gpd.read_file(PATH_ESTACIONES)
trazados = gpd.read_file(PATH_TRAZADOS)

# Asegurar que ambos manejen el mismo sistema de coordenadas (WGS84)
estaciones = estaciones.to_crs(epsg=4326)
trazados = trazados.to_crs(epsg=4326)

# Tip: Para cálculos de distancia métrica precisa en Bogotá se suele usar EPSG:3116 (Magna-Sirgas / Colombia Bogota)
# Lo proyectamos temporalmente para cálculos de distancia exactos
estaciones_m = estaciones.to_crs(epsg=3116)
trazados_m = trazados.to_crs(epsg=3116)

aristas_lista = []

print("🚀 Procesando traza vial por troncal para conectar nodos secuencialmente...")

# 2. Iterar sobre cada trazo vial/troncal
for idx, trazo in trazados_m.iterrows():
    nombre_troncal = trazo.get('nom_tronc', f"Trazo_{idx}")
    letra_troncal = trazo.get('le_troncal', None)
    id_trazado = trazo.get('id_trazado', f"TZ_{idx}")
    tipo_via = trazo.get('tipo_tra', 1) # Atributo de arista (Carril exclusivo/mixto)
    linea_geo = trazo.geometry
    
    # Filtrar estaciones que pertenecen a esta troncal lógicamente
    # (Ajusta el nombre de la columna si en estaciones se llama diferente, ej: 'troncal' o 'linea')
    if letra_troncal:
        # Intentamos filtrar estaciones de la misma letra de troncal
        col_troncal_estacion = [c for c in estaciones_m.columns if 'tronc' in c.lower() or 'letra' in c.lower() or 'linea' in c.lower()]
        if col_troncal_estacion:
            estaciones_filtradas = estaciones_m[estaciones_m[col_troncal_estacion[0]] == letra_troncal].copy()
        else:
            estaciones_filtradas = estaciones_m.copy()
    else:
        estaciones_filtradas = estaciones_m.copy()
        
    if estaciones_filtradas.empty:
        continue
        
    # 3. Proyección Geométrica: Calcular la posición de cada estación a lo largo de la línea vial
    posiciones = []
    for est_idx, estacion in estaciones_filtradas.iterrows():
        punto_estacion = estacion.geometry
        # .project() calcula la distancia desde el inicio de la línea hasta la proyección del punto
        distancia_lineal = linea_geo.project(punto_estacion)
        
        # Guardamos metadatos esenciales para el grafo
        posiciones.append({
            'id_estacion': estacion.get('objectid') or estacion.get('id') or est_idx,
            'nombre_estacion': estacion.get('nombre') or estacion.get('nom_estac') or f"Estacion_{est_idx}",
            'distancia_lineal': distancia_lineal
        })
        
    df_posiciones = pd.DataFrame(posiciones)
    # Ordenar las estaciones según su orden físico de aparición en el trazado vial
    df_posiciones = df_posiciones.sort_values(by='distancia_lineal').reset_index(drop=True)
    
    # 4. Crear las aristas conectando estaciones consecutivas
    for i in range(len(df_posiciones) - 1):
        nodo_u = df_posiciones.loc[i, 'id_estacion']
        name_u = df_posiciones.loc[i, 'nombre_estacion']
        nodo_v = df_posiciones.loc[i+1, 'id_estacion']
        name_v = df_posiciones.loc[i+1, 'nombre_estacion']
        
        dist_nodos = abs(df_posiciones.loc[i+1, 'distancia_lineal'] - df_posiciones.loc[i, 'distancia_lineal'])
        
        # Añadir Arista en Sentido de Ida
        aristas_lista.append({
            'source': nodo_u, 'source_name': name_u,
            'target': nodo_v, 'target_name': name_v,
            'troncal': nombre_troncal, 'id_trazado': id_trazado,
            'weight_distance_m': dist_nodos, 'tipo_via': tipo_via
        })
        # Añadir Arista en Sentido de Vuelta (Bidireccional para Transmilenio)
        aristas_lista.append({
            'source': nodo_v, 'source_name': name_v,
            'target': nodo_u, 'target_name': name_u,
            'troncal': nombre_troncal, 'id_trazado': id_trazado,
            'weight_distance_m': dist_nodos, 'tipo_via': tipo_via
        })

# 5. Guardar el Edge List final listo para tu GAT
df_aristas = pd.DataFrame(aristas_lista).drop_duplicates(subset=['source', 'target'])

path_salida = os.path.join(OUTPUT_DIR, "aristas_infraestructura_gat.csv")
df_aristas.to_csv(path_salida, index=False)

print(f"✅ ¡Estructura de Red Completada exitosamente!")
print(f"📊 Total de conexiones (Aristas) generadas: {len(df_aristas)}")
print(f"📁 Archivo guardado listo para PyTorch Geometric en: {path_salida}")