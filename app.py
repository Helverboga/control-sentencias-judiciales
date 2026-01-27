import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURACIÓN DE PÁGINA Y ESTILOS ---
st.set_page_config(
    page_title="Control de Sentencias Cloud",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS (Los mismos que te gustaban)
st.markdown("""
<style>
    .main-header {
        font-size: 2.5em;
        font-weight: bold;
        text-align: center;
        color: #1f4e79;
        margin-bottom: 30px;
        border-bottom: 3px solid #d4a574;
        padding-bottom: 10px;
    }
    .phase-card {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #1f4e79;
        margin: 10px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .metric-card {
        background: linear-gradient(135deg, #1f4e79, #2d5aa0);
        color: white;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- DEFINICIÓN DE FASES (Tu lógica original) ---
FASES_PROCESO = {
    "I. Fase Propedéutica": {
        "tiempo_estimado": "Variable",
        "descripcion": "Preparación inicial y auto de pruebas",
        "pasos": [
            "01) Copiar y pegar 0.Kit", "02) Cambiar nombre a 0. Kit", "03) Crear carpeta mes",
            "04) Descargar expediente digital", "05) Aprovisionar herramientas", "06) Editar e imprimir",
            "07) Índice del expediente", "08) Foto del proceso", "09) Estructurar piezas procesales",
            "10) Reporte de pruebas", "11) Hago el fáctum", "12) Elaboro auto de pruebas",
            "13) Comparo, corrijo y notifico"
        ]
    },
    "II. Fase Lectura del Expediente": {
        "tiempo_estimado": "0.5 días",
        "descripcion": "Lectura comprensiva",
        "pasos": ["01) Lectura completa", "02) Identificación puntos clave", "03) Toma de notas"]
    },
    "III. Fase Elaboración de la Sentencia": {
        "tiempo_estimado": "5 días hábiles",
        "descripcion": "Redacción del fallo",
        "pasos": [
            "01) Elegir modelo y rotular", "02) Sintetizar escritos", "03) Agregar síntesis al borrador",
            "04) Investigación jurídica", "05) Alojar investigaciones", "06) Investigación jurisprudencial",
            "07) Valorar pruebas", "08) Elaborar 6 etapas sentencia", "09) Enriquecer proyecto",
            "10) Guardar proyecto final"
        ]
    },
    "IV. Fase Preparación Audiencia": {
        "tiempo_estimado": "2 días",
        "descripcion": "Preparación para la oralidad",
        "pasos": ["01) Operar algoritmo", "02) Presupuestos procesales", "03) Crear capa", 
                  "04) Control asistencia", "05) Roteiro"]
    }
}

# --- CONEXIÓN CON GOOGLE SHEETS ---
@st.cache_resource
def get_connection():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

def get_data():
    client = get_connection()
    try:
        sh = client.open("DB_Control_Sentencias")
    except:
        st.error("🚨 No encuentro la hoja 'DB_Control_Sentencias'.")
        st.stop()
        
    # Obtener o crear hojas
    try:
        w_proc = sh.worksheet("Procesos")
    except:
        w_proc = sh.add_worksheet("Procesos", 100, 10)
        w_proc.append_row(["id", "radicado", "fecha", "estado", "fase_actual", "progreso"])
        
    try:
        w_detalles = sh.worksheet("Detalles")
    except:
        w_detalles = sh.add_worksheet("Detalles", 1000, 10)
        # Estructura: id_proceso, fase, paso_idx, completado(0/1), tiempo_acumulado, timer_start, timer_active(0/1)
        w_detalles.append_row(["id_proceso", "fase", "paso_idx", "completado", "tiempo_acumulado", "timer_start", "timer_active"])
        
    return w_proc, w_detalles

# --- FUNCIONES AUXILIARES ---
def formatear_tiempo(segundos):
    if segundos < 60: return f"{int(segundos)}s"
    elif segundos < 3600: return f"{int(segundos//60)}m {int(segundos%60)}s"
    else: return f"{int(segundos//3600)}h {int((segundos%3600)//60)}m"

# --- INTERFAZ DE USUARIO ---

def mostrar_dashboard(df_proc):
    st.markdown('<div class="main-header">📊 Dashboard - Resumen General</div>', unsafe_allow_html=True)
    
    if df_proc.empty:
        st.info("👋 No hay procesos activos. Inicia uno nuevo en el menú lateral.")
        return

    # Métricas
    total = len(df_proc)
    promedio = df_proc['progreso'].mean()
    fase_comun = df_proc['fase_actual'].mode()[0] if not df_proc.empty else "N/A"

    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="metric-card"><h3>📋 Procesos</h3><h2>{total}</h2></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="metric-card"><h3>📈 Progreso Promedio</h3><h2>{promedio:.1f}%</h2></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="metric-card"><h3>🎯 Fase Más Común</h3><h4>{fase_comun}</h4></div>', unsafe_allow_html=True)

    st.markdown("### 📊 Progreso por Proceso")
    fig = px.bar(df_proc, x='radicado', y='progreso', color='fase_actual', title="Estado Actual")
    st.plotly_chart(fig, use_container_width=True)

def nuevo_proceso(w_proc):
    st.markdown('<div class="main-header">➕ Nuevo Expediente</div>', unsafe_allow_html=True)
    
    with st.form("frm_new"):
        radicado = st.text_input("Número de Radicado / Proceso", placeholder="Ej: 2026-001-CIVIL")
        
        # Mostrar fases informativas
        st.info("El proceso se creará con las 4 Fases estándar configuradas.")
        
        if st.form_submit_button("🚀 Crear Proceso"):
            # Validar duplicados
            datos = w_proc.get_all_records()
            df = pd.DataFrame(datos)
            if not df.empty and str(radicado) in df['radicado'].astype(str).values:
                st.error("¡Este radicado ya existe!")
            else:
                new_id = int(time.time())
                fecha = datetime.now().strftime("%Y-%m-%d")
                w_proc.append_row([new_id, radicado, fecha, "Activo", "I. Fase Propedéutica", 0])
                st.success(f"✅ Proceso {radicado} creado exitosamente.")
                time.sleep(1)
                st.rerun()

def gestionar_proceso(w_proc, w_detalles, df_proc):
    st.markdown('<div class="main-header">📂 Gestión de Expedientes</div>', unsafe_allow_html=True)
    
    lista_procs = df_proc['radicado'].tolist()
    seleccion = st.selectbox("Selecciona un Expediente para trabajar:", lista_procs)
    
    # Obtener datos del proceso
    proc_row = df_proc[df_proc['radicado'] == seleccion].iloc[0]
    proc_id = int(proc_row['id'])
    
    # Header del proceso
    st.markdown(f"""
    <div style="background-color:#e9ecef;padding:15px;border-radius:10px;margin-bottom:20px;">
        <h3>📌 Expediente: {seleccion}</h3>
        <p><strong>Estado:</strong> {proc_row['estado']} | <strong>Fase:</strong> {proc_row['fase_actual']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Cargar detalles (pasos y tiempos)
    all_detalles = w_detalles.get_all_records()
    df_det = pd.DataFrame(all_detalles)
    
    # Filtrar solo de este proceso
    if not df_det.empty:
        df_det = df_det[df_det['id_proceso'] == proc_id]
    
    # --- ITERAR FASES ---
    total_pasos_global = 0
    total_completados_global = 0
    
    for fase_nombre, info in FASES_PROCESO.items():
        with st.expander(f"📂 {fase_nombre}", expanded=(fase_nombre == proc_row['fase_actual'])):
            
            # --- SECCIÓN A: CRONÓMETRO ---
            # Buscar info de tiempo en df_det (usamos paso_idx = -1 para guardar el tiempo general de la fase)
            time_row = df_det[(df_det['fase'] == fase_nombre) & (df_det['paso_idx'] == -1)]
            
            tiempo_acumulado = 0.0
            timer_active = 0
            timer_start = 0.0
            
            if not time_row.empty:
                tiempo_acumulado = float(time_row.iloc[0]['tiempo_acumulado'])
                timer_active = int(time_row.iloc[0]['timer_active'])
                timer_start = float(time_row.iloc[0]['timer_start'])
            
            # Calculo tiempo real
            tiempo_mostrar = tiempo_acumulado
            if timer_active:
                tiempo_mostrar += (time.time() - timer_start)
                time.sleep(1) # Refresco para efecto visual
                st.rerun()
            
            c1, c2, c3 = st.columns([2,1,1])
            c1.markdown(f"#### ⏱️ Tiempo: `{formatear_tiempo(tiempo_mostrar)}`")
            
            if timer_active:
                if c2.button("⏸️ Pausar", key=f"p_{proc_id}_{fase_nombre}"):
                    # Guardar pausa
                    nuevo_acumulado = tiempo_acumulado + (time.time() - timer_start)
                    # Lógica de actualización en Sheets (borrar viejo, poner nuevo)
                    # Nota: Para producción masiva esto se optimiza, aquí usamos append/filter simple
                    filas_a_borrar = w_detalles.findall(str(proc_id))
                    # (Simplificación: Agregamos una nueva fila de estado y filtraremos por la última fecha/logica)
                    # MEJOR: Usar celdas específicas es complejo sin IDs de fila. 
                    # ESTRATEGIA: Appending log. Tomamos el último estado.
                    w_detalles.append_row([proc_id, fase_nombre, -1, 0, nuevo_acumulado, 0, 0])
                    st.rerun()
            else:
                if c2.button("▶️ Iniciar", key=f"s_{proc_id}_{fase_nombre}"):
                    w_detalles.append_row([proc_id, fase_nombre,