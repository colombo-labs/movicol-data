# 📊 MoviCol Data

Pipeline ETL y datos de movilidad urbana para el proyecto MoviCol.

## Qué es

Este repositorio contiene:
1. **Datos crudos** descargados de fuentes abiertas colombianas (`data/raw/`)
2. **Scripts ETL** para descargar, procesar y cargar datos (`scripts/`)
3. **Grafos construidos** de la red de transporte de Bogotá (`data/graphs/`)
4. **Catálogo** de todos los datasets con sus fuentes y estado (`config/datasets.yaml`)

## Datos disponibles

| Categoría | Fuente | Archivos | Tamaño |
|-----------|--------|----------|--------|
| TransMilenio (estaciones, rutas) | GIS Transmilenio | 6 | 3.4 MB |
| SITP (paraderos, rutas zonales) | datos.gov.co + ArcGIS Hub | 8 | 37 MB |
| Demanda de pasajeros | datos.gov.co | 1 | 96 KB |
| Siniestralidad | datos.gov.co + RUNT | 2 | 6 MB |
| Red vial nacional | datos.gov.co | 1 | 14 MB |
| Movilidad vehicular | datos.gov.co | 4 | 11 MB |
| Movilidad urbana | datos.gov.co | 2 | 4.8 MB |
| Red vial urbana (OSM) | OpenStreetMap | 2 | 39 MB |
| **Grafos construidos** | Procesamiento propio | 3 | 63 MB |

**Total: ~178 MB | 30+ archivos | 170,000+ registros**

## Grafos construidos

| Grafo | Nodos | Aristas | Descripción |
|-------|-------|---------|-------------|
| `grafo_movilidad_bogota.graphml` | 7,444 | 41,990 | Grafo base (TM + SITP) |
| `grafo_movilidad_bogota_enriched.graphml` | 7,444 | 41,990 | + features (siniestralidad, centralidad, demanda) |
| `grafo_integrado_bogota.graphml` | ~15,000 | ~80,000 | Integrado con red vial |

## Quick Start

```bash
# Instalar dependencias
make install

# Levantar PostGIS local
docker compose -f docker-compose.dev.yml up -d

# Descargar datos de datos.gov.co (Socrata API)
make download

# Procesar datos y construir grafo
make process

# Cargar a PostGIS
make load
```

## Estructura

```
movicol-data/
├── config/
│   └── datasets.yaml          # Catálogo completo de datasets (fuentes, estado, paths)
├── data/
│   ├── raw/                   # Datos crudos (NO van a git — ver README dentro)
│   ├── processed/             # Datos limpios (se regeneran con make process)
│   └── graphs/                # Grafos NetworkX (.graphml)
├── scripts/
│   ├── download.py            # Descarga de Socrata API
│   ├── process.py             # Limpieza + construcción del grafo
│   └── load_postgis.py        # Carga a PostGIS
├── notebooks/                 # Jupyter notebooks de exploración
├── docker-compose.dev.yml     # PostGIS para desarrollo local
├── pyproject.toml             # Dependencias Python
└── Makefile                   # Task runner
```

## Fuentes de datos

### Gubernamentales (100% datos abiertos — requisito del concurso)
- **datos.gov.co** — Portal nacional de datos abiertos (Socrata API)
- **GIS Transmilenio** — Servicio ArcGIS de Transmilenio S.A.
- **ArcGIS Hub SDM** — Secretaría Distrital de Movilidad

### Complementarias (justificación en data/raw/README.md)
- **OpenStreetMap** — Red vial urbana completa (datos.gov.co solo tiene red nacional)

## Requisitos

- Python 3.11+
- Docker (para PostGIS)

## Concurso

**Datos al Ecosistema 2026: IA para Colombia** — MinTIC
- Organización: Colombo-labs
- Proyecto: MoviCol
