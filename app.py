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
    
    for fase, info in FASES_PROCESO.items():
        with st.expander(f"📌 {fase}", expanded=(fase == row['fase_actual'])):
            
            # --- CRONÓMETRO ---
            # Buscar último registro de tiempo (paso_idx = -1)
            t_row = df_det[(df_det['fase'] == fase) & (df_det['paso_idx'] == -1)]
            
            t_acum = 0.0
            t_activo = 0
            t_inicio = 0.0
            
            if not t_row.empty:
                # Tomamos el último registro válido
                last = t_row.iloc[-1]
                t_acum = float(last['tiempo'])
                t_activo = int(last['activo'])
                t_inicio = float(last['inicio'])
            
            t_show = t_acum
            if t_activo:
                t_show += (time.time() - t_inicio)
                time.sleep(1) # Refresco
                st.rerun()
                
            c1, c2 = st.columns([3, 1])
            c1.write(f"⏱️ **Tiempo:** `{formatear_tiempo(t_show)}`")
            
            if t_activo:
                if c2.button("⏸️ Pausar", key=f"p_{proc_id}_{fase}"):
                    nuevo_t = t_acum + (time.time() - t_inicio)
                    # Guardar fila de pausa: paso_idx=-1, activo=0
                    w_detalles.append_row([proc_id, fase, -1, 0, nuevo_t, 0, 0])
                    st.rerun()
            else:
                if c2.button("▶️ Iniciar", key=f"s_{proc_id}_{fase}"):
                    # Guardar fila de inicio: paso_idx=-1, activo=1
                    w_detalles.append_row([proc_id, fase, -1, 0, t_acum, time.time(), 1])
                    st.rerun()
            
            st.divider()
            
            # --- CHECKLIST ---
            pasos = info['pasos']
            total_pasos += len(pasos)
            ok_fase = 0
            
            for i, txt in enumerate(pasos):
                # Buscar estado
                p_row = df_det[(df_det['fase'] == fase) & (df_det['paso_idx'] == i)]
                checked = False
                if not p_row.empty:
                    checked = bool(p_row.iloc[-1]['val'])
                
                col_c, col_t = st.columns([1, 12])
                new_val = col_c.checkbox("", value=checked, key=f"c_{proc_id}_{fase}_{i}")
                col_t.write(txt)
                
                if new_val: ok_fase += 1
                
                if new_val != checked:
                    # Guardar cambio: val=1 o 0
                    v_num = 1 if new_val else 0
                    w_detalles.append_row([proc_id, fase, i, v_num, 0, 0, 0])
                    st.rerun()
            
            st.progress(ok_fase / len(pasos))
            total_ok += ok_fase

    # Actualizar Global
    if total_pasos > 0:
        new_prog = int((total_ok / total_pasos) * 100)
        # Actualizar celda de progreso (Columna 6) en la hoja Procesos
        # Buscamos la fila por ID (forma simplificada: buscar texto del radicado)
        try:
            cell = w_proc.find(str(row['radicado']))
            w_proc.update_cell(cell.row, 6, new_prog)
        except:
            pass # Si no encuentra, no rompe la app

# --- MAIN ---
def main():
    w_proc, w_det = get_data()
    data = w_proc.get_all_records()
    df = pd.DataFrame(data)
    
    st.sidebar.title("⚖️ Magistratura")
    opcion = st.sidebar.radio("Menú", ["Dashboard", "Nuevo Proceso", "Gestionar"])
    
    if opcion == "Dashboard":
        st.markdown('<div class="main-header">📊 Resumen</div>', unsafe_allow_html=True)
        if not df.empty:
            c1, c2 = st.columns(2)
            c1.markdown(f'<div class="metric-card"><h1>{len(df)}</h1>Procesos</div>', unsafe_allow_html=True)
            prom = df['progreso'].mean()
            c2.markdown(f'<div class="metric-card"><h1>{prom:.1f}%</h1>Avance</div>', unsafe_allow_html=True)
            st.bar_chart(df, x="radicado", y="progreso")
        else:
            st.info("Sin datos.")
            
    elif opcion == "Nuevo Proceso":
        nuevo_proceso(w_proc)
        
    elif opcion == "Gestionar":
        if df.empty:
            st.warning("Crea un proceso primero.")
        else:
            gestionar(w_proc, w_det, df)

if __name__ == "__main__":
    main()