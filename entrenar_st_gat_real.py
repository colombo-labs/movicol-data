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

# 2. Cargar infraestructura y unificar índices
grafo_base = torch.load(PATH_GRAFO, weights_only=False)
df_nodos_infra = pd.read_csv(PATH_NODOS)
df_nodos_infra['num_est_str'] = df_nodos_infra['num_est'].astype(str).str.zfill(5)
nodo_to_idx = {num_est: idx for idx, num_est in enumerate(df_nodos_infra['num_est_str'].unique())}
num_nodos = len(nodo_to_idx)

# 3. Cargar y ordenar Demanda Real cronológicamente
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

# Construir Tensor [Intervalos, Nodos, 1]
X_real = np.zeros((len(intervalos_reales), num_nodos, 1))
for t_idx, intervalo in enumerate(intervalos_reales):
    df_bloque = df_demanda[df_demanda['Intervalo'] == intervalo]
    for _, row in df_bloque.iterrows():
        X_real[t_idx, int(row['nodo_idx']), 0] = row['Validaciones']

# 4. CREAR SECUENCIAS TEMPORALES (Ventana de tiempo de tamaño 4 = 1 hora de historia)
window_size = 4
X_seq, Y_seq = [], []

for i in range(len(X_real) - window_size):
    X_seq.append(X_real[i:i+window_size])         # Pasado: formato [window_size, num_nodos, 1]
    Y_seq.append(X_real[i+window_size])           # Futuro a predecir: formato [num_nodos, 1]

X_seq = torch.tensor(np.array(X_seq), dtype=torch.float)
Y_seq = torch.tensor(np.array(Y_seq), dtype=torch.float)

print(f"📅 Datos secuenciales creados: {X_seq.shape[0]} muestras temporales listas.")

# 5. ARQUITECTURA AVANZADA: ST-GAT (Spatial-Temporal Graph Attention Network)
class STGATTransmilenio(torch.nn.Module):
    def __init__(self, in_channels, hidden_channels, out_channels, window_size, heads=4):
        super(STGATTransmilenio, self).__init__()
        # Componente Espacial: Capa GAT
        self.gat = GATConv(in_channels, hidden_channels, heads=heads, edge_dim=2, dropout=0.1)
        
        # Componente Temporal: GRU Celda Recurrente
        # La entrada a la GRU por nodo será la salida de las cabezas de la GAT
        self.gru = torch.nn.GRU(hidden_channels * heads, hidden_channels, batch_first=True)
        
        # Capa de Salida Lineal para Regresión
        self.fully_connected = torch.nn.Linear(hidden_channels, out_channels)

    def forward(self, x_seq, edge_index, edge_attr):
        # x_seq tiene tamaño: [window_size, num_nodos, 1]
        w_size, n_nodes, f_size = x_seq.shape
        
        # Procesar cada paso de la ventana temporal a través de la GAT espacial
        gat_outputs = []
        for t in range(w_size):
            x_t = x_seq[t] # [num_nodos, 1]
            h_spatial = F.elu(self.gat(x_t, edge_index, edge_attr)) # [num_nodos, hidden_channels * heads]
            gat_outputs.append(h_spatial.unsqueeze(0)) # Guardar paso temporal
            
        # Unificar pasos para la GRU -> forma: [num_nodos, window_size, hidden_channels * heads]
        gat_outputs = torch.cat(gat_outputs, dim=0).transpose(0, 1)
        
        # Pasar la secuencia temporal por la memoria GRU
        gru_out, _ = self.gru(gat_outputs) # gru_out: [num_nodos, window_size, hidden_channels]
        
        # Tomar únicamente el último estado de la memoria (el más reciente)
        last_temporal_state = gru_out[:, -1, :] # [num_nodos, hidden_channels]
        
        # Predicción final
        output = self.fully_connected(last_temporal_state) # [num_nodos, out_channels]
        return output

# 6. CONFIGURAR ENTRENAMIENTO AVANZADO
model = STGATTransmilenio(in_channels=1, hidden_channels=16, out_channels=1, window_size=window_size, heads=4)
optimizer = torch.optim.Adam(model.parameters(), lr=0.003, weight_decay=1e-4)
criterion = torch.nn.MSELoss()

print("\n🚀 Iniciando Entrenamiento Espacio-Temporal con Memoria Histórica (50 Épocas)...")
model.train()

for epoch in range(1, 51):
    loss_total = 0
    for s in range(X_seq.shape[0]):
        optimizer.zero_grad()
        
        x_seq_sample = X_seq[s]  # Ventana de 4 intervalos del pasado
        y_real_sample = Y_seq[s] # El intervalo objetivo del futuro
        
        y_pred = model(x_seq_sample, grafo_base.edge_index, grafo_base.edge_attr)
        
        loss = criterion(y_pred, y_real_sample)
        loss.backward()
        optimizer.step()
        
        loss_total += loss.item()
        
    loss_promedio = loss_total / X_seq.shape[0]
    
    if epoch % 10 == 0 or epoch == 1:
        rmse = np.sqrt(loss_promedio)
        print(f"   Epoch {epoch:02d}/50 -> Loss (MSE): {loss_promedio:.2f} | RMSE: {rmse:.2f} pasajeros")

# Guardar nuevo modelo robusto
PATH_ST_MODELO = os.path.join(GRAPHS_DIR, "st_gat_transmilenio_pesos.pth")
torch.save(model.state_dict(), PATH_ST_MODELO)
print(f"\n👑 ¡Modelo ST-GAT entrenado y guardado en: {PATH_ST_MODELO}")