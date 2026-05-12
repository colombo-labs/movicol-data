# 🚗 vehicular/ — Movilidad Vehicular

Datos de parque automotor, tráfico en peajes y pesaje de vehículos.

## Estado: ✅ MÁXIMO DISPONIBLE PÚBLICAMENTE

Se descargó **todo** lo que datos.gov.co ofrece de tráfico vehicular sin restricciones:
- Parque automotor (RUNT)
- Tráfico en peajes INVIAS + ANI
- Pesaje de vehículos de carga

## Fuente
- **datos.gov.co** — Socrata API
- **Tipo:** 🏛️ Gubernamental (MinTransporte, ANI, INVIAS, RUNT)
- **Clasificación:** Datos abiertos oficiales

## Archivos

| Archivo | Registros | Tamaño | Descripción |
|---------|-----------|--------|-------------|
| `parque_automotor_bogota.csv` | 3,160 | 258 KB | Vehículos registrados por municipio |
| `trafico_peajes_invias.csv` | 60,780 | 2.5 MB | Tráfico en peajes INVIAS |
| `trafico_vehicular_peajes_ani.csv` | ~50,000 | 4.5 MB | Tráfico vehicular peajes ANI |
| `pesaje_vehiculos_carga.csv` | ~50,000 | 3.5 MB | Pesaje de vehículos de carga |

## Cobertura

| Aspecto | Estado | Detalle |
|---------|--------|---------|
| Parque automotor | ✅ 100% | 2.7M vehículos registrados en Bogotá |
| Tráfico en peajes | ✅ 100% | INVIAS + ANI (110K+ registros) |
| Pesaje vehículos carga | ✅ 100% | 50K registros |
| Aforos vehiculares urbanos | ❌ No disponible | SIMUR/SDM — no público |
| Velocidades promedio | ❌ No disponible | SIMUR/SDM — no público |
| Red semafórica | ❌ No funcional | datos.gov.co `2gfp-jiqi` — API retorna error |

## ¿Por qué no está al 100% absoluto?

Los datos de **aforos vehiculares** (conteos de vehículos por vía) y **velocidades promedio** son gestionados por:
- **SIMUR** (Sistema Inteligente de Movilidad Urbana Regional)
- **SDM** (Secretaría Distrital de Movilidad)

Estos datos NO están publicados en datos.gov.co ni en ninguna API pública. Son de uso interno de la SDM.

La **red semafórica** (`2gfp-jiqi`) existe en datos.gov.co pero la API retorna error al consultarla (posible dataset no tabular o restringido).

## Mitigación en el modelo

Con los datos disponibles:
1. **Parque automotor** → Densidad vehicular por zona
2. **Tráfico peajes** → Proxy de flujo vehicular en corredores principales
3. **OSM** → La red vial de OSM incluye clasificación de vías (primaria/secundaria/residencial) que sirve como proxy de volumen vehicular
4. **Siniestralidad** → Zonas con muchos accidentes ≈ zonas con mucho tráfico

## Uso en el modelo
- **Feature complementaria:** Volumen vehicular por zona
- **Correlación:** Zonas con alto tráfico vehicular → mayor probabilidad de congestión en transporte público
