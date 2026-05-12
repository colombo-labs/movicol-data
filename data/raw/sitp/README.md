# 🚏 sitp/ — Transporte Zonal (SITP)

Datos del Sistema Integrado de Transporte Público — componente zonal.

## Fuentes

| Archivo | Fuente | Tipo |
|---------|--------|------|
| `paraderos_sistema.csv` | datos.gov.co (`hxy3-94yh`) | 🏛️ Gubernamental — Socrata API |
| `paraderos_sitp_bogota.geojson` | datos.gov.co (`yvk5-8nn5`) | 🏛️ Gubernamental — Socrata API |
| `nodos_sitp_bogota.geojson` | datos.gov.co (`djsz-g96f`) | 🏛️ Gubernamental — Socrata API |
| `paraderos_sitp_arcgis_hub.geojson` | ArcGIS Hub SDM | 🏛️ Gubernamental — Secretaría de Movilidad |
| `nodos_sitp_arcgis_hub.geojson` | ArcGIS Hub SDM | 🏛️ Gubernamental — Secretaría de Movilidad |
| `paraderos_rutas_sitp.geojson` | GIS Transmilenio | 🏛️ Gubernamental — Transmilenio S.A. |
| `paraderos_zonales_sitp.geojson` | GIS Transmilenio | 🏛️ Gubernamental — Transmilenio S.A. |
| `rutas_zonales_sitp.geojson` | GIS Transmilenio | 🏛️ Gubernamental — Transmilenio S.A. |

> Todas las fuentes son gubernamentales. No hay datos externos en esta categoría.

## Archivos

| Archivo | Registros | Descripción |
|---------|-----------|-------------|
| `paraderos_sistema.csv` | 928 | Paradas con coordenadas, nombre, secuencia, ruta |
| `paraderos_sitp_bogota.geojson` | 7,694 | Todos los paraderos SITP con geometría |
| `nodos_sitp_bogota.geojson` | 154 | Nodos principales de transporte |
| `paraderos_sitp_arcgis_hub.geojson` | 7,694 | Paraderos desde ArcGIS Hub (respaldo) |
| `nodos_sitp_arcgis_hub.geojson` | 154 | Nodos desde ArcGIS Hub (respaldo) |
| `paraderos_rutas_sitp.geojson` | 42,601 | Relaciones paradero↔ruta (secuencia ordenada) |
| `paraderos_zonales_sitp.geojson` | ~1,000 | Paraderos del componente zonal |
| `rutas_zonales_sitp.geojson` | 703 | Rutas zonales del SITP |

## Uso en el modelo

- **Nodos del grafo:** Cada paradero es un nodo (7,291 únicos por cenefa)
- **Aristas del grafo:** Las secuencias paradero-ruta generan 41,907 aristas
- **Deduplicación:** De 42,601 relaciones a 7,291 paraderos únicos
