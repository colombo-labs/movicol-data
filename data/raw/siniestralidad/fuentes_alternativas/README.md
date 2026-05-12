# Vehículos en Accidentes — Fuente Alternativa

## Fuente
- **datos.gov.co** — Dataset RUNT (Registro Único Nacional de Tránsito)
- **Marco legal:** Ley 2251 de 2022
- **Tipo:** 🏛️ Gubernamental

## ¿Por qué es "alternativa"?

Los datos ideales son los **Anuarios de Siniestralidad 2017-2024** publicados en `datosabiertos.bogota.gov.co`, que contienen geolocalización precisa de cada accidente. Sin embargo, esos archivos requieren login institucional y no son accesibles vía API pública.

Este dataset del RUNT es la mejor alternativa disponible en datos.gov.co sin restricciones de acceso.

## Archivo
- `vehiculos_accidentes_bogota.csv` — 50,000+ registros (año 2024)

## Contenido
- Tipo de vehículo involucrado
- Clase de accidente
- Gravedad (heridos/muertos)
- Municipio
- **Limitación:** No tiene geolocalización precisa (solo municipio/sector)

## Hallazgos
- 96.5% de accidentes con heridos, 3.5% con muertos
- Motos son el vehículo #1 en accidentes
- 2.7M vehículos registrados en Bogotá
