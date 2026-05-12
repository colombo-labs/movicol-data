# 🛣️ red_vial/ — Red Vial Nacional

Red vial nacional de Colombia con geometría.

## Fuente
- **datos.gov.co** — ID: `ie7y-asdn`
- **Tipo:** 🏛️ Gubernamental — Socrata API (INVIAS)
- **Clasificación:** Dato abierto oficial

## Archivos

| Archivo | Registros | Tamaño | Descripción |
|---------|-----------|--------|-------------|
| `red_vial_nacional.csv` | 44 | 14 MB | Tramos de la red vial nacional con geometría WKT |

## Uso en el modelo

- **Aristas macro:** Conexiones entre ciudades/municipios
- **Limitación:** Solo contiene la red NACIONAL (carreteras entre ciudades), no la red urbana de Bogotá
- **Complemento:** Para la red urbana se usa OpenStreetMap (ver `osm/README.md`)

## ⚠️ Nota

Este dataset es pesado (14MB) porque incluye geometría WKT completa de cada tramo.
Solo tiene 44 registros pero cada uno contiene miles de coordenadas.
