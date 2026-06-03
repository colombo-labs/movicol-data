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
idx_to_name = {idx: row['nom_est'] for idx, row in df_nodos_infra.iterrows() if row['num_est_str'] in nodo_to_idx}
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

# Crear Secuencias Temporales (Ventana de 4 intervalos = 1 hora de historia)
window_size = 4
X_seq, Y_seq = [], []
for i in range(len(X_real) - window_size):
    X_seq.append(X_real[i:i+window_size])
    Y_seq.append(X_real[i+window_size])

X_seq = torch.tensor(np.array(X_seq), dtype=torch.float)
Y_seq = torch.tensor(np.array(Y_seq), dtype=torch.float)

# 4. Arquitectura ST-GAT
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

# 5. Configurar Entrenamiento de Alto Rendimiento
model = STGATTransmilenio(in_channels=1, hidden_channels=24, out_channels=1, window_size=window_size, heads=4)
optimizer = torch.optim.Adam(model.parameters(), lr=0.004, weight_decay=1e-4)
# Reducirá el learning rate a la mitad cada 40 épocas para ayudar a afinar la convergencia
scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=40, gamma=0.5)
criterion = torch.nn.MSELoss()

epochs = 150
print(f"\n🚀 Iniciando Entrenamiento Extendido a {epochs} Épocas...")
model.train()

for epoch in range(1, epochs + 1):
    loss_total = 0
    for s in range(X_seq.shape[0]):
        optimizer.zero_grad()
        y_pred = model(X_seq[s], grafo_base.edge_index, grafo_base.edge_attr)
        loss = criterion(y_pred, Y_seq[s])
        loss.backward()
        optimizer.step()
        loss_total += loss.item()
        
    scheduler.step()
    loss_promedio = loss_total / X_seq.shape[0]
    
    # Imprimir reporte cada 15 épocas
    if epoch % 15 == 0 or epoch == 1:
        rmse = np.sqrt(loss_promedio)
        lr_actual = optimizer.param_groups[0]['lr']
        print(f"   Epoch {epoch:03d}/{epochs} -> Loss (MSE): {loss_promedio:.2f} | RMSE: {rmse:.2f} pasajeros | LR: {lr_actual:.5f}")

# Guardar los mejores pesos optimizados
PATH_ST_OPTIMO = os.path.join(GRAPHS_DIR, "st_gat_transmilenio_optimizado.pth")
torch.save(model.state_dict(), PATH_ST_OPTIMO)

# 6. Evaluación Automática Final e Insumo para Gráficos
print("\n🧐 Calculando métricas de rendimiento final...")
model.eval()
historial_predicciones, historial_reales = [], []

with torch.no_grad():
    for s in range(X_seq.shape[0]):
        y_pred_sample = model(X_seq[s], grafo_base.edge_index, grafo_base.edge_attr)
        historial_predicciones.append(y_pred_sample.numpy().flatten())
        historial_reales.append(Y_seq[s].numpy().flatten())

historial_predicciones = np.array(historial_predicciones)
historial_reales = np.array(historial_reales)

# Métricas globales finales
mae_f = np.mean(np.abs(historial_predicciones - historial_reales))
rmse_f = np.sqrt(np.mean((historial_predicciones - historial_reales) ** 2))
ss_res = np.sum((historial_reales - historial_predicciones) ** 2)
ss_tot = np.sum((historial_reales - np.mean(historial_reales)) ** 2)
r2_f = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

print("\n🏆 REPORTE FINAL CON 150 ÉPOCAS:")
print("=" * 65)
print(f"-> Error Medio Absoluto (MAE): {mae_f:.2f} pasajeros")
print(f"-> Raíz del Error Cuadrático (RMSE): {rmse_f:.2f} pasajeros")
print(f"-> Coeficiente de Determinación Final (R²): {r2_f:.4f}")
print("=" * 65)

# 7. Exportar los datos listos para el script de visualización
# Mapeamos los intervalos evaluados (quitando los primeros 4 que corresponden al window_size)
intervalos_evaluados = intervalos_reales[window_size:]

registros_csv = []
for t_idx, intervalo in enumerate(intervalos_evaluados):
    for n_idx in range(num_nodos):
        registros_csv.append({
            'Intervalo': intervalo,
            'Nombre_Estacion': idx_to_name.get(n_idx, f"Estacion_{n_idx}"),
            'Demanda_Real': historial_reales[t_idx, n_idx],
            'Demanda_Predicha': historial_predicciones[t_idx, n_idx]
        })

df_graficos = pd.DataFrame(registros_csv)
PATH_CSV_RESULTADOS = os.path.join(GRAPHS_DIR, "predicciones_vs_reales.csv")
df_graficos.to_csv(PATH_CSV_RESULTADOS, index=False)
print(f"💾 Datos para graficar exportados exitosamente en: {PATH_CSV_RESULTADOS}\n")