# 📈 demanda/ — Demanda de Pasajeros

Datos históricos de pasajeros del transporte masivo en Colombia.

## Fuente
- **datos.gov.co** — ID: `2h8t-2zik`
- **Tipo:** 🏛️ Gubernamental — Socrata API (MinTransporte)
- **Clasificación:** Dato abierto oficial

## Archivo

| Archivo | Registros | Período | Ciudades |
|---------|-----------|---------|----------|
| `pasajeros_transporte_masivo.csv` | 1,490 | Abril–Agosto 2020 | Bogotá, Medellín, Cali, Barranquilla, Bucaramanga, Pereira, Cartagena |

## Campos
- `fecha` — Fecha del registro
- `ciudad` — Ciudad del sistema
- `sistema` — Nombre del sistema (TRANSMILENIO, SITVA, MIO, etc.)
- `pasajeros_dia` — Pasajeros por día
- `pasajeros_d_a_t_pico_laboral` — Pasajeros día típico laboral
- `pasajeros_d_a_s_bado` — Pasajeros día sábado
- `pasajeros_d_a_festivo` — Pasajeros día festivo

## Uso en el modelo
- **Feature de demanda:** Indica la "normalidad" del sistema por día de la semana
- **Variable temporal:** Permite al modelo entender patrones cíclicos (laboral vs fin de semana)

## ⚠️ Limitación: Solo período pandemia (2020)

**Problema:** El dataset solo cubre abril–agosto 2020. La demanda durante pandemia NO refleja el comportamiento normal del sistema (caída del 60-80% en pasajeros).

**¿Por qué no hay datos más recientes?**
- datos.gov.co solo tiene este dataset público de pasajeros de transporte masivo
- Los datos 2021-2025 existen en `datosabiertos.bogota.gov.co` pero requieren login institucional
- No hay API pública alternativa

**Mitigación en el modelo:**
- Se usan los datos como referencia de patrones relativos (lunes > domingo), no como valores absolutos
- Se complementa con variables sintéticas (día_semana, hora, festivo, hora_pico)
- El modelo aprende la ESTRUCTURA temporal, no los valores exactos de pandemia

## Estado: ✅ MÁXIMO DISPONIBLE PÚBLICAMENTE
Este es el 100% de lo que datos.gov.co ofrece para este dataset (1,490 de 1,490 registros).
