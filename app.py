import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. CONFIGURACIÓN Y ESTILOS ---
st.set_page_config(
    page_title="Magistratura Cloud",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Personalizado (El diseño bonito)
st.markdown("""
<style>
    .main-header {
        font-size: 2.2em;
        font-weight: bold;
        color: #1f4e79;
        text-align: center;
        border-bottom: 3px solid #d4a574;
        margin-bottom: 20px;
        padding-bottom: 10px;
    }
    .metric-card {
        background: linear-gradient(135deg, #1f4e79, #2d5aa0);
        color: white;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
    }
    .phase-header {
        background-color: #f8f9fa;
        padding: 10px;
        border-left: 5px solid #1f4e79;
        border-radius: 5px;
        margin-top: 10px;
    }
    .stProgress > div > div > div > div {
        background-color: #28a745;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. DEFINICIÓN DETALLADA DE FASES ---
FASES_PROCESO = {
    "I. Fase Propedéutica": {
        "descripcion": "Preparación y Auto de Pruebas",
        "pasos": [
            "01) Copiar y pegar 0.Kit", "02) Cambiar nombre a 0. Kit", "03) Crear carpeta mes",
            "04) Descargar expediente", "05) Aprovisionar herramientas", "06) Editar e imprimir",
            "07) Índice del expediente", "08) Foto del proceso", "09) Estructurar piezas",
            "10) Reporte de pruebas", "11) Fáctum", "12) Auto de pruebas", "13) Notificar"
        ]
    },
    "II. Fase Lectura": {
        "descripcion": "Análisis comprensivo (0.5 días)",
        "pasos": ["01) Lectura completa", "02) Identificar claves", "03) Toma de notas"]
    },
    "III. Fase Sentencia": {
        "descripcion": "Redacción del fallo (5 días)",
        "pasos": [
            "01) Elegir modelo", "02) Sintetizar escritos", "03) Agregar síntesis",
            "04) Investigación jurídica", "05) Alojar investigaciones", "06) Jurisprudencia",
            "07) Valorar pruebas", "08) 6 etapas sentencia", "09) Enriquecer proyecto",
            "10) Guardar proyecto"
        ]
    },
    "IV. Fase Audiencia": {
        "descripcion": "Preparación oralidad (2 días)",
        "pasos": ["01) Operar algoritmo", "02) Presupuestos", "03) Crear capa", 
                  "04) Asistencia", "05) Roteiro"]
    }
}

# --- 3. CONEXIÓN ---
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
        st.error("🚨 Error: No encuentro 'DB_Control_Sentencias' en Drive.")
        st.stop()
        
    try:
        w_proc = sh.worksheet("Procesos")
    except:
        w_proc = sh.add_worksheet("Procesos", 100, 10)
        w_proc.append_row(["id", "radicado", "fecha", "estado", "fase_actual", "progreso"])

    try:
        w_det = sh.worksheet("Detalles")
    except:
        w_det = sh.add_worksheet("Detalles", 2000, 10)
        w_det.append_row(["id_proc", "fase", "paso", "valor", "tiempo", "inicio", "activo"])
        
    return w_proc, w_det

# --- 4. FUNCIONES VISUALES Y LÓGICA ---
def formatear_tiempo(segundos):
    segundos = int(segundos)
    if segundos < 60: return f"{segundos}s"
    mins = segundos // 60
    return f"{mins}m {segundos % 60}s"

def vista_nuevo_proceso(w_proc):
    st.markdown('<div class="main-header">➕ Nuevo Expediente</div>', unsafe_allow_html=True)
    with st.form("new_frm"):
        col1, col2 = st.columns(2)
        with col1:
            rad = st.text_input("Número de Radicado", placeholder="Ej: 2026-001")
        with col2:
            st.info("El proceso iniciará en Fase I automáticamente.")
            
        if st.form_submit_button("🚀 Crear Expediente"):
            df = pd.DataFrame(w_proc.get_all_records())
            
            # Validación segura
            existe = False
            if not df.empty and 'radicado' in df.columns:
                if str(rad) in df['radicado'].astype(str).values:
                    existe = True
            
            if existe:
                st.error("¡Este radicado ya existe!")
            elif not rad:
                st.error("Debes escribir un radicado.")
            else:
                new_id = int(time.time())
                fecha = datetime.now().strftime("%Y-%m-%d")
                w_proc.append_row([new_id, rad, fecha, "Activo", "I. Fase Propedéutica", 0])
                st.success("✅ ¡Expediente Creado!")
                time.sleep(1)
                st.rerun()

def vista_gestion(w_proc, w_det, df_proc):
    st.markdown('<div class="main-header">📂 Gestión de Expedientes</div>', unsafe_allow_html=True)
    
    lista = df_proc['radicado'].tolist()
    sel = st.selectbox("Seleccione el Expediente a trabajar:", lista)
    
    row = df_proc[df_proc['radicado'] == sel].iloc[0]
    proc_id = int(row['id'])
    
    # Header del Proceso
    st.info(f"📌 **Radicado:** {row['radicado']} | **Fase Actual:** {row['fase_actual']} | **Progreso Global:** {row['progreso']}%")
    
    # --- BLINDAJE DE DATOS ---
    data_det = w_det.get_all_records()
    df_d = pd.DataFrame(data_det)
    
    # Reconstrucción de seguridad si está vacío
    cols_obligatorias = ["id_proc", "fase", "paso", "valor", "tiempo", "inicio", "activo"]
    if df_d.empty or not set(cols_obligatorias).issubset(df_d.columns):
        df_d = pd.DataFrame(columns=cols_obligatorias)
    
    # Filtrar
    if not df_d.empty:
        df_d = df_d[df_d['id_proc'] == proc_id]

    # Iterar Fases
    listado = FASES_PROCESO.items()
    for fase, info in listado:
        expandir = (fase == row['fase_actual'])
        with st.expander(f"📁 {fase}", expanded=expandir):
            st.caption(f"_{info['descripcion']}_")
            
            # A. RELOJ
            t_row = df_d[(df_d['fase'] == fase) & (df_d['paso'] == -1)]
            
            t_acum = 0.0
            t_act = 0
            t_ini = 0.0
            
            if not t_row.empty:
                last = t_row.iloc[-1]
                t_acum = float(last['tiempo'])
                t_act = int(last['activo'])
                t_ini = float(last['inicio'])
            
            t_show = t_acum
            if t_act:
                t_show += (time.time() - t_ini)
                time.sleep(1)
                st.rerun()
            
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"### ⏱️ `{formatear_tiempo(t_show)}`")
            
            if t_act == 0:
                if c2.button("▶️ Iniciar", key=f"s_{proc_id}_{fase}"):
                    w_det.append_row([proc_id, fase, -1, 0, t_acum, time.time(), 1])
                    st.rerun()
            else:
                if c2.button("⏸️ Pausar", key=f"p_{proc_id}_{fase}"):
                    n_acum = t_acum + (time.time() - t_ini)
                    w_det.append_row([proc_id, fase, -1, 0, n_acum, 0, 0])
                    st.rerun()
            
            st.divider()
            
            # B. CHECKLIST
            pasos = info['pasos']
            ok_count = 0
            for i, txt in enumerate(pasos):
                p_row = df_d[(df_d['fase'] == fase) & (df_d['paso'] == i)]
                checked = False
                if not p_row.empty:
                    checked = bool(p_row.iloc[-1]['valor'])
                
                c_chk, c_txt = st.columns([1, 15])
                new_val = c_chk.checkbox("", value=checked, key=f"k_{proc_id}_{fase}_{i}")
                c_txt.write(txt)
                
                if new_val: ok_count += 1
                
                if new_val != checked:
                    val = 1 if new_val else 0
                    w_det.append_row([proc_id, fase, i, val, 0, 0, 0])
                    st.rerun()
            
            prog = ok_count / len(pasos) if len(pasos) > 0 else 0
            st.progress(prog)
            
            # Actualizar Progreso Global
            if expandir and len(pasos) > 0:
                new_glob = int(prog * 100)
                if new_glob != int(row['progreso']):
                     try:
                         cell = w_proc.find(str(sel))
                         w_proc.update_cell(cell.row, 6, new_glob)
                     except: pass

def vista_reportes(df_proc):
    st.markdown('<div class="main-header">📊 Dashboard y Reportes</div>', unsafe_allow_html=True)
    
    if df_proc.empty:
        st.warning("No hay datos para mostrar aún.")
        return

    # Tarjetas Métricas
    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="metric-card"><h1>{len(df_proc)}</h1>Total Expedientes</div>', unsafe_allow_html=True)
    
    # Cálculo seguro del promedio
    promedio = 0
    if 'progreso' in df_proc.columns:
        promedio = pd.to_numeric(df_proc['progreso'], errors='coerce').mean()
    
    c2.markdown(f'<div class="metric-card"><h1>{promedio:.1f}%</h1>Avance Promedio</div>', unsafe_allow_html=True)
    
    activos = 0
    if 'estado' in df_proc.columns:
        activos = len(df_proc[df_proc['estado'] == 'Activo'])
    
    c3.markdown(f'<div class="metric-card"><h1>{activos}</h1>En Trámite</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Gráficos
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        st.subheader("Estado de Avance por Expediente")
        if not df_proc.empty and 'radicado' in df_proc.columns and 'progreso' in df_proc.columns:
            fig_bar = px.bar(df_proc, x='radicado', y='progreso', color='fase_actual', 
                            title="Progreso Individual", height=400)
            st.plotly_chart(fig_bar, use_container_width=True)
        
    with col_g2:
        st.subheader("Distribución por Fases")
        if not df_proc.empty and 'fase_actual' in df_proc.columns:
            conteo_fases = df_proc['fase_actual'].value_counts().reset_index()
            conteo_fases.columns = ['Fase', 'Cantidad']
            fig_pie = px.pie(conteo_fases, values='Cantidad', names='Fase', 
                            title="Carga de Trabajo", height=400)
            st.plotly_chart(fig_pie, use_container_width=True)
    
    st.markdown("### 📋 Tabla de Datos")
    st.dataframe(df_proc, use_container_width=True)

# --- 5. MAIN ---
def main():
    w_proc, w_det = get_data()
    df_proc = pd.DataFrame(w_proc.get_all_records())
    
    # Manejo de DF vacío en Procesos
    cols_proc = ["id", "radicado", "fecha", "estado", "fase_actual", "progreso"]
    if df_proc.empty or not set(cols_proc).issubset(df_proc.columns):
        df_proc = pd.DataFrame(columns=cols_proc)

    # --- BARRA LATERAL CON ÍCONOS ---
    st.sidebar.title("⚖️ Magistratura")
    st.sidebar.markdown("---")
    
    # Menú Restaurado
    opcion = st.sidebar.radio("Navegación", 
        ["🏠 Dashboard", "➕ Nuevo Proceso", "📂 Mis Expedientes", "📈 Reportes"]
    )
    
    st.sidebar.markdown("---")
    st.sidebar.caption("🟢 Sistema Online v2.0")
    
    # Lógica de Navegación
    if opcion == "🏠 Dashboard":
        # Dashboard simplificado (o reusa reportes)
        vista_reportes(df_proc)
        
    elif opcion == "➕ Nuevo Proceso":
        vista_nuevo_proceso(w_proc)
        
    elif opcion == "📂 Mis Expedientes":
        if df_proc.empty:
            st.warning("⚠️ No hay expedientes. Ve a 'Nuevo Proceso' para crear uno.")
        else:
            vista_gestion(w_proc, w_det, df_proc)
            
    elif opcion == "📈 Reportes":
        vista_reportes(df_proc)

if __name__ == "__main__":
    main()