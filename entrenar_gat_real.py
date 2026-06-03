import os
import re
import pandas as pd
import numpy as np
import torch
import torch.nn.functional as F
from torch_geometric.nn import GATConv

# 1. Rutas del proyecto
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else os.getcwd()
GRAPHS_DIR = os.path.join(BASE_DIR, "data", "graphs")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
INFRA_DIR = os.path.join(BASE_DIR, "data", "raw", "infraestructura")

PATH_GRAFO = os.path.join(GRAPHS_DIR, "transmilenio_graph_data.pt")
PATH_NODOS = os.path.join(PROCESSED_DIR, "nodos_infraestructura_gat.csv")

# 2. Cargar infraestructura y mapear índices correlativos (Igual al proceso anterior)
print("⏳ Cargando infraestructura y base del grafo...")
grafo_base = torch.load(PATH_GRAFO, weights_only=False)
df_nodos_infra = pd.read_csv(PATH_NODOS)

df_nodos_infra['num_est_str'] = df_nodos_infra['num_est'].astype(str).str.zfill(5)
nodos_unicos = df_nodos_infra['num_est_str'].unique()
nodo_to_idx = {num_est: idx for idx, num_est in enumerate(nodos_unicos)}
num_nodos = len(nodo_to_idx)

# 3. Cargar y procesar el archivo de demanda REAL
print("📊 Cargando y ordenando tus datos reales de demanda...")
path_demanda = os.path.join(PROCESSED_DIR, "demanda_con_nodos.csv")
if not os.path.exists(path_demanda):
    path_demanda = os.path.join(PROCESSED_DIR, "demanda_troncal_2025_final.csv")
df_demanda = pd.read_csv(path_demanda)

# Extraer códigos en formato '07103'
def extraer_codigo_estacion(texto):
    match = re.search(r'\((\d+)\)', str(texto))
    return match.group(1).zfill(5) if match else None

df_demanda['num_est_str'] = df_demanda['Estación'].apply(extraer_codigo_estacion)
df_demanda['nodo_idx'] = df_demanda['num_est_str'].map(nodo_to_idx)
df_demanda = df_demanda.dropna(subset=['nodo_idx'])

# Asegurar orden cronológico de los intervalos usando Hora_Num e Intervalo
# Creamos una columna auxiliar para ordenar de forma natural (ej: 04:15 antes de 13:00)
def minutos_del_dia(texto_intervalo):
    try:
        h, m = map(int, str(texto_intervalo).split(':'))
        return h * 60 + m
    except:
        return 0

df_demanda['minutos'] = df_demanda['Intervalo'].apply(minutos_del_dia)
df_demanda = df_demanda.sort_values(by=['minutos']).reset_index(drop=True)

intervalos_reales = sorted(df_demanda['Intervalo'].unique(), key=minutos_del_dia)
num_intervalos = len(intervalos_reales)
print(f"📅 Se estructurarán {num_intervalos} bloques de tiempo reales de 15 minutos.")

# 4. Construir el Tensor Tridimensional REAL: [Intervalos, Nodos, Features]
X_real = np.zeros((num_intervalos, num_nodos, 1))

for t_idx, intervalo in enumerate(intervalos_reales):
    df_bloque = df_demanda[df_demanda['Intervalo'] == intervalo]
    for _, row in df_bloque.iterrows():
        n_idx = int(row['nodo_idx'])
        X_real[t_idx, n_idx, 0] = row['Validaciones']

X_real_tensor = torch.tensor(X_real, dtype=torch.float)

# --- 5. ARQUITECTURA GAT (Soporta variables reales) ---
class GATTransmilenio(torch.nn.Module):
    def __init__(self, in_channels, hidden_channels, out_channels, heads=4):
        super(GATTransmilenio, self).__init__()
        self.gat1 = GATConv(in_channels, hidden_channels, heads=heads, edge_dim=2, dropout=0.1)
        self.gat2 = GATConv(hidden_channels * heads, out_channels, heads=1, edge_dim=2, dropout=0.1)

    def forward(self, x, edge_index, edge_attr):
        x = self.gat1(x, edge_index, edge_attr)
        x = F.elu(x)
        x = F.dropout(x, p=0.1, training=self.training)
        x = self.gat2(x, edge_index, edge_attr)
        return x

# --- 6. CONFIGURAR ENTRENAMIENTO ---
model = GATTransmilenio(in_channels=1, hidden_channels=32, out_channels=1, heads=4)
optimizer = torch.optim.Adam(model.parameters(), lr=0.005, weight_decay=1e-4)
criterion = torch.nn.MSELoss()

print(f"\n🚀 Iniciando entrenamiento con demanda REAL de Transmilenio (50 épocas)...")
epochs = 50

model.train()
for epoch in range(1, epochs + 1):
    loss_total = 0
    for t in range(num_intervalos - 1):
        optimizer.zero_grad()
        
        x_t = X_real_tensor[t]          # Demanda real en intervalo t
        y_real = X_real_tensor[t+1]      # Lo que realmente pasó en t+1
        
        y_pred = model(x_t, grafo_base.edge_index, grafo_base.edge_attr)
        
        loss = criterion(y_pred, y_real)
        loss.backward()
        optimizer.step()
        
        loss_total += loss.item()
        
    loss_promedio = loss_total / (num_intervalos - 1)
    
    if epoch % 10 == 0 or epoch == 1:
        # Calculamos la raíz del MSE (RMSE) para interpretarlo en "unidades de pasajeros"
        rmse = np.sqrt(loss_promedio)
        print(f"   Epoch {epoch:02d}/{epochs:02d} -> Loss Promedio (MSE): {loss_promedio:.2f} | RMSE aprox: {rmse:.2f} pasajeros")

# Guardar los pesos entrenados del modelo
PATH_MODELO = os.path.join(GRAPHS_DIR, "gat_transmilenio_pesos.pth")
torch.save(model.state_dict(), PATH_MODELO)
print(f"\n🎯 ¡Entrenamiento Real Completado con éxito!")
print(f"💾 Red neuronal guardada en: {PATH_MODELO}")