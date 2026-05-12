# 🚌 transmilenio/ — Transporte Masivo

Datos geoespaciales del sistema TransMilenio de Bogotá.

## Fuente
- **GIS Transmilenio** — `gis.transmilenio.gov.co/arcgis/rest/services/`
- **Tipo:** ArcGIS REST API (servicio público, no requiere autenticación)
- **Clasificación:** 🏛️ Gubernamental (Transmilenio S.A. — empresa pública)

## Archivos

| Archivo | Registros | Descripción |
|---------|-----------|-------------|
| `estaciones_troncales_tm.geojson` | 153 | Estaciones del sistema troncal con coordenadas |
| `rutas_troncales_transmilenio.geojson` | 126 | Rutas troncales (origen → destino) |
| `trazados_troncales_transmilenio.geojson` | 20 | Geometría de las 13 troncales |
| `trazados_estaciones_tm.geojson` | ~150 | Trazados entre estaciones consecutivas |
| `patios_troncales_tm.geojson` | ~10 | Patios y portales del sistema |
| `conexiones_troncales_tm.geojson` | ~20 | Conexiones entre troncales |

## Uso en el modelo

- **Nodos del grafo:** Cada estación es un nodo con coordenadas (lat, lon)
- **Aristas del grafo:** Las rutas conectan estaciones (origen → destino)
- **Geometría:** Los trazados permiten calcular distancias reales entre estaciones

## Cómo se descargó

```
GET https://gis.transmilenio.gov.co/arcgis/rest/services/Troncal/Estaciones_Troncales_TM/FeatureServer/0/query?where=1=1&outFields=*&f=geojson
```
(Repetir para cada capa del servicio)
