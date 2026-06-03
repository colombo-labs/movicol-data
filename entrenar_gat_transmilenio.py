import os
import torch
import torch.nn.functional as F
from torch_geometric.nn import GATConv

# 1. Configurar rutas relativas basadas en tu estructura
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else os.getcwd()
GRAPHS_DIR = os.path.join(BASE_DIR, "data", "graphs")
PATH_GRAFO = os.path.join(GRAPHS_DIR, "transmilenio_graph_data.pt")

print("⏳ Cargando la topología y base del grafo de Transmilenio...")
# Cargamos el objeto Data que generamos exitosamente en el paso anterior
grafo_base = torch.load(PATH_GRAFO, weights_only=False)

# --- CONFIGURACIÓN DE DATOS SIMULADOS / TEMPORALES ---
# Como el objeto base solo guardó 1 intervalo de prueba (X: [150, 1]), vamos a estructurar
# una matriz temporal real para simular los 96 intervalos detectados en tu dataset.
# En producción, aquí mapearías los 96 vectores reales consecutivamente.
num_nodos = grafo_base.num_nodes
num_intervalos = 96

print(f"📊 Generando tensores de entrenamiento para los {num_intervalos} intervalos temporales...")
# Simulación de secuencias temporales: X_temporal tendrá forma [96, 150, 1]
torch.manual_seed(42)
X_temporal = torch.randn(num_intervalos, num_nodos, 1) * 50 + 100 # Demanda base simulada
X_temporal = torch.clamp(X_temporal, min=0) # Evitar demandas negativas

# --- 2. DEFINICIÓN DE LA ARQUITECTURA GAT ---
class GATTransmilenio(torch.nn.Module):
    def __init__(self, in_channels, hidden_channels, out_channels, heads=4):
        super(GATTransmilenio, self).__init__()
        # Primera capa GAT: Recibe las validaciones y los atributos de la arista
        # edge_dim=2 porque pasamos (distancia_normalizada, tipo_via)
        self.gat1 = GATConv(in_channels, hidden_channels, heads=heads, edge_dim=2, dropout=0.1)
        
        # Segunda capa GAT (Salida): Conecta las cabezas anteriores y reduce a la predicción final
        # heads=1 para la salida para consolidar los canales en una sola predicción por nodo
        self.gat2 = GATConv(hidden_channels * heads, out_channels, heads=1, edge_dim=2, dropout=0.1)

    def forward(self, x, edge_index, edge_attr):
        # Primera propagación con atención espacial e infraestructura
        x = self.gat1(x, edge_index, edge_attr)
        x = F.elu(x) # Activación no-lineal ELU para redes de grafos
        x = F.dropout(x, p=0.1, training=self.training)
        
        # Capa de salida: Predicción de demanda continua (Regresión)
        x = self.gat2(x, edge_index, edge_attr)
        return x

# --- 3. INICIALIZACIÓN DEL MODELO ---
# in_channels=1 (Validaciones actuales), out_channels=1 (Validaciones del próximo intervalo)
model = GATTransmilenio(in_channels=1, hidden_channels=16, out_channels=1, heads=4)
optimizer = torch.optim.Adam(model.parameters(), lr=0.01, weight_decay=5e-4)
criterion = torch.nn.MSELoss() # Error Cuadrático Medio para predicción numérica

print(f"\n🧠 Arquitectura del modelo GAT cargada con éxito:")
print(model)

# --- 4. CICLO DE ENTRENAMIENTO ---
print("\n🚀 Iniciando entrenamiento espacio-temporal de la red neuronal...")
epochs = 20

model.train()
for epoch in range(1, epochs + 1):
    loss_total = 0
    # Iteramos a través del tiempo entrenando al modelo para pasar de t -> t+1
    for t in range(num_intervalos - 1):
        optimizer.zero_grad()
        
        # Entrada en el tiempo t
        x_t = X_temporal[t] 
        # Target real en el tiempo t+1 (lo que queremos predecir)
        y_real = X_temporal[t+1] 
        
        # Pasar datos por la GAT (usando las aristas y atributos físicos fijos)
        y_pred = model(x_t, grafo_base.edge_index, grafo_base.edge_attr)
        
        # Calcular el error de predicción en toda la red de Bogotá
        loss = criterion(y_pred, y_real)
        loss.backward()
        optimizer.step()
        
        loss_total += loss.item()
        
    loss_promedio = loss_total / (num_intervalos - 1)
    
    if epoch % 5 == 0 or epoch == 1:
        print(f"   Epoch {epoch:02d}/{epochs:02d} -> Loss Promedio (MSE): {loss_promedio:.4f}")

print("\n🎯 ¡Entrenamiento completado!")
print("💾 El modelo ha aprendido los pesos de atención basados en las troncales viales.")