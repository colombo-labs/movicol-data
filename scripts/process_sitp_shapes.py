import json
import logging
from pathlib import Path

import geopandas as gpd
import networkx as nx
import osmnx as ox
from shapely.geometry import LineString, Point

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Paths
EXPORTS_DIR = Path(__file__).parent.parent / "exports" / "backend"
RUTAS_PARADEROS_FILE = EXPORTS_DIR / "sitp_rutas_paraderos.geojson"
RUTAS_SHAPES_FILE = EXPORTS_DIR / "sitp_rutas_shapes.geojson"

def process_shapes(limit: int = 0):
    logger.info("⏳ Iniciando procesamiento de shapes (Snap-to-Road)...")
    
    if not RUTAS_PARADEROS_FILE.exists():
        logger.error(f"❌ No se encontró {RUTAS_PARADEROS_FILE}")
        return

    # Cargar datos de paraderos agrupados por ruta
    logger.info("Cargando GeoJSON de rutas y paraderos...")
    gdf = gpd.read_file(RUTAS_PARADEROS_FILE)
    
    # Agrupar por ruta
    rutas = gdf.groupby("ruta")
    
    # Descargar o cargar el grafo vial de Bogotá
    # Nota: Para un ambiente de producción usaríamos todo Bogotá, 
    # aquí descargaremos un bbox genérico o la ciudad completa (puede tardar ~1-2 min)
    logger.info("Descargando/Construyendo grafo vial de Bogotá vía OSMnx...")
    ox.settings.log_console = True
    ox.settings.use_cache = True
    
    # Usamos network_type="drive" para buses
    try:
        G = ox.graph_from_place("Bogotá, Colombia", network_type="drive", simplify=True)
        # Asegurar proyección correcta para búsqueda de nodos cercanos
        G_proj = ox.project_graph(G)
    except Exception as e:
        logger.error(f"❌ Error al descargar grafo de Bogotá: {e}")
        return

    rutas_shapes = []
    rutas_list = list(rutas)
    
    if limit > 0:
        logger.info(f"Limiting to {limit} routes for speed in this run.")
        rutas_list = rutas_list[:limit]
        
    total_rutas = len(rutas_list)
    
    for i, (ruta_name, group) in enumerate(rutas_list):
        # Ordenar por secuencia si existe, sino intentar por orden original
        if "orden" in group.columns:
            group = group.sort_values("orden")
            
        logger.info(f"Procesando ruta [{i+1}/{total_rutas}]: {ruta_name} ({len(group)} paraderos)")
        
        # Extraer puntos
        coords = [(geom.x, geom.y) for geom in group.geometry if isinstance(geom, Point)]
        if len(coords) < 2:
            continue
            
        # Proyectar coordenadas a UTM para encontrar los nodos más cercanos rápidamente
        points_gpd = gpd.GeoDataFrame(geometry=[Point(lon, lat) for lon, lat in coords], crs="EPSG:4326")
        points_proj = points_gpd.to_crs(G_proj.graph["crs"])
        
        X = [geom.x for geom in points_proj.geometry]
        Y = [geom.y for geom in points_proj.geometry]
        
        nearest_nodes = ox.distance.nearest_nodes(G_proj, X, Y)
        
        # Calcular rutas más cortas entre nodos consecutivos
        route_nodes = []
        for j in range(len(nearest_nodes) - 1):
            try:
                # Usar el algoritmo de Dijkstra en el grafo original para shortest_path
                path = nx.shortest_path(G, nearest_nodes[j], nearest_nodes[j+1], weight="length")
                # Evitar duplicar el nodo de conexión
                if route_nodes:
                    route_nodes.extend(path[1:])
                else:
                    route_nodes.extend(path)
            except nx.NetworkXNoPath:
                # Si no hay ruta en el grafo vial, hacer fallback a línea recta (menos estético pero funcional)
                logger.warning(f"  ⚠️ No hay camino en OSM entre el nodo {j} y {j+1} de la ruta {ruta_name}")
                pass
                
        # Construir la geometría LineString
        if len(route_nodes) > 1:
            try:
                # Obtener lat/lons de los nodos para construir la línea en EPSG:4326
                route_line_coords = [(G.nodes[n]['x'], G.nodes[n]['y']) for n in route_nodes]
                line = LineString(route_line_coords)
                rutas_shapes.append({
                    "type": "Feature",
                    "properties": {"ruta": ruta_name},
                    "geometry": line.__geo_interface__
                })
            except Exception as e:
                logger.error(f"  ❌ Error construyendo línea para {ruta_name}: {e}")
        else:
            # Fallback a unir los paraderos con líneas rectas si falló el ruteo
            line = LineString(coords)
            rutas_shapes.append({
                "type": "Feature",
                "properties": {"ruta": ruta_name, "fallback": True},
                "geometry": line.__geo_interface__
            })

    # Guardar en GeoJSON
    logger.info(f"💾 Guardando {len(rutas_shapes)} rutas procesadas...")
    feature_collection = {
        "type": "FeatureCollection",
        "features": rutas_shapes
    }
    
    with open(RUTAS_SHAPES_FILE, "w", encoding="utf-8") as f:
        json.dump(feature_collection, f)
        
    logger.info(f"✅ ¡Shapes generados exitosamente en {RUTAS_SHAPES_FILE.name}!")

if __name__ == "__main__":
    # Podemos pasar limit=10 o algo similar si queremos procesar rápido para la demo
    # Procesar 50 rutas para tener una buena muestra sin bloquear la ejecución 1 hora
    process_shapes(limit=50)
