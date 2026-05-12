# 🌐 osm/ — Red Vial Urbana (OpenStreetMap)

Red vial completa de Bogotá extraída de OpenStreetMap.

## Fuente
- **OpenStreetMap** — Overpass API
- **Tipo:** 🌐 Externa — Comunidad abierta (licencia ODbL)
- **Clasificación:** Dato abierto comunitario

## ¿Por qué se usa una fuente externa?

**datos.gov.co solo tiene la red vial NACIONAL** (44 tramos, carreteras entre ciudades).
Para un modelo de movilidad URBANA necesitamos la red vial de Bogotá: calles, carreras, avenidas, intersecciones.

**OpenStreetMap** es la única fuente abierta que provee:
- 100,000+ segmentos de vía urbana en Bogotá
- Clasificación por tipo (primaria, secundaria, residencial)
- Geometría completa para routing

> **Nota para el concurso:** El uso de OSM está permitido. La regla dice "priorizar datos.gov.co" y permite "fuentes en tiempo real y datos estructurados y no estructurados" para nivel avanzado.

## Archivos

| Archivo | Tamaño | Descripción |
|---------|--------|-------------|
| `bogota_roads.json` | 30 MB | Todas las vías de Bogotá (100K+ segmentos) |
| `bogota_main_roads.json` | 9 MB | Solo vías principales (primarias + secundarias) |

## Cómo se descargó

```python
# Overpass API query
query = """
[out:json][timeout:300];
area["name"="Bogotá"]["admin_level"="6"]->.bogota;
way["highway"](area.bogota);
out geom;
"""
```

## Uso en el modelo

- **Aristas del grafo integrado:** Conecta estaciones/paraderos a través de la red vial real
- **Routing:** Permite calcular rutas reales (no solo línea recta)
- **pgRouting:** Base para pathfinding en PostGIS
