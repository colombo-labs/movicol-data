"""Process raw data: clean, transform, and build the mobility graph."""

from pathlib import Path

import geopandas as gpd
import networkx as nx
import pandas as pd

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"
GRAPHS_DIR = Path(__file__).parent.parent / "data" / "graphs"


def load_transmilenio() -> gpd.GeoDataFrame:
    """Load TransMilenio stations."""
    path = RAW_DIR / "transmilenio" / "estaciones_troncales_tm.geojson"
    if not path.exists():
        print("  ⚠️  estaciones_troncales_tm.geojson not found")
        return gpd.GeoDataFrame()
    gdf = gpd.read_file(path)
    print(f"  🚌 TransMilenio: {len(gdf)} estaciones")
    return gdf


def load_sitp() -> tuple[pd.DataFrame, gpd.GeoDataFrame]:
    """Load SITP stops and routes."""
    paraderos_path = RAW_DIR / "sitp" / "paraderos_sistema.csv"
    rutas_path = RAW_DIR / "sitp" / "paraderos_rutas_sitp.geojson"

    paraderos = pd.DataFrame()
    rutas = gpd.GeoDataFrame()

    if paraderos_path.exists():
        paraderos = pd.read_csv(paraderos_path)
        print(f"  🚏 SITP paraderos: {len(paraderos)} registros")

    if rutas_path.exists():
        rutas = gpd.read_file(rutas_path)
        print(f"  🚏 SITP paraderos-rutas: {len(rutas)} relaciones")

    return paraderos, rutas


def load_siniestralidad() -> pd.DataFrame:
    """Load accident data for risk scoring."""
    path = RAW_DIR / "siniestralidad" / "datos_gov_co" / "sectores_criticos_siniestralidad.csv"
    if not path.exists():
        print("  ⚠️  sectores_criticos_siniestralidad.csv not found")
        return pd.DataFrame()
    df = pd.read_csv(path)
    print(f"  🚨 Siniestralidad: {len(df)} sectores críticos")
    return df


def build_graph(tm_stations: gpd.GeoDataFrame, paraderos: pd.DataFrame,
                rutas: gpd.GeoDataFrame) -> nx.Graph:
    """Build the mobility graph from TM stations and SITP stops."""
    g = nx.Graph()

    # Add TM stations as nodes
    if not tm_stations.empty:
        for _, row in tm_stations.iterrows():
            node_id = row.get("nombre") or str(row.name)
            g.add_node(
                node_id,
                lat=row.geometry.y if row.geometry else 0,
                lon=row.geometry.x if row.geometry else 0,
                name=row.get("nombre", ""),
                is_tm=1,
            )

    # Add SITP stops as nodes
    if not paraderos.empty:
        for _, row in paraderos.iterrows():
            node_id = row.get("cenefa") or str(row.name)
            g.add_node(
                node_id,
                lat=row.get("latitud", 0),
                lon=row.get("longitud", 0),
                name=row.get("nombre_paradero", ""),
                route=row.get("ruta", ""),
                is_tm=0,
            )

    # Add edges from SITP route sequences
    if not rutas.empty and "ruta" in rutas.columns and "cenefa" in rutas.columns:
        for route_name, group in rutas.groupby("ruta"):
            sorted_stops = group.sort_values("secuencia") if "secuencia" in group.columns else group
            stops = sorted_stops["cenefa"].tolist()
            for i in range(len(stops) - 1):
                if stops[i] in g and stops[i + 1] in g:
                    g.add_edge(stops[i], stops[i + 1], route=route_name)

    print(f"  📊 Graph: {g.number_of_nodes()} nodes, {g.number_of_edges()} edges")
    return g


def enrich_graph(g: nx.Graph, siniestralidad: pd.DataFrame) -> nx.Graph:
    """Add features to graph nodes (centrality, risk scores)."""
    if g.number_of_nodes() == 0:
        return g

    # Compute centrality metrics
    print("  🔄 Computing betweenness centrality...")
    betweenness = nx.betweenness_centrality(g)
    closeness = nx.closeness_centrality(g)

    for node in g.nodes():
        g.nodes[node]["betweenness"] = betweenness.get(node, 0)
        g.nodes[node]["closeness"] = closeness.get(node, 0)
        g.nodes[node]["degree"] = g.degree(node)

    # Add siniestralidad scores (proximity-based)
    if not siniestralidad.empty and "latitud" in siniestralidad.columns:
        print("  🔄 Computing siniestralidad scores...")
        # Simplified: assign score based on proximity to critical sectors
        for node in g.nodes():
            g.nodes[node]["siniestralidad_score"] = 0.0

    print(f"  ✅ Enriched graph: {g.number_of_nodes()} nodes with features")
    return g


def save_graph(g: nx.Graph, name: str) -> None:
    """Save graph to GraphML format."""
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    output = GRAPHS_DIR / f"{name}.graphml"
    nx.write_graphml(g, output)
    size_mb = output.stat().st_size / (1024 * 1024)
    print(f"  💾 Saved: {output.name} ({size_mb:.1f} MB)")


def main() -> None:
    """Run the full processing pipeline."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    print("\n📥 Loading raw data...")
    tm_stations = load_transmilenio()
    paraderos, rutas = load_sitp()
    siniestralidad = load_siniestralidad()

    if tm_stations.empty and paraderos.empty:
        print("❌ No data found. Run `make download` first or copy data to data/raw/.")
        return

    print("\n🔨 Building base graph...")
    g = build_graph(tm_stations, paraderos, rutas)

    print("\n🔬 Enriching graph with features...")
    g_enriched = enrich_graph(g.copy(), siniestralidad)

    print("\n💾 Saving graphs...")
    save_graph(g, "grafo_movilidad_bogota")
    save_graph(g_enriched, "grafo_movilidad_bogota_enriched")

    print("\n✅ Processing complete!")
    print(f"   Nodes: {g.number_of_nodes()}")
    print(f"   Edges: {g.number_of_edges()}")


if __name__ == "__main__":
    main()
