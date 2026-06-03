import os
import re
import pandas as pd
import numpy as np
import torch
from torch_geometric.data import Data

# 1. Configurar rutas relativas basadas en tu estructura
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else os.getcwd()
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
GRAPHS_DIR = os.path.join(BASE_DIR, "data", "graphs")
INFRA_DIR = os.path.join(BASE_DIR, "data", "raw", "infraestructura")

print("⏳ Cargando datos del ecosistema Transmilenio...")
df_nodos_infra = pd.read_csv(os.path.join(PROCESSED_DIR, "nodos_infraestructura_gat.csv"))
df_aristas = pd.read_csv(os.path.join(GRAPHS_DIR, "aristas_infraestructura_gat.csv"))
df_estaciones_base = pd.read_csv(os.path.join(INFRA_DIR, "estaciones_troncales.csv"))

# Usaremos 'demanda_con_nodos.csv' o 'demanda_troncal_2025_final.csv'
path_demanda = os.path.join(PROCESSED_DIR, "demanda_con_nodos.csv")
if not os.path.exists(path_demanda):
    path_demanda = os.path.join(PROCESSED_DIR, "demanda_troncal_2025_final.csv")
df_demanda = pd.read_csv(path_demanda)

print("📍 Sincronizando identificadores de infraestructura...")

# ¡Corregido aquí! Cambiado pd.series por pd.Series con S mayúscula
dict_obj_to_num = pd.Series(df_estaciones_base.num_est.values, index=df_estaciones_base.objectid.values).to_dict()

# Mapeamos las aristas para que queden expresadas en el formato unificado 'num_est'
df_aristas['source_num'] = df_aristas['source'].map(dict_obj_to_num)
df_aristas['target_num'] = df_aristas['target'].map(dict_obj_to_num)

# Rellenar con ceros a la izquierda para asegurar formato de 5 dígitos (ej: '07103')
df_nodos_infra['num_est_str'] = df_nodos_infra['num_est'].astype(str).str.zfill(5)
df_aristas['source_num'] = df_aristas['source_num'].astype(str).str.zfill(5)
df_aristas['target_num'] = df_aristas['target_num'].astype(str).str.zfill(5)

# 2. Definir los índices correlativos estrictos de PyG (0 a N-1) basados en 'num_est_str'
nodos_unicos = df_nodos_infra['num_est_str'].unique()
nodo_to_idx = {num_est: idx for idx, num_est in enumerate(nodos_unicos)}
num_nodos = len(nodo_to_idx)
print(f"   -> {num_nodos} estaciones indexadas correctamente para la GAT.")

# 3. Construcción del Tensor Edge Index [2, E]
df_aristas_validas = df_aristas[
    df_aristas['source_num'].isin(nodo_to_idx.keys()) & 
    df_aristas['target_num'].isin(nodo_to_idx.keys())
].copy()

df_aristas_validas['source_idx'] = df_aristas_validas['source_num'].map(nodo_to_idx)
# ¡Corregido aquí también! Se quitó la variable fantasma que se coló en el medio
df_aristas_validas['target_idx'] = df_aristas_validas['target_num'].map(nodo_to_idx)

edge_index = torch.tensor(
    df_aristas_validas[['source_idx', 'target_idx']].values.T, 
    dtype=torch.long
)

# Features de las aristas (normalizadas)
dist_max = df_aristas_validas['weight_distance_m'].max()
df_aristas_validas['dist_norm'] = df_aristas_validas['weight_distance_m'] / (dist_max if dist_max > 0 else 1)
edge_attr = torch.tensor(
    df_aristas_validas[['dist_norm', 'tipo_via']].values, 
    dtype=torch.float
)

# 4. Procesamiento y limpieza de la Demanda Temporal
print("📊 Extrayendo códigos de estaciones desde la demanda...")

def extraer_codigo_estacion(texto):
    match = re.search(r'\((\d+)\)', str(texto))
    return match.group(1).zfill(5) if match else None

df_demanda['num_est_str'] = df_demanda['Estación'].apply(extraer_codigo_estacion)

# Asignar el índice numérico correlativo de la GAT a la demanda
df_demanda['nodo_idx'] = df_demanda['num_est_str'].map(nodo_to_idx)
df_demanda = df_demanda.dropna(subset=['nodo_idx'])

intervalos_disponibles = sorted(df_demanda['Intervalo'].unique())
print(f"📅 Se detectaron {len(intervalos_disponibles)} intervalos de 15 minutos en la demanda.")

# 5. Estructurar Atributos de Nodos (X) - Caso Piloto (Primer Intervalo disponible)
x_matriz = np.zeros((num_nodos, 1))

if len(intervalos_disponibles) > 0:
    primer_intervalo = intervalos_disponibles[0]
    print(f"⏰ Extrayendo matriz de demanda inicial para el intervalo: {primer_intervalo}")
    
    df_bloque = df_demanda[df_demanda['Intervalo'] == primer_intervalo]
    for _, row in df_bloque.iterrows():
        idx_nodo = int(row['nodo_idx'])
        x_matriz[idx_nodo, 0] = row['Validaciones']
else:
    print("⚠️ Error Crítico: No coincide ningún ID extraído de la demanda con tu infraestructura.")

x_tensor = torch.tensor(x_matriz, dtype=torch.float)

# 6. Empaquetar todo en el Objeto Data de PyTorch Geometric
grafo_pyg = Data(x=x_tensor, edge_index=edge_index, edge_attr=edge_attr)

print("\n👑 ¡Objeto PyTorch Geometric estructurado exitosamente!")
print("-" * 60)
print(f"Estructura del Objeto: {grafo_pyg}")
print(f"-> Nodos Operativos (Estaciones): {grafo_pyg.num_nodes}")
print(f"-> Conexiones Activas (Aristas): {grafo_pyg.num_edges}")
print(f"-> Variables por Nodo (Validaciones): {grafo_pyg.num_node_features}")
print(f"-> Variables por Arista (Distancia/Vía): {grafo_pyg.num_edge_features}")
print("-" * 60)

# Guardar a disco
path_save_graph = os.path.join(GRAPHS_DIR, "transmilenio_graph_data.pt")
torch.save(grafo_pyg, path_save_graph)
print(f"💾 Grafo guardado de manera limpia en: {path_save_graph}\n")