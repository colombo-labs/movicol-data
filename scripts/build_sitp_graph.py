"""Build enriched SITP route graph with segment distances and estimated times.

Validates that all 689 SITP routes have complete route coordinates,
calculates real distances per segment (stop-to-stop) using haversine,
aggregates estimated travel times, and exports the graph as JSON
for consumption by movicol-ai.
"""

import json
import math
from collections import defaultdict
from pathlib import Path

EXPORTS_DIR = Path(__file__).parent.parent / "exports" / "backend"
OUTPUT_DIR = Path(__file__).parent.parent / "exports" / "ai"
GEOJSON_PATH = EXPORTS_DIR / "sitp_rutas_paraderos.geojson"

# Average bus speed by zone type (km/h) for time estimation
SPEED_SITP_KMH = 15.0
# Average frequency in minutes for SITP routes (proxy from usage data)
BASE_FREQUENCY_MIN = 10.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate haversine distance in km between two points."""
    r = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def load_sitp_data() -> dict:
    """Load SITP GeoJSON data."""
    with open(GEOJSON_PATH) as f:
        return json.load(f)


def build_routes(data: dict) -> dict:
    """Group features by route and sort stops by 'orden' field."""
    routes: dict[str, list[dict]] = defaultdict(list)
    for feat in data["features"]:
        props = feat.get("properties", {})
        geom = feat.get("geometry")
        ruta = props.get("ruta")
        if not ruta or not geom or not geom.get("coordinates"):
            continue
        routes[ruta].append(
            {
                "cenefa": props.get("cenefa", ""),
                "nombre": props.get("nombre", ""),
                "orden": props.get("orden", ""),
                "lat": geom["coordinates"][1],
                "lon": geom["coordinates"][0],
                "localidad": props.get("localidad", ""),
                "zona": props.get("zona_nueva", ""),
            }
        )
    # Sort stops within each route by 'orden'
    for ruta in routes:
        routes[ruta].sort(key=lambda s: s["orden"])
    return dict(routes)


def validate_routes(routes: dict) -> dict:
    """Validate routes and report completeness statistics."""
    stats = {
        "total_routes": len(routes),
        "routes_with_coords": 0,
        "routes_incomplete": [],
        "total_stops": 0,
        "stops_with_coords": 0,
    }
    for ruta, stops in routes.items():
        stats["total_stops"] += len(stops)
        valid = [s for s in stops if s["lat"] != 0 and s["lon"] != 0]
        stats["stops_with_coords"] += len(valid)
        if len(valid) == len(stops) and len(stops) >= 2:
            stats["routes_with_coords"] += 1
        else:
            stats["routes_incomplete"].append(
                {"ruta": ruta, "total": len(stops), "with_coords": len(valid)}
            )
    return stats


def compute_segments(routes: dict) -> tuple[list[dict], list[dict], list[dict]]:
    """Compute segment distances, times, and build graph nodes/edges."""
    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    route_summaries: list[dict] = []

    for ruta, stops in routes.items():
        valid_stops = [s for s in stops if s["lat"] != 0 and s["lon"] != 0]
        if len(valid_stops) < 2:
            continue

        route_dist = 0.0
        route_time = 0.0
        route_edges = []

        for i, stop in enumerate(valid_stops):
            node_id = stop["cenefa"] or f"{ruta}_{i}"
            if node_id not in nodes:
                nodes[node_id] = {
                    "id": node_id,
                    "nombre": stop["nombre"],
                    "lat": stop["lat"],
                    "lon": stop["lon"],
                    "localidad": stop["localidad"],
                    "zona": stop["zona"],
                    "rutas": [ruta],
                }
            else:
                if ruta not in nodes[node_id]["rutas"]:
                    nodes[node_id]["rutas"].append(ruta)

            if i > 0:
                prev = valid_stops[i - 1]
                prev_id = prev["cenefa"] or f"{ruta}_{i - 1}"
                dist_km = haversine_km(prev["lat"], prev["lon"], stop["lat"], stop["lon"])
                time_min = (dist_km / SPEED_SITP_KMH) * 60

                edge = {
                    "source": prev_id,
                    "target": node_id,
                    "ruta": ruta,
                    "distance_km": round(dist_km, 4),
                    "time_min": round(time_min, 2),
                }
                edges.append(edge)
                route_edges.append(edge)
                route_dist += dist_km
                route_time += time_min

        # Estimate frequency based on number of stops (proxy)
        freq_min = max(5, min(20, BASE_FREQUENCY_MIN * (30 / max(len(valid_stops), 1))))

        route_summaries.append(
            {
                "ruta": ruta,
                "total_stops": len(valid_stops),
                "total_distance_km": round(route_dist, 2),
                "total_time_min": round(route_time, 1),
                "avg_segment_km": round(route_dist / max(len(valid_stops) - 1, 1), 3),
                "estimated_frequency_min": round(freq_min, 1),
            }
        )

    return list(nodes.values()), edges, route_summaries


def build_graph_json(
    nodes: list[dict],
    edges: list[dict],
    route_summaries: list[dict],
    stats: dict,
) -> dict:
    """Build the final graph JSON for AI consumption."""
    return {
        "metadata": {
            "description": "SITP enriched route graph for MoviCol AI pathfinding",
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "total_routes": len(route_summaries),
            "validation": {
                "routes_with_complete_coords": stats["routes_with_coords"],
                "total_routes": stats["total_routes"],
                "completeness_pct": round(
                    stats["routes_with_coords"] / max(stats["total_routes"], 1) * 100, 1
                ),
            },
        },
        "nodes": nodes,
        "edges": edges,
        "routes": route_summaries,
    }


def main() -> None:
    """Run the SITP graph building pipeline."""
    print("\n=== SITP Route Graph Builder ===\n")

    print("Loading SITP data...")
    data = load_sitp_data()
    print(f"  Loaded {len(data['features'])} features")

    print("\nBuilding routes...")
    routes = build_routes(data)
    print(f"  Found {len(routes)} routes")

    print("\nValidating routes...")
    stats = validate_routes(routes)
    print(f"  Routes with complete coords: {stats['routes_with_coords']}/{stats['total_routes']}")
    print(f"  Stops with coords: {stats['stops_with_coords']}/{stats['total_stops']}")
    if stats["routes_incomplete"]:
        print(f"  Incomplete routes: {len(stats['routes_incomplete'])}")

    print("\nComputing segments (distances, times)...")
    nodes, edges, route_summaries = compute_segments(routes)
    print(f"  Nodes: {len(nodes)}")
    print(f"  Edges: {len(edges)}")
    print(f"  Routes processed: {len(route_summaries)}")

    print("\nBuilding graph JSON...")
    graph = build_graph_json(nodes, edges, route_summaries, stats)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "sitp_graph_enriched.json"
    with open(output_path, "w") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)
    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"\n  Saved: {output_path} ({size_mb:.1f} MB)")

    print("\n=== Done ===")
    print(f"  Total routes: {len(route_summaries)}")
    total_dist = sum(r["total_distance_km"] for r in route_summaries)
    print(f"  Total network distance: {total_dist:.1f} km")
    avg_stops = sum(r["total_stops"] for r in route_summaries) / max(len(route_summaries), 1)
    print(f"  Avg stops per route: {avg_stops:.0f}")


if __name__ == "__main__":
    main()
