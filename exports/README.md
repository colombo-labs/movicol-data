# Exported Datasets

Processed GeoJSON files ready to be consumed by frontend and backend services.

## Usage
These files are the **single source of truth**. Copy them to the respective repos:

```bash
# Frontend (TM data)
cp exports/frontend/*.geojson ../movicol-frontend/public/data/

# Backend (SITP data)
cp exports/backend/*.geojson ../movicol-backend/data/
```

## Contents
- `frontend/tm_troncales.geojson` — 20 TransMilenio trunk routes
- `frontend/tm_estaciones.geojson` — 332 TM stations
- `backend/sitp_rutas_paraderos.geojson` — 42,601 stops across 689 routes
- `backend/sitp_paraderos.geojson` — SITP bus stops
