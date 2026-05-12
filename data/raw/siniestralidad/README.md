# 🚨 siniestralidad/ — Accidentalidad Vial

Datos de siniestralidad vial para detección de zonas de riesgo.

## Estado: ✅ MÁXIMO DISPONIBLE PÚBLICAMENTE

Se descargó **todo** lo que datos.gov.co ofrece sin restricciones de acceso:
- 316 sectores críticos con geolocalización (ANSV)
- 50,000 registros de vehículos en accidentes (RUNT)

## Estructura

```
siniestralidad/
├── datos_gov_co/
│   └── sectores_criticos_siniestralidad.csv    ← 316 tramos con lat/lon
└── fuentes_alternativas/
    └── vehiculos_accidentes_bogota.csv          ← 50,000 accidentes (2024)
```

## Fuentes (ambas gubernamentales)

| Archivo | Fuente | ID | Entidad |
|---------|--------|-----|---------|
| `sectores_criticos_siniestralidad.csv` | datos.gov.co | `rs3u-8r4q` | ANSV |
| `vehiculos_accidentes_bogota.csv` | datos.gov.co | Ley 2251-2022 | RUNT |

## Cobertura

| Aspecto | Estado | Detalle |
|---------|--------|---------|
| Sectores críticos (tramos peligrosos) | ✅ 100% | 316 tramos con lat/lon |
| Vehículos en accidentes | ✅ 100% | 50,000 registros (2024) |
| Geolocalización precisa por accidente | ❌ No disponible | Requiere login en datosabiertos.bogota.gov.co |
| Series temporales (2017-2024) | ❌ No disponible | Anuarios xlsx requieren login institucional |

## ¿Por qué no está al 100% absoluto?

Los **Anuarios de Siniestralidad 2017-2024** de la Secretaría de Movilidad contienen:
- Geolocalización EXACTA de cada accidente (lat/lon por evento)
- 3 secciones: Siniestros, Vehículos, Actor Vial
- Datos de 2017 a 2024

**Están publicados en `datosabiertos.bogota.gov.co` pero requieren login institucional.**
No son accesibles vía API pública ni están en datos.gov.co.

## Mitigación en el modelo

Con los datos disponibles:
1. **Sectores críticos** → Score de riesgo por proximidad (nodos a <2km de un sector crítico)
2. **Vehículos accidentes** → Estadísticas por municipio/tipo de vehículo
3. **Feature engineering** → Se cruza con la red vial para asignar riesgo a aristas del grafo

## Hallazgos con datos actuales
- Zona más peligrosa: Fontibón (KR 123) — 13 fallecidos, score 2.99
- 96.5% de accidentes con heridos, 3.5% con muertos
- Motos son el vehículo #1 en accidentes
