import os
import re
import pandas as pd
import numpy as np
import torch
import torch.nn.functional as F
from torch_geometric.nn import GATConv

# 1. Rutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else os.getcwd()
GRAPHS_DIR = os.path.join(BASE_DIR, "data", "graphs")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")

PATH_GRAFO = os.path.join(GRAPHS_DIR, "transmilenio_graph_data.pt")
PATH_NODOS = os.path.join(PROCESSED_DIR, "nodos_infraestructura_gat.csv")
PATH_PESOS = os.path.join(GRAPHS_DIR, "gat_transmilenio_pesos.pth")

# 2. Reconstruir Grafo y Demanda Real (Igual al script de entrenamiento)
grafo_base = torch.load(PATH_GRAFO, weights_only=False)
df_nodos_infra = pd.read_csv(PATH_NODOS)
df_nodos_infra['num_est_str'] = df_nodos_infra['num_est'].astype(str).str.zfill(5)
nodos_unicos = df_nodos_infra['num_est_str'].unique()
nodo_to_idx = {num_est: idx for idx, num_est in enumerate(nodos_unicos)}
idx_to_name = {idx: row['nom_est'] for idx, row in df_nodos_infra.iterrows() if row['num_est_str'] in nodo_to_idx}

path_demanda = os.path.join(PROCESSED_DIR, "demanda_con_nodos.csv")
if not os.path.exists(path_demanda):
    path_demanda = os.path.join(PROCESSED_DIR, "demanda_troncal_2025_final.csv")
df_demanda = pd.read_csv(path_demanda)

def extraer_codigo_estacion(texto):
    match = re.search(r'\((\d+)\)', str(texto))
    return match.group(1).zfill(5) if match else None

df_demanda['num_est_str'] = df_demanda['Estación'].apply(extraer_codigo_estacion)
df_demanda['nodo_idx'] = df_demanda['num_est_str'].map(nodo_to_idx)
df_demanda = df_demanda.dropna(subset=['nodo_idx'])

def minutos_del_dia(texto_intervalo):
    try: h, m = map(int, str(texto_intervalo).split(':')); return h * 60 + m
    except: return 0

df_demanda['minutos'] = df_demanda['Intervalo'].apply(minutos_del_dia)
df_demanda = df_demanda.sort_values(by=['minutos']).reset_index(drop=True)
intervalos_reales = sorted(df_demanda['Intervalo'].unique(), key=minutos_del_dia)

X_real = np.zeros((len(intervalos_reales), len(nodo_to_idx), 1))
for t_idx, intervalo in enumerate(intervalos_reales):
    df_bloque = df_demanda[df_demanda['Intervalo'] == intervalo]
    for _, row in df_bloque.iterrows():
        X_real[t_idx, int(row['nodo_idx']), 0] = row['Validaciones']
X_real_tensor = torch.tensor(X_real, dtype=torch.float)

# 3. Definir e Inicializar Arquitectura GAT (debe coincidir con la entrenada)
class GATTransmilenio(torch.nn.Module):
    def __init__(self, in_channels, hidden_channels, out_channels, heads=4):
        super(GATTransmilenio, self).__init__()
        self.gat1 = GATConv(in_channels, hidden_channels, heads=heads, edge_dim=2, dropout=0.1)
        self.gat2 = GATConv(hidden_channels * heads, out_channels, heads=1, edge_dim=2, dropout=0.1)

    def forward(self, x, edge_index, edge_attr):
        # Modificación para retornar coeficientes de atención opcionalmente en evaluación
        x, alpha = self.gat1(x, edge_index, edge_attr, return_attention_weights=True)
        x = F.elu(x)
        x = self.gat2(x, edge_index, edge_attr)
        return x, alpha

model = GATTransmilenio(in_channels=1, hidden_channels=32, out_channels=1, heads=4)
model.load_state_dict(torch.load(PATH_PESOS, weights_only=False))
model.eval()

# 4. Evaluación de Métricas Globales
print("🧐 Evaluando modelo entrenado contra los datos de validaciones reales...")
predicciones = []
reales = []

with torch.no_grad():
    for t in range(len(intervalos_reales) - 1):
        x_t = X_real_tensor[t]
        y_t_real = X_real_tensor[t+1]
        
        y_t_pred, _ = model(x_t, grafo_base.edge_index, grafo_base.edge_attr)
        
        predicciones.append(y_t_pred.numpy().flatten())
        reales.append(y_t_real.numpy().flatten())

predicciones = np.array(predicciones)
reales = np.array(reales)

# Calcular métricas estadísticas clave
mae = np.mean(np.abs(predicciones - reales))
rmse = np.sqrt(np.mean((predicciones - reales) ** 2))
# Coeficiente de determinación R2 (evitar división por cero)
ss_res = np.sum((reales - predicciones) ** 2)
ss_tot = np.sum((reales - np.mean(reales)) ** 2)
r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

print("\n📊 REPORTE DE MÉTRICAS ESTADÍSTICAS (GAT BASE):")
print("-" * 50)
print(f"-> Error Medio Absoluto (MAE): {mae:.2f} pasajeros")
print(f"-> Raíz del Error Cuadrático (RMSE): {rmse:.2f} pasajeros")
print(f"-> Coeficiente de Determinación (R²): {r2:.4f}")
print("-" * 50)

# 5. Análisis del comportamiento por Estación
print("\n🔍 Analizando las estaciones con mayores retos de predicción...")
errores_por_estacion = np.mean(np.abs(predicciones - reales), axis=0)

df_analisis = pd.DataFrame({
    'Indice_Nodo': range(len(errores_por_estacion)),
    'Nombre_Estacion': [idx_to_name.get(i, f"Estacion_{i}") for i in range(len(errores_por_estacion))],
    'MAE_Pasajeros': errores_por_estacion
}).sort_values(by='MAE_Pasajeros', ascending=False)

print("\n🔝 Top 5 Estaciones con mayor error de predicción (Donde hay flujos caóticos):")
print(df_analisis.head(5).to_string(index=False))

print("\n📉 Top 5 Estaciones con predicciones más exactas (Flujos estables):")
print(df_analisis.tail(5).to_string(index=False))
