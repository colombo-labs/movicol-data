import os
import re
import pandas as pd
import numpy as np
import torch
import torch.nn.functional as F
from torch_geometric.nn import GATConv
import matplotlib.pyplot as plt
import seaborn as sns

# 1. Configurar rutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else os.getcwd()
GRAPHS_DIR = os.path.join(BASE_DIR, "data", "graphs")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")

PATH_GRAFO = os.path.join(GRAPHS_DIR, "transmilenio_graph_data.pt")
PATH_NODOS = os.path.join(PROCESSED_DIR, "nodos_infraestructura_gat.csv")

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

X_real = np.zeros((len(intervalos_reales), num_nodos, 1))
for t_idx, intervalo in enumerate(intervalos_reales):
    df_bloque = df_demanda[df_demanda['Intervalo'] == intervalo]
    for _, row in df_bloque.iterrows():
        X_real[t_idx, int(row['nodo_idx']), 0] = row['Validaciones']

# =========================================================================
# NUEVA ESTRATEGIA: ESTANDARIZACIÓN Z-SCORE (Previene la muerte del gradiente)
# =========================================================================
mean_demanda = X_real.mean()
std_demanda = X_real.std() if X_real.std() > 0 else 1
X_real_scaled = (X_real - mean_demanda) / std_demanda

# Crear Secuencias Temporales
window_size = 4
X_seq, Y_seq = [], []
for i in range(len(X_real_scaled) - window_size):
    X_seq.append(X_real_scaled[i:i+window_size])
    Y_seq.append(X_real_scaled[i+window_size])

X_seq = torch.tensor(np.array(X_seq), dtype=torch.float)
Y_seq = torch.tensor(np.array(Y_seq), dtype=torch.float)

# 4. Arquitectura ST-GAT Estabilizada
class STGATEstabilizada(torch.nn.Module):
    def __init__(self, in_channels, hidden_channels, out_channels, window_size, heads=4):
        super(STGATEstabilizada, self).__init__()
        # Quitamos dropout drástico para evitar pérdida de gradiente en datos estandarizados
        self.gat = GATConv(in_channels, hidden_channels, heads=heads, edge_dim=2, dropout=0.0)
        self.gru = torch.nn.GRU(hidden_channels * heads, hidden_channels, batch_first=True)
        self.fc = torch.nn.Linear(hidden_channels, out_channels)

    def forward(self, x_seq, edge_index, edge_attr):
        w_size, n_nodes, f_size = x_seq.shape
        gat_outputs = []
        for t in range(w_size):
            x_t = x_seq[t]
            # Usamos LeakyReLU para garantizar que los valores negativos estandarizados sigan vivos
            h_spatial = F.leaky_relu(self.gat(x_t, edge_index, edge_attr), negative_slope=0.1)
            gat_outputs.append(h_spatial.unsqueeze(0))
            
        gat_outputs = torch.cat(gat_outputs, dim=0).transpose(0, 1)
        gru_out, _ = self.gru(gat_outputs)
        last_temporal_state = gru_out[:, -1, :]
        
        out = self.fc(last_temporal_state)
        return out

# 5. Configurar Entrenamiento
model = STGATEstabilizada(in_channels=1, hidden_channels=16, out_channels=1, window_size=window_size, heads=4)
optimizer = torch.optim.Adam(model.parameters(), lr=0.002, weight_decay=1e-4)
criterion = torch.nn.MSELoss()

epochs = 100
print(f"\n🚀 Entrenando Red ST-GAT con Estandarización Z-Score (100 Épocas)...")
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
        
    if epoch % 25 == 0 or epoch == 1:
        loss_promedio = loss_total / X_seq.shape[0]
        # RMSE real des-estandarizado
        rmse_real = np.sqrt(loss_promedio) * std_demanda
        print(f"   Epoch {epoch:03d}/{epochs} -> Loss Escalado: {loss_promedio:.5f} | RMSE Real: {rmse_real:.2f} pasajeros")

# 6. Evaluación e Inversión de la Estandarización
model.eval()
historial_predicciones, historial_reales = [], []

with torch.no_grad():
    for s in range(X_seq.shape[0]):
        y_pred_scaled = model(X_seq[s], grafo_base.edge_index, grafo_base.edge_attr)
        # Operación inversa de Z-Score: (X_scaled * std) + mean
        y_pred_unscaled = (y_pred_scaled.numpy().flatten() * std_demanda) + mean_demanda
        y_real_unscaled = (Y_seq[s].numpy().flatten() * std_demanda) + mean_demanda
        
        historial_predicciones.append(y_pred_unscaled)
        historial_reales.append(y_real_unscaled)

historial_predicciones = np.clip(np.array(historial_predicciones), a_min=0, a_max=None)
historial_reales = np.array(historial_reales)

# Calcular R² real sobre la escala humana de pasajeros
ss_res = np.sum((historial_reales - historial_predicciones) ** 2)
ss_tot = np.sum((historial_reales - np.mean(historial_reales)) ** 2)
r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
print(f"\n🎯 ¡Entrenamiento completado de forma estable! Nuevo R² Real: {r2:.4f}")

# 7. REGENERAR VISUALIZACIONES DINÁMICAS
print("📊 Actualizando gráficos de diagnóstico viales...")
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
df_res = pd.DataFrame(registros_csv)

# Graficar Línea Temporal de la Estación Crítica (Calle 127)
plt.figure(figsize=(12, 5))
sns.set_theme(style="whitegrid")
est_critica = "Calle 127" if "Calle 127" in df_res['Nombre_Estacion'].unique() else df_res['Nombre_Estacion'].unique()[0]
df_plot = df_res[df_res['Nombre_Estacion'] == est_critica]

ticks_to_use = np.arange(0, len(df_plot), len(df_plot) // 12)
plt.plot(df_plot['Intervalo'], df_plot['Demanda_Real'], label='Demanda Real', color='#2ca02c', linewidth=2.5)
plt.plot(df_plot['Intervalo'], df_plot['Demanda_Predicha'], label='Predicción ST-GAT Dinámica', color='#d62728', linewidth=2, linestyle='--')
plt.title(f"Ajuste Espacio-Temporal Exitoso - Estación {est_critica}", weight='bold')
plt.xticks(ticks_to_use, df_plot['Intervalo'].values[ticks_to_use], rotation=45)
plt.ylabel("Pasajeros")
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(GRAPHS_DIR, "resultado_temporal_transmilenio.png"), dpi=300)
plt.close()

# Graficar Scatter Plot Global
plt.figure(figsize=(7, 6))
sns.scatterplot(data=df_res.sample(min(len(df_res), 8000)), x='Demanda_Real', y='Demanda_Predicha', alpha=0.4, color='#1f77b4', edgecolor=None)
max_v = int(max(df_res['Demanda_Real'].max(), df_res['Demanda_Predicha'].max()))
plt.plot([0, max_v], [0, max_v], color='black', linestyle=':', label='Ideal')
plt.xlim(0, max_v); plt.ylim(0, max_v)
plt.title("Ajuste Dinámico Global Estabilizado", weight='bold')
plt.xlabel("Demanda Real Observada"); plt.ylabel("Demanda Predicha")
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(GRAPHS_DIR, "ajuste_global_scatter.png"), dpi=300)
plt.close()

print("👑 ¡Gráficos actualizados con éxito! Revisa de nuevo la carpeta 'graphs'.")