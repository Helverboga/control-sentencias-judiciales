import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuración de página optimizada para móviles
st.set_page_config(page_title="Control Judicial Cloud", layout="wide")

# Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def inicializar_hoja_calculo():
    """Crea la estructura de tablas si la hoja está vacía"""
    try:
        # Intentamos leer la pestaña de procesos
        conn.read(worksheet="procesos")
    except:
        st.warning("Configurando estructura inicial en Google Sheets...")
        # Estructura de Procesos
        df_procesos = pd.DataFrame(columns=[
            "id", "numero_proceso", "fecha_inicio", "estado", "fase_actual", "progreso_total"
        ])
        # Estructura de Seguimiento (Cronómetros y Pasos)
        df_seguimiento = pd.DataFrame(columns=[
            "proceso_id", "fase", "paso_n", "completado", "tiempo_segundos"
        ])
        
        # Actualizamos la hoja (Requiere permisos de escritura)
        conn.update(worksheet="procesos", data=df_procesos)
        conn.update(worksheet="seguimiento", data=df_seguimiento)
        st.success("¡Estructura creada con éxito!")

# --- LÓGICA DE INTERFAZ RESPONSIVE ---
st.markdown('<h1 style="text-align:center;">⚖️ Control de Sentencias Cloud</h1>', unsafe_allow_html=True)

# Usamos contenedores para que en móvil se apilen mejor
metric_container = st.container()
with metric_container:
    # En PC se verán 4 columnas, en móvil Streamlit las ajusta automáticamente
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    
    # Simulación de carga de datos desde Sheets
    # df = conn.read(worksheet="procesos")
    
    col1.metric("📋 Procesos", "5")
    col2.metric("📈 Progreso", "45%")
    col3.metric("🚨 Alertas", "0", delta_color="inverse")
    col4.metric("⏱️ Activos", "2")

# --- RESTO DE TU LÓGICA DE FASES (Adaptada a API de Google) ---
# (Aquí iría el resto de las funciones de tu script original)