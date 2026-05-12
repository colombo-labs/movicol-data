# 📂 data/raw — Datos Crudos de Movilidad Urbana

Datos descargados directamente de fuentes abiertas colombianas, sin transformar.

**Total: 30 archivos | ~115 MB | 170,000+ registros**
**Fecha de descarga: 1 de mayo de 2026**

---

## Estructura

```
data/raw/
├── transmilenio/              ← 6 GeoJSON — Transporte masivo (estaciones, rutas, troncales)
├── sitp/                      ← 1 CSV + 7 GeoJSON — Transporte zonal (paraderos, rutas)
├── demanda/                   ← 1 CSV — Pasajeros transporte masivo
├── siniestralidad/
│   ├── datos_gov_co/          ← 1 CSV — Sectores críticos (fuente oficial)
│   └── fuentes_alternativas/  ← 1 CSV — Accidentes Bogotá (fuente alternativa)
├── red_vial/                  ← 1 CSV — Red vial nacional
├── vehicular/                 ← 4 CSV — Parque automotor, tráfico, pesaje
├── movilidad_urbana/          ← 2 CSV — Pasajeros carretera, aéreo
└── osm/                       ← 2 JSON — Red vial completa Bogotá (OpenStreetMap)
```

---

## Resumen por categoría

| Categoría | Archivos | Tamaño | Registros clave | Uso en el modelo |
|-----------|----------|--------|-----------------|------------------|
| `transmilenio/` | 6 GeoJSON | 3.4 MB | 153 estaciones, 126 rutas, 20 troncales | Nodos + aristas troncales |
| `sitp/` | 1 CSV + 7 GeoJSON | 37 MB | 7,694 paraderos, 42,601 relaciones, 703 rutas | Nodos + aristas zonales |
| `demanda/` | 1 CSV | 96 KB | 1,000 registros pasajeros/día | Feature: demanda |
| `siniestralidad/` | 2 CSV | 6 MB | 316 sectores + 50,000 accidentes | Feature: riesgo |
| `red_vial/` | 1 CSV | 14 MB | 44 tramos con geometría | Aristas macro |
| `vehicular/` | 4 CSV | 11 MB | 3,160 + 110,780 registros | Features: tráfico |
| `movilidad_urbana/` | 2 CSV | 4.8 MB | Origen-destino carretera/aéreo | Features complementarias |
| `osm/` | 2 JSON | 39 MB | Red vial completa Bogotá | Aristas urbanas |

---

## Fuentes de datos

### 🏛️ Fuentes gubernamentales (obligatorias para el concurso)

| Fuente | URL | Tipo | Datos |
|--------|-----|------|-------|
| **datos.gov.co** | `www.datos.gov.co/resource/{ID}` | Socrata API | Paraderos, pasajeros, siniestralidad, red vial, parque automotor |
| **GIS Transmilenio** | `gis.transmilenio.gov.co/arcgis/rest/services/` | ArcGIS REST | Estaciones, rutas, trazados, paraderos-rutas |
| **ArcGIS Hub SDM** | `services2.arcgis.com/NEwhEo9GGSHXcRXV/` | ArcGIS FeatureServer | Paraderos SITP, nodos transporte |

> **Regla del concurso:** El 100% de los datos de entrenamiento deben provenir de datos.gov.co o fuentes abiertas oficiales.

### 🌐 Fuentes externas (complementarias)

| Fuente | URL | Tipo | Razón de uso |
|--------|-----|------|--------------|
| **OpenStreetMap** | `overpass-api.de/api/` | Overpass API | Red vial completa de Bogotá — datos.gov.co solo tiene la red nacional (44 tramos), no la urbana. OSM provee 100,000+ segmentos de vía urbana necesarios para routing. |
| **RUNT (vía datos.gov.co)** | `www.datos.gov.co` | Socrata API | Vehículos en accidentes — alternativa a los anuarios de siniestralidad que requieren login institucional. |

---

## ⚠️ Datos pendientes (Fase 2)

| Dataset | Fuente | Problema | Impacto |
|---------|--------|----------|---------|
| Anuarios siniestralidad 2020-2024 (xlsx) | datosabiertos.bogota.gov.co | Requiere login institucional | Alto — geolocalización precisa de accidentes |
| Demanda post-pandemia (2021-2025) | datosabiertos.bogota.gov.co | Requiere login institucional | Alto — datos actualizados de pasajeros |
| GTFS Transmilenio | Transmilenio S.A. | No disponible públicamente | Alto — horarios y frecuencias en tiempo real |
| Red semafórica | datos.gov.co (`2gfp-jiqi`) | Disponible pero no descargado | Medio — feature de congestión |
| Ciclovías / BiciTM | IDECA | Por explorar | Medio — capa de bicicletas |
| Aforos vehiculares | SIMUR / SDM | Por explorar | Medio — flujos vehiculares reales |

---

## Cómo reproducir la descarga

```bash
cd movicol-data
make download    # Descarga datasets de Socrata API (datos.gov.co)
```

Para los GeoJSON de GIS Transmilenio y ArcGIS Hub, ver los README de cada subcarpeta con las URLs específicas.
