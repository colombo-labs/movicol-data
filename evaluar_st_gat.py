import os
import re
import pandas as pd
import numpy as np
import torch
import torch.nn.functional as F
from torch_geometric.nn import GATConv

# 1. Configurar rutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else os.getcwd()
GRAPHS_DIR = os.path.join(BASE_DIR, "data", "graphs")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")

PATH_GRAFO = os.path.join(GRAPHS_DIR, "transmilenio_graph_data.pt")
PATH_NODOS = os.path.join(PROCESSED_DIR, "nodos_infraestructura_gat.csv")
PATH_PESOS_ST = os.path.join(GRAPHS_DIR, "st_gat_transmilenio_pesos.pth")

# 2. Cargar infraestructura
grafo_base = torch.load(PATH_GRAFO, weights_only=False)
df_nodos_infra = pd.read_csv(PATH_NODOS)
df_nodos_infra['num_est_str'] = df_nodos_infra['num_est'].astype(str).str.zfill(5)
nodo_to_idx = {num_est: idx for idx, num_est in enumerate(df_nodos_infra['num_est_str'].unique())}
idx_to_name = {idx: row['nom_est'] for idx, row in df_nodos_infra.iterrows() if row['num_est_str'] in nodo_to_idx}
num_nodos = len(nodo_to_idx)

# 3. Cargar y ordenar Demanda
df_demanda = pd.read_csv(os.path.join(PROCESSED_DIR, "demanda_con_nodos.csv"))
def extraer_codigo(texto):
    match = re.search(r'\((\d+)\)', str(texto))
    return match.group(1).zfill(5) if match else None

df_demanda['num_est_str'] = df_demanda['Estación'].apply(extraer_codigo)
df_demanda['nodo_idx'] = df_demanda['num_est_str'].map(nodo_to_idx)
df_demanda = df_demanda.dropna(subset=['nodo_idx'])

def mins_dia(t):
    try: h, m = map(int, str(t).split(':')); return h * 60 + m
    except: return 0

df_demanda['minutos'] = df_demanda['Intervalo'].apply(mins_dia)
df_demanda = df_demanda.sort_values(by=['minutos']).reset_index(drop=True)
intervalos_reales = sorted(df_demanda['Intervalo'].unique(), key=mins_dia)

# Construir Tensor Matriz
X_real = np.zeros((len(intervalos_reales), num_nodos, 1))
for t_idx, intervalo in enumerate(intervalos_reales):
    df_bloque = df_demanda[df_demanda['Intervalo'] == intervalo]
    for _, row in df_bloque.iterrows():
        X_real[t_idx, int(row['nodo_idx']), 0] = row['Validaciones']

# Crear Ventanas temporales
window_size = 4
X_seq, Y_seq = [], []
for i in range(len(X_real) - window_size):
    X_seq.append(X_real[i:i+window_size])
    Y_seq.append(X_real[i+window_size])

X_seq = torch.tensor(np.array(X_seq), dtype=torch.float)
Y_seq = torch.tensor(np.array(Y_seq), dtype=torch.float)

# 4. Definir Arquitectura ST-GAT idéntica
class STGATTransmilenio(torch.nn.Module):
    def __init__(self, in_channels, hidden_channels, out_channels, window_size, heads=4):
        super(STGATTransmilenio, self).__init__()
        self.gat = GATConv(in_channels, hidden_channels, heads=heads, edge_dim=2, dropout=0.1)
        self.gru = torch.nn.GRU(hidden_channels * heads, hidden_channels, batch_first=True)
        self.fully_connected = torch.nn.Linear(hidden_channels, out_channels)

    def forward(self, x_seq, edge_index, edge_attr):
        w_size, n_nodes, f_size = x_seq.shape
        gat_outputs = []
        for t in range(w_size):
            x_t = x_seq[t]
            h_spatial = F.elu(self.gat(x_t, edge_index, edge_attr))
            gat_outputs.append(h_spatial.unsqueeze(0))
            
        gat_outputs = torch.cat(gat_outputs, dim=0).transpose(0, 1)
        gru_out, _ = self.gru(gat_outputs)
        last_temporal_state = gru_out[:, -1, :]
        output = self.fully_connected(last_temporal_state)
        return output

# Inicializar y cargar pesos entrenados
model = STGATTransmilenio(in_channels=1, hidden_channels=16, out_channels=1, window_size=window_size, heads=4)
model.load_state_dict(torch.load(PATH_PESOS_ST, weights_only=False))
model.eval()

# 5. Evaluar Métricas con Datos Reales Secuenciales
print("🧐 Evaluando el modelo ST-GAT Avanzado...")
predicciones = []
reales = []

with torch.no_grad():
    for s in range(X_seq.shape[0]):
        x_sample = X_seq[s]
        y_real_sample = Y_seq[s]
        
        y_pred_sample = model(x_sample, grafo_base.edge_index, grafo_base.edge_attr)
        
        predicciones.append(y_pred_sample.numpy().flatten())
        reales.append(y_real_sample.numpy().flatten())

predicciones = np.array(predicciones)
reales = np.array(reales)

# Calcular métricas globales
mae = np.mean(np.abs(predicciones - reales))
rmse = np.sqrt(np.mean((predicciones - reales) ** 2))
ss_res = np.sum((reales - predicciones) ** 2)
ss_tot = np.sum((reales - np.mean(reales)) ** 2)
r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

print("\n📊 REPORTE DE MÉTRICAS ESTADÍSTICAS (ST-GAT CON MEMORIA):")
print("-" * 65)
print(f"-> Error Medio Absoluto (MAE): {mae:.2f} pasajeros")
print(f"-> Raíz del Error Cuadrático (RMSE): {rmse:.2f} pasajeros")
print(f"-> Nuevo Coeficiente de Determinación (R²): {r2:.4f}")
print("-" * 65)

# Desglose por estaciones
errores_por_estacion = np.mean(np.abs(predicciones - reales), axis=0)
df_analisis = pd.DataFrame({
    'Nombre_Estacion': [idx_to_name.get(i, f"Estacion_{i}") for i in range(len(errores_por_estacion))],
    'MAE_Pasajeros': errores_por_estacion
}).sort_values(by='MAE_Pasajeros', ascending=False)

print("\n🔝 Estaciones con mayor reto de predicción bajo ST-GAT:")
print(df_analisis.head(5).to_string(index=False))