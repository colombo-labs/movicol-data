# 📊 data/graphs/ — Grafos Construidos

Grafos de la red de movilidad de Bogotá en formato GraphML (NetworkX).

## Archivos

| Grafo | Nodos | Aristas | Tamaño | Descripción |
|-------|-------|---------|--------|-------------|
| `grafo_movilidad_bogota.graphml` | 7,444 | 41,990 | 8 MB | Grafo base: TM (153 estaciones) + SITP (7,291 paraderos) |
| `grafo_movilidad_bogota_enriched.graphml` | 7,444 | 41,990 | 9.4 MB | Grafo base + features (siniestralidad, centralidad, demanda) |
| `grafo_integrado_bogota.graphml` | ~15,000 | ~80,000 | 45 MB | Integrado con red vial (OSM) |

## Cómo se construyeron

```bash
make process   # Ejecuta scripts/process.py
```

### Grafo base
1. **Nodos TM:** 153 estaciones de `transmilenio/estaciones_troncales_tm.geojson`
2. **Nodos SITP:** 7,291 paraderos únicos de `sitp/paraderos_rutas_sitp.geojson` (deduplicados por cenefa)
3. **Aristas TM:** 83 rutas troncales conectando estaciones
4. **Aristas SITP:** 41,907 secuencias de paradas por ruta

### Grafo enriquecido (features por nodo)
- `lat`, `lon` — Coordenadas geográficas
- `grado` — Número de conexiones
- `betweenness` — Centralidad de intermediación
- `closeness` — Centralidad de cercanía
- `siniestralidad_score` — Índice de peligrosidad (sectores críticos a <2km)
- `fallecidos_cercanos` — Fallecidos en accidentes cercanos
- `is_tm` — 1 si es estación TM, 0 si es paradero SITP

### Grafo integrado
- Todo lo anterior + segmentos de vía de OSM como aristas adicionales

## Uso

```python
import networkx as nx

# Cargar grafo
G = nx.read_graphml("data/graphs/grafo_movilidad_bogota_enriched.graphml")

print(f"Nodos: {G.number_of_nodes()}")   # 7,444
print(f"Aristas: {G.number_of_edges()}")  # 41,990
```

## Regenerar

Si los datos raw cambian, regenerar con:
```bash
make process
```
