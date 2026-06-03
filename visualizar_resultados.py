import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# 1. Configurar rutas y cargar los resultados exportados
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else os.getcwd()
GRAPHS_DIR = os.path.join(BASE_DIR, "data", "graphs")
PATH_CSV_RESULTADOS = os.path.join(GRAPHS_DIR, "predicciones_vs_reales.csv")

if not os.path.exists(PATH_CSV_RESULTADOS):
    raise FileNotFoundError(f"No se encontró el archivo de resultados en: {PATH_CSV_RESULTADOS}. Ejecuta primero 'optimizar_st_gat.py'")

df = pd.read_csv(PATH_CSV_RESULTADOS)

# Configuración estética general de los gráficos
sns.set_theme(style="whitegrid")
plt.rcParams.update({'font.size': 11, 'axes.labelsize': 12, 'axes.titlesize': 14})

# =========================================================================
# GRÁFICO 1: COMPARATIVA TEMPORAL EN ESTACIONES CLAVE
# =========================================================================
estacion_caotica = "Calle 127"
estacion_estable = "AV. Jiménez - CL 13"

# Si por alguna razón el string exacto cambió en tu dataset, tomamos las que existan
estaciones_disponibles = df['Nombre_Estacion'].unique()
if estacion_caotica not in estaciones_disponibles:
    estacion_caotica = estaciones_disponibles[0]
if estacion_estable not in estaciones_disponibles:
    estacion_estable = estaciones_disponibles[-1]

fig, axes = plt.subplots(2, 1, figsize=(12, 10), sharex=False)

for idx, est in enumerate([estacion_caotica, estacion_estable]):
    df_est = df[df['Nombre_Estacion'] == est].copy()
    
    # Para que el eje X no se sature de texto, seleccionamos una muestra de etiquetas
    ticks_to_use = np.arange(0, len(df_est), max(1, len(df_est) // 12))
    labels_to_use = df_est['Intervalo'].values[ticks_to_use]
    
    axes[idx].plot(df_est['Intervalo'], df_est['Demanda_Real'], label='Demanda Real (Validaciones)', color='#2ca02c', linewidth=2.5, linestyle='-')
    axes[idx].plot(df_est['Intervalo'], df_est['Demanda_Predicha'], label='Predicción ST-GAT', color='#d62728', linewidth=2, linestyle='--')
    
    axes[idx].set_title(f"Comportamiento Espacio-Temporal: Estación {est}", weight='bold')
    axes[idx].set_ylabel("Cantidad de Pasajeros")
    axes[idx].set_xticks(ticks_to_use)
    axes[idx].set_xticklabels(labels_to_use, rotation=45)
    axes[idx].legend(loc='upper right')

plt.tight_layout()
path_save_temporal = os.path.join(GRAPHS_DIR, "resultado_temporal_transmilenio.png")
plt.savefig(path_save_temporal, dpi=300)
print(f"📊 Gráfico temporal guardado con éxito en: {path_save_temporal}")
plt.close()

# =========================================================================
# GRÁFICO 2: DISPERSIÓN GLOBAL (PREDICCIÓN VS REALIDAD)
# =========================================================================
plt.figsize = (8, 8)
plt.figure(figsize=(8, 7))

# Tomamos una muestra aleatoria si el dataset es gigante para no saturar el scatter, o lo pintamos completo
sample_size = min(len(df), 10000)
df_sample = df.sample(n=sample_size, random_state=42)

sns.scatterplot(data=df_sample, x='Demanda_Real', y='Demanda_Predicha', alpha=0.4, color='#1f77b4', edgecolor=None)

# Dibujar la línea de identidad perfecta (Donde Y = X)
max_val = int(max(df['Demanda_Real'].max(), df['Demanda_Predicha'].max()))
plt.plot([0, max_val], [0, max_val], color='black', linestyle=':', linewidth=2, label='Predicción Perfecta (Ideal)')

plt.title("Ajuste Global del Modelo ST-GAT en Transmilenio\n(Muestra de 150 estaciones e intervalos)", weight='bold')
plt.xlabel("Demanda Real Observada (Pasajeros)")
plt.ylabel("Demanda Predicha por la Red Neuronal (Pasajeros)")
plt.xlim(0, max_val)
plt.ylim(0, max_val)
plt.legend()
plt.tight_layout()

path_save_scatter = os.path.join(GRAPHS_DIR, "ajuste_global_scatter.png")
plt.savefig(path_save_scatter, dpi=300)
print(f"📊 Gráfico de dispersión global guardado con éxito en: {path_save_scatter}\n")
plt.close()

print("👑 ¡Felicidades! Los gráficos de alta resolución han sido generados. Puedes abrirlos en tu carpeta de destino.")