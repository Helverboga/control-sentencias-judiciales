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
            "01) Copiar y pegar 0.Kit",
            "02) Cambiar nombre a 0. Kit", 
            "03) Crear carpeta en el mes correspondiente",
            "04) Descargar expediente digital",
            "05) Aprovisionar de herramientas la carpeta",
            "06) Editar e imprimir",
            "07) Índice del expediente",
            "08) Foto del proceso",
            "09) Estructurar piezas procesales",
            "10) Reporte de pruebas",
            "11) Hago el fáctum",
            "12) Elaboro el auto de pruebas",
            "13) Comparo, corrijo y envío a notificación"
        ]
    },
    "II. Fase Lectura del Expediente": {
        "descripcion": "Análisis comprensivo (0.5 días)",
        "pasos": [
            "01) Lectura completa y comprensiva",
            "02) Identificación de puntos clave",
            "03) Toma de notas relevantes"
        ]
    },
    "III. Fase Elaboración de Sentencia": {
        "descripcion": "Redacción del fallo (5 días)",
        "pasos": [
            "01) Elegir modelo, guardar y rotular",
            "02) Sintetizar escritos fundamentales",
            "03) Agrego al borrador la síntesis",
            "04) Investigación jurídica y resíntesis",
            "05) Alojar investigaciones en carpeta",
            "06) Investigación jurisprudencial",
            "07) Valorar pruebas individual y conjunto",
            "08) Elaborar 6 etapas de sentencia oral",
            "09) Enriquecer jurisprudencialmente",
            "10) Guardar proyecto en carpeta"
        ]
    },
    "IV. Fase Preparación Audiencia": {
        "descripcion": "Preparación inteligente (2 días)",
        "pasos": [
            "01) Opero conforme el algoritmo",
            "02) Presupuestos procesales y sustanciales",
            "03) Creo la capa",
            "04) Control de asistencia",
            "05) Elijo y hago el roteiro"
        ]
    }
}

# --- 3. CONEXIÓN A GOOGLE SHEETS ---
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
        st.error("🚨 Error crítico: No encuentro la hoja 'DB_Control_Sentencias' en tu Google Drive.")
        st.stop()
        
    # Inicializar Hojas si no existen
    try:
        w_proc = sh.worksheet("Procesos")
    except:
        w_proc = sh.add_worksheet("Procesos", 100, 10)
        w_proc.append_row(["id", "radicado", "fecha", "estado", "fase_actual", "progreso"])

    try:
        w_det = sh.worksheet("Detalles")
    except:
        w_det = sh.add_worksheet("Detalles", 2000, 10)
        # Estructura: id_proceso, fase, paso_index, valor(0/1), tiempo_acumulado, timestamp_inicio, timer_activo(0/1)
        w_det.append_row(["id_proc", "fase", "paso", "valor", "tiempo", "inicio", "activo"])
        
    return w_proc, w_det

# --- 4. FUNCIONES DE LÓGICA ---
def formatear_tiempo(segundos):
    segundos = int(segundos)
    if segundos < 60: return f"{segundos}s"
    minutes = segundos // 60
    if minutes < 60: return f"{minutes}m {segundos % 60}s"
    hours = minutes // 60
    return f"{hours}h {minutes % 60}m"

# --- 5. INTERFAZ: NUEVO PROCESO ---
def vista_nuevo_proceso(w_proc):
    st.markdown('<div class="main-header">➕ Nuevo Expediente</div>', unsafe_allow_html=True)
    
    with st.form("form_nuevo"):
        col1, col2 = st.columns(2)
        with col1:
            radicado = st.text_input("Número de Radicado", placeholder="Ej: 2026-001-CIVIL")
        with col2:
            st.info("El proceso iniciará en la Fase I automáticamente.")
            
        submitted = st.form_submit_button("🚀 Crear Expediente")
        
        if submitted:
            if not radicado:
                st.error("El radicado es obligatorio.")
                return
                
            # Validar duplicados
            df = pd.DataFrame(w_proc.get_all_records())
            if not df.empty and str(radicado) in df['radicado'].astype(str).values:
                st.error("¡Este expediente ya existe!")
            else:
                new_id = int(time.time())
                fecha = datetime.now().strftime("%Y-%m-%d")
                w_proc.append_row([new_id, radicado, fecha, "Activo", "I. Fase Propedéutica", 0])
                st.success(f"✅ Expediente {radicado} creado en la Nube.")
                time.sleep(1.5)
                st.rerun()

# --- 6. INTERFAZ: GESTIÓN PRINCIPAL ---
def vista_gestion(w_proc, w_det, df_proc):
    st.markdown('<div class="main-header">📂 Gestión de Expedientes</div>', unsafe_allow_html=True)
    
    # Selector
    lista_opciones = df_proc['radicado'].tolist()
    seleccion = st.selectbox("Seleccione el Expediente a trabajar:", lista_opciones)
    
    # Obtener datos del seleccionado
    row = df_proc[df_proc['radicado'] == seleccion].iloc[0]
    proc_id = int(row['id'])
    
    # Encabezado del Proceso
    st.info(f"📌 **Radicado:** {row['radicado']} | **Fase Actual:** {row['fase_actual']} | **Progreso Global:** {row['progreso']}%")
    global_progress_bar = st.progress(int(row['progreso']) / 100)
    
    # Cargar detalles de este proceso
    data_det = w_det.get_all_records()
    df_d = pd.DataFrame(data_det)
    if not df_d.empty:
        df_d = df_d[df_d['id_proc'] == proc_id]
    
    # Variables para cálculo global
    total_pasos_global = 0
    total_completados_global = 0
    
    # --- ITERAR FASES ---
    listado_fases = FASES_PROCESO.items() # Para evitar error de sintaxis
    
    for fase_nombre, info in listado_fases:
        es_fase_actual = (fase_nombre == row['fase_actual'])
        
        with st.expander(f"📁 {fase_nombre}", expanded=es_fase_actual):
            st.markdown(f"_{info['descripcion']}_")
            
            # --- A. CRONÓMETRO ---
            # Buscar último estado del reloj (paso = -1)
            t_row = df_d[(df_d['fase'] == fase_nombre) & (df_d['paso'] == -1)]
            
            t_acumulado = 0.0
            t_activo = 0
            t_inicio = 0.0
            
            if not t_row.empty:
                ultimo_reg = t_row.iloc[-1]
                t_acumulado = float(ultimo_reg['tiempo'])
                t_activo = int(ultimo_reg['activo'])
                t_inicio = float(ultimo_reg['inicio'])
            
            # Calcular tiempo real visual
            t_mostrar = t_acumulado
            if t_activo == 1:
                t_mostrar += (time.time() - t_inicio)
                time.sleep(1) # Refresco automático
                st.rerun()
            
            c1, c2, c3 = st.columns([2, 1, 1])
            c1.markdown(f"### ⏱️ `{formatear_tiempo(t_mostrar)}`")
            
            if t_activo == 0:
                if c2.button("▶️ Iniciar", key=f"start_{proc_id}_{fase_nombre}"):
                    # Guardar inicio
                    w_det.append_row([proc_id, fase_nombre, -1, 0, t_acumulado, time.time(), 1])
                    st.rerun()
            else:
                if c2.button("⏸️ Pausar", key=f"pause_{proc_id}_{fase_nombre}"):
                    # Guardar pausa y actualizar acumulado
                    nuevo_acum = t_acumulado + (time.time() - t_inicio)
                    w_det.append_row([proc_id, fase_nombre, -1, 0, nuevo_acum, 0, 0])
                    st.rerun()
            
            st.divider()
            
            # --- B. LISTA DE PASOS ---
            pasos = info['pasos']
            total_pasos_global += len(pasos)
            ok_local = 0
            
            for i, texto_paso in enumerate(pasos):
                # Buscar estado del checkbox
                chk_row = df_d[(df_d['fase'] == fase_nombre) & (df_d['paso'] == i)]
                checked = False
                if not chk_row.empty:
                    checked = bool(chk_row.iloc[-1]['valor'])
                
                # Checkbox
                col_chk, col_txt = st.columns([1, 15])
                nuevo_valor = col_chk.checkbox("", value=checked, key=f"chk_{proc_id}_{fase_nombre}_{i}")
                col_txt.write(texto_paso)
                
                if nuevo_valor:
                    ok_local += 1
                
                # Guardar cambios si hubo clic
                if nuevo_valor != checked:
                    val_num = 1 if nuevo_valor else 0
                    w_det.append_row([proc_id, fase_nombre, i, val_num, 0, 0, 0])
                    st.rerun()
            
            # Barra de progreso local
            progreso_local = ok_local / len(pasos)
            st.progress(progreso_local)
            st.caption(f"Progreso de Fase: {int(progreso_local*100)}%")
            
            total_completados_global += ok_local

    # --- ACTUALIZAR PROGRESO GLOBAL ---
    if total_pasos_global > 0:
        nuevo_progreso_global = int((total_completados_global / total_pasos_global) * 100)
        # Solo actualizamos si cambió (para no saturar Sheets)
        if nuevo_progreso_global != int(row['progreso']):
            # Buscar celda y actualizar
            try:
                cell = w_proc.find(str(row['radicado']))
                if cell:
                    w_proc.update_cell(cell.row, 6, nuevo_progreso_global) # Columna 6 es progreso
            except:
                pass

# --- 7. INTERFAZ: REPORTES Y DASHBOARD ---
def vista_reportes(df_proc):
    st.markdown('<div class="main-header">📊 Dashboard y Reportes</div>', unsafe_allow_html=True)
    
    if df_proc.empty:
        st.warning("No hay datos para mostrar.")
        return

    # Tarjetas Métricas
    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="metric-card"><h1>{len(df_proc)}</h1>Total Expedientes</div>', unsafe_allow_html=True)
    
    promedio = df_proc['progreso'].mean()
    c2.markdown(f'<div class="metric-card"><h1>{promedio:.1f}%</h1>Avance Promedio</div>', unsafe_allow_html=True)
    
    activos = len(df_proc[df_proc['estado'] == 'Activo'])
    c3.markdown(f'<div class="metric-card"><h1>{activos}</h1>En Trámite</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Gráficos
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        st.subheader("Estado de Avance por Expediente")
        fig_bar = px.bar(df_proc, x='radicado', y='progreso', color='fase_actual', 
                         title="Progreso Individual", height=400)
        st.plotly_chart(fig_bar, use_container_width=True)
        
    with col_g2:
        st.subheader("Distribución por Fases")
        conteo_fases = df_proc['fase_actual'].value_counts().reset_index()
        conteo_fases.columns = ['Fase', 'Cantidad']
        fig_pie = px.pie(conteo_fases, values='Cantidad', names='Fase', 
                         title="Carga de Trabajo por Fase", height=400)
        st.plotly_chart(fig_pie, use_container_width=True)
    
    st.markdown("### 📋 Tabla de Datos")
    st.dataframe(df_proc[['radicado', 'fecha', 'fase_actual', 'progreso', 'estado']], use_container_width=True)

# --- 8. EJECUCIÓN PRINCIPAL ---
def main():
    w_proc, w_det = get_data()
    data_proc = w_proc.get_all_records()
    df_proc = pd.DataFrame(data_proc)
    
    # Barra Lateral
    st.sidebar.title("⚖️ Magistratura")
    st.sidebar.markdown("---")
    opcion = st.sidebar.radio("Navegación", 
        ["🏠 Dashboard", "➕ Nuevo Proceso", "📂 Mis Expedientes", "📈 Reportes"]
    )
    st.sidebar.markdown("---")
    st.sidebar.caption("🟢 Sistema Online | Sincronizado con Google Drive")
    
    if opcion == "🏠 Dashboard":
        vista_reportes(df_proc) # El dashboard es lo mismo que reportes simplificado
    elif opcion == "➕ Nuevo Proceso":
        vista_nuevo_proceso(w_proc)
    elif opcion == "📂 Mis Expedientes":
        if df_proc.empty:
            st.info("No hay expedientes creados. Ve a 'Nuevo Proceso'.")
        else:
            vista_gestion(w_proc, w_det, df_proc)
    elif opcion == "📈 Reportes":
        vista_reportes(df_proc)

if __name__ == "__main__":
    main()