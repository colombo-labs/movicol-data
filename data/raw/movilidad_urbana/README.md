# 🚌 movilidad_urbana/ — Movilidad Complementaria

Datos complementarios de movilidad interurbana y aérea.

## Fuente
- **datos.gov.co** — Socrata API
- **Tipo:** 🏛️ Gubernamental (MinTransporte, Aerocivil)
- **Clasificación:** Datos abiertos oficiales

## Archivos

| Archivo | Registros | Descripción |
|---------|-----------|-------------|
| `pasajeros_carretera_origen_destino.csv` | ~50,000 | Pasajeros por carretera origen-destino |
| `aereo_origen_destino_bogota.csv` | ~200 | Transporte aéreo origen-destino Bogotá |

## Uso en el modelo

- **Feature complementaria:** Volumen de pasajeros que llegan/salen de Bogotá
- **Contexto:** Permite entender la presión sobre terminales de transporte
- **Prioridad:** Baja para el MVP, útil para escalabilidad futura
