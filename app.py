import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(
    page_title="Control de Sentencias Cloud",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5em; 
        font-weight: bold; 
        text-align: center; 
        color: #1f4e79;
        border-bottom: 3px solid #d4a574;
        margin-bottom: 20px;
    }
    .metric-card {
        background: linear-gradient(135deg, #1f4e79, #2d5aa0);
        color: white;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        margin: 5px;
    }
</style>
""", unsafe_allow_html=True)

# --- DEFINICIÓN DE FASES ---
FASES_PROCESO = {
    "I. Fase Propedéutica": {
        "descripcion": "Preparación inicial",
        "pasos": [
            "01) Copiar y pegar Kit", "02) Cambiar nombre carpeta", "03) Crear carpeta mes",
            "04) Descargar expediente", "05) Aprovisionar herramientas", "06) Editar e imprimir",
            "07) Índice del expediente", "08) Foto del proceso", "09) Estructurar piezas",
            "10) Reporte de pruebas", "11) Fáctum", "12) Auto de pruebas", "13) Notificar"
        ]
    },
    "II. Fase Lectura": {
        "descripcion": "Lectura y análisis",
        "pasos": ["01) Lectura completa", "02) Identificar claves", "03) Toma de notas"]
    },
    "III. Fase Sentencia": {
        "descripcion": "Elaboración del fallo",
        "pasos": [
            "01) Elegir modelo", "02) Sintetizar escritos", "03) Agregar síntesis",
            "04) Investigación jurídica", "05) Alojar investigaciones", "06) Jurisprudencia",
            "07) Valorar pruebas", "08) 6 etapas sentencia", "09) Enriquecer proyecto",
            "10) Guardar fallo final"
        ]
    },
    "IV. Fase Audiencia": {
        "descripcion": "Preparación oralidad",
        "pasos": ["01) Operar algoritmo", "02) Presupuestos", "03) Crear capa", 
                  "04) Asistencia", "05) Roteiro"]
    }
}

# --- CONEXIÓN GOOGLE SHEETS ---
@st.cache_resource
def get_connection():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

def get_data():
    client = get_connection()
    try:
        sh = client.open("DB_Control_Sentencias")
    except:
        st.error("🚨 No se encuentra la hoja 'DB_Control_Sentencias' en Drive.")
        st.stop()
        
    # Verificar hojas
    try:
        w_proc = sh.worksheet("Procesos")
    except:
        w_proc = sh.add_worksheet("Procesos", 100, 10)
        w_proc.append_row(["id", "radicado", "fecha", "estado", "fase_actual", "progreso"])
        
    try:
        w_detalles = sh.worksheet("Detalles")
    except:
        w_detalles = sh.add_worksheet("Detalles", 1000, 10)
        # Headers: id_proc, fase, paso_idx, completado, tiempo_acum, start_time, timer_active
        w_detalles.append_row(["id_proceso", "fase", "paso_idx", "val", "tiempo", "inicio", "activo"])
        
    return w_proc, w_detalles

# --- FUNCIONES DE INTERFAZ ---
def formatear_tiempo(segundos):
    segundos = int(segundos)
    if segundos < 60: return f"{segundos}s"
    minutes = segundos // 60
    if minutes < 60: return f"{minutes}m {segundos % 60}s"
    return f"{minutes // 60}h {minutes % 60}m"

def nuevo_proceso(w_proc):
    st.markdown('<div class="main-header">➕ Nuevo Expediente</div>', unsafe_allow_html=True)
    with st.form("frm_new"):
        radicado = st.text_input("Número de Radicado", placeholder="Ej: 2026-001")
        if st.form_submit_button("Crear"):
            df = pd.DataFrame(w_proc.get_all_records())
            if not df.empty and str(radicado) in df['radicado'].astype(str).values:
                st.error("¡Ya existe!")
            else:
                new_id = int(time.time())
                fecha = datetime.now().strftime("%Y-%m-%d")
                # Fila nueva: id, radicado, fecha, estado, fase, progreso
                w_proc.append_row([new_id, radicado, fecha, "Activo", "I. Fase Propedéutica", 0])
                st.success("¡Creado!")
                time.sleep(1)
                st.rerun()

def gestionar(w_proc, w_detalles, df_proc):
    st.markdown('<div class="main-header">📂 Gestión</div>', unsafe_allow_html=True)
    
    opciones = df_proc['radicado'].tolist()
    seleccion = st.selectbox("Expediente:", opciones)
    
    # Datos del seleccionado
    row = df_proc[df_proc['radicado'] == seleccion].iloc[0]
    proc_id = int(row['id'])
    
    st.info(f"Fase Actual: {row['fase_actual']} | Progreso: {row['progreso']}%")
    
    # Cargar detalles
    df_det = pd.DataFrame(w_detalles.get_all_records())
    if not df_det.empty:
        df_det = df_det[df_det['id_proceso'] == proc_id]
    
    total_pasos = 0
    total_ok = 0
    
    for fase, info in FASES_PROCESO.