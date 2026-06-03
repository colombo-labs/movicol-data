import pandas as pd
import glob
import os

# 1. Configurar rutas basadas en tu terminal limpia de la raíz
RAIZ_PROYECTO = os.getcwd()
CARPETA_TRONCAL = os.path.join(RAIZ_PROYECTO, "data", "raw", "demanda", "transmilenio_validaciones", "troncal")
ARCHIVO_SALIDA = os.path.join(RAIZ_PROYECTO, "data", "processed", "demanda_troncal_2025_final.csv")

print("🚀 Iniciando Limpieza Quirúrgica de Transmilenio Troncal...")

if not os.path.exists(CARPETA_TRONCAL):
    print(f"❌ Error: No existe la carpeta TRONCAL en:\n👉 {CARPETA_TRONCAL}")
else:
    archivos = glob.glob(os.path.join(CARPETA_TRONCAL, "*.csv"))
    if not archivos:
        print("⚠️ No se encontraron archivos .csv en la carpeta troncal.")
    else:
        print(f"📦 Se detectaron {len(archivos)} archivos mensuales para procesar.")
        lista_dfs_limpios = []
        
        for archivo in archivos:
            nombre_mes = os.path.basename(archivo)
            print(f"-> Procesando de forma avanzada: {nombre_mes}")
            
            try:
                # TRUCO 1: Skiprows=5 salta el título del gobierno y cae directo en 'Fase;Línea;Estación...'
                # TRUCO 2: sep=';' y encoding='latin1' para digerir los datos colombianos sin romperse
                df = pd.read_csv(archivo, sep=';', skiprows=5, encoding='latin1', on_bad_lines='skip')
                
                # Limpiar espacios invisibles en los nombres de las columnas
                df.columns = df.columns.str.strip()
                
                # Corregir nombres deformados por la codificación si llegaran a ocurrir
                df = df.rename(columns={
                    'Lnea': 'Línea', 'Línea': 'Línea',
                    'Estacin': 'Estación', 'Estación': 'Estación'
                })
                
                # Filtrar solo las columnas base que necesitamos del inicio
                columnas_base = ['Línea', 'Estación', 'Intervalo']
                
                # Busquemos cuáles columnas corresponden a los días del mes (las que tienen formato de fecha DD/MM/AAAA)
                columnas_dias = [col for col in df.columns if '/' in col]
                
                if not columnas_dias:
                    print(f"⚠️ Alerta: No se detectaron columnas de días en {nombre_mes}")
                    continue
                    
                # Seleccionamos la estructura completa
                df_filtrado = df[columnas_base + columnas_dias].dropna(subset=columnas_base).copy()
                
                # TRUCO 3 (Avanzado): Convertimos la tabla ancha de días en una tabla larga hacia abajo (Melt)
                # Esto transforma 31 columnas de días en una sola columna 'Fecha' y una columna 'Validaciones'
                df_largo = df_filtrado.melt(
                    id_vars=columnas_base, 
                    value_vars=columnas_dias, 
                    var_name='Fecha', 
                    value_name='Validaciones'
                )
                
                # Limpiamos los números: convertimos las validaciones a enteros (rellenando vacíos con 0)
                df_largo['Validaciones'] = pd.to_numeric(df_largo['Validaciones'], errors='coerce').fillna(0).astype(int)
                
                # Eliminamos registros donde nadie se subió al bus para no llenar de basura el grafo
                df_largo = df_largo[df_largo['Validaciones'] > 0]
                
                lista_dfs_limpios.append(df_largo)
                
            except Exception as e:
                print(f"❌ Error crítico procesando el archivo {nombre_mes}: {str(e)}")
        
        # 2. Consolidar todos los meses limpios en un solo súper archivo
        if lista_dfs_limpios:
            print("\n🔄 Uniendo los meses procesados...")
            df_final = pd.concat(lista_dfs_limpios, ignore_index=True)
            
            # 3. Feature Engineering: Extraer la hora numérica del intervalo (ej: "9:30" -> 9)
            print("🧹 Extrayendo horas numéricas para el modelo GAT...")
            df_final['Hora_Num'] = df_final['Intervalo'].str.split(':').str[0]
            df_final['Hora_Num'] = pd.to_numeric(df_final['Hora_Num'], errors='coerce').fillna(0).astype(int)
            
            # Guardar el resultado en processed/
            os.makedirs(os.path.dirname(ARCHIVO_SALIDA), exist_ok=True)
            df_final.to_csv(ARCHIVO_SALIDA, index=False)
            
            print("\n==================================================")
            print("✅ ¡PROCESO CONCLUIDO CON ÉXITO CIENTÍFICO!")
            print(f"💾 Archivo consolidado guardado en: {ARCHIVO_SALIDA}")
            print(f"📊 Registros totales listos para la IA: {df_final.shape[0]}")
            print("==================================================")
            print("\nMuestra de tu base de datos final unificada:")
            print(df_final.head())
        else:
            print("❌ No se generaron datos válidos. Revisa el formato de tus archivos.")