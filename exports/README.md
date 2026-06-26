# Exports

## ⚠️ DEPRECATED — Migrado a ArcGIS REST API

A partir de junio 2026, **todos los datos estáticos fueron eliminados** de este directorio.
El backend (`movicol-backend`) ahora consume datos directamente desde las APIs públicas de
ArcGIS FeatureServer de la Secretaría Distrital de Movilidad de Bogotá.

### Datasets migrados

| Dato | API ArcGIS | Records |
|------|-----------|---------|
| Paraderos SITP | `Paraderos_SITP_Bogotá_D_C` | 7,694 |
| Paraderos por Ruta SITP | `Paraderos_Ruta` | 41,038 |
| Estaciones TransMilenio | `Estaciones_y_trazados_de_Transmilenio_WFL1` (Layer 0) | 149 |
| Rutas Troncales TM | `Estaciones_y_trazados_de_Transmilenio_WFL1` (Layer 2) | 155 |
| Trazados Troncales TM | `Trazados_Troncales_de_TRANSMILENIO` | 20 |
| Rutas SITP (shapes) | `Rutas_SITP` | 700 |
| Carril Preferencial | `Carril_Preferencial_SITP_Bogota_D_C` | 8 |
| Siniestros 2024 | `Siniestros_graves_2024` | 12,908 |
| Siniestros por Localidad | `Siniestros_Fallecidos_por_Localidad` | 20 |

### Base URL
```
https://services2.arcgis.com/NEwhEo9GGSHXcRXV/arcgis/rest/services/{SERVICE_NAME}/FeatureServer/{LAYER}/query?where=1=1&outFields=*&f=geojson
```

### Cache
El backend usa Redis con TTL de 24 horas. Primera request fetcha de ArcGIS (~2-5s),
las siguientes son instantáneas desde cache.

### Archivos eliminados
- `sitp_paraderos.geojson` (1 MB)
- `sitp_rutas_paraderos.geojson` (30 MB)
- `tm_rutas_troncales.json` (1.5 MB)
- `siniestralidad.json` (351 KB)
- `frontend/tm_estaciones.geojson`
- `frontend/tm_troncales.geojson`
