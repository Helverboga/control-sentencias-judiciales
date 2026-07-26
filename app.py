import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import time
import gspread
from google.oauth2.service_account import Credentials

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

FASE_ORDEN = list(FASES_PROCESO.keys())
TOTAL_PASOS = sum(len(info['pasos']) for info in FASES_PROCESO.values())

def siguiente_fase(fase_actual):
    """Devuelve el nombre de la fase que sigue, o None si ya es la última."""
    idx = FASE_ORDEN.index(fase_actual)
    if idx + 1 < len(FASE_ORDEN):
        return FASE_ORDEN[idx + 1]
    return None

# --- 3. CONEXIÓN ---
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

@st.cache_resource
def get_connection():
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

@st.cache_resource
def get_data():
    client = get_connection()
    try:
        sh = client.open("DB_Control_Sentencias")
    except Exception:
        st.error("🚨 Error: No encuentro 'DB_Control_Sentencias' en Drive.")
        st.stop()
        
    try:
        w_proc = sh.worksheet("Procesos")
    except Exception:
        w_proc = sh.add_worksheet("Procesos", 100, 10)
        w_proc.append_row(["id", "radicado", "fecha", "estado", "fase_actual", "progreso"])

    try:
        w_det = sh.worksheet("Detalles")
    except Exception:
        w_det = sh.add_worksheet("Detalles", 2000, 10)
        w_det.append_row(["id_proc", "fase", "paso", "valor", "tiempo", "inicio", "activo"])
        
    return w_proc, w_det

@st.cache_data(ttl=5)
def leer_datos(_w_proc, _w_det):
    """Lee ambas hojas con una caché corta de 5 segundos, para no golpear la API
    de Google en cada recarga de la página. Después de cualquier escritura real
    (marcar un paso, crear o eliminar un expediente) se llama leer_datos.clear()
    para que el cambio se vea de inmediato."""
    df_proc = pd.DataFrame(_w_proc.get_all_records())
    df_det = pd.DataFrame(_w_det.get_all_records())
    return df_proc, df_det

# --- 4. FUNCIONES VISUALES Y LÓGICA ---
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
                leer_datos.clear()
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
    _, data_det = leer_datos(w_proc, w_det)
    df_d = data_det.copy() if not data_det.empty else pd.DataFrame()
    
    # Reconstrucción de seguridad si está vacío
    cols_obligatorias = ["id_proc", "fase", "paso", "valor", "tiempo", "inicio", "activo"]
    if df_d.empty or not set(cols_obligatorias).issubset(df_d.columns):
        df_d = pd.DataFrame(columns=cols_obligatorias)
    
    # Filtrar
    if not df_d.empty:
        df_d = df_d[df_d['id_proc'] == proc_id]

    # Iterar Fases
    listado = FASES_PROCESO.items()
    total_ok = 0
    for fase, info in listado:
        expandir = (fase == row['fase_actual'])
        with st.expander(f"📁 {fase}", expanded=expandir):
            st.caption(f"_{info['descripcion']}_")

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
                    actualizar_o_crear_detalle(w_det, proc_id, fase, i, val)
                    leer_datos.clear()
                    st.rerun()
            
            prog = ok_count / len(pasos) if len(pasos) > 0 else 0
            st.progress(prog)
            total_ok += ok_count

            # Avanzar a la siguiente fase si el checklist de la fase ACTIVA llegó al 100%
            if expandir and len(pasos) > 0 and prog == 1:
                try:
                    cell = w_proc.find(str(sel))
                except Exception:
                    cell = None

                if cell:
                    sig = siguiente_fase(fase)
                    if sig:
                        w_proc.update_cell(cell.row, 5, sig)   # columna 5 = fase_actual
                        st.success(f"✅ Fase completada. El expediente avanzó a: {sig}")
                    else:
                        w_proc.update_cell(cell.row, 4, "Finalizado")  # columna 4 = estado
                        st.success("🏁 ¡Expediente completado en todas sus fases!")
                    leer_datos.clear()
                    time.sleep(1)
                    st.rerun()

    # Progreso ponderado del expediente completo (las 4 fases, según su cantidad de pasos)
    progreso_ponderado = round((total_ok / TOTAL_PASOS) * 100) if TOTAL_PASOS > 0 else 0
    if progreso_ponderado != int(row['progreso']):
        try:
            cell = w_proc.find(str(sel))
            if cell:
                w_proc.update_cell(cell.row, 6, progreso_ponderado)  # columna 6 = progreso
                leer_datos.clear()
        except Exception:
            pass

    # --- ZONA DE PELIGRO: ELIMINAR EXPEDIENTE ---
    st.divider()
    with st.expander("⚠️ Zona de peligro"):
        st.warning("Esta acción elimina el expediente y todo su historial (checklist y tiempos registrados). No se puede deshacer.")
        confirmar = st.checkbox(
            f'Confirmo que deseo eliminar el expediente "{sel}" de forma permanente.',
            key=f"confirm_del_{proc_id}"
        )
        if st.button("🗑️ Eliminar expediente definitivamente", disabled=not confirmar, key=f"del_{proc_id}"):
            eliminar_expediente(w_proc, w_det, proc_id, sel)
            leer_datos.clear()
            st.success(f"Expediente {sel} eliminado.")
            time.sleep(1)
            st.rerun()

def actualizar_o_crear_detalle(w_det, proc_id, fase, paso, valor):
    """Actualiza en el lugar la fila del paso si ya existe; si no, la crea.
    Evita que la hoja 'Detalles' crezca sin control con una fila nueva
    cada vez que se marca o desmarca una casilla."""
    datos = w_det.get_all_values()
    fila_encontrada = None
    for idx, f in enumerate(datos[1:], start=2):  # fila 1 = encabezados
        if len(f) >= 4 and str(f[0]) == str(proc_id) and f[1] == fase and str(f[2]) == str(paso):
            fila_encontrada = idx
            break
    if fila_encontrada:
        w_det.update_cell(fila_encontrada, 4, valor)  # columna 4 = valor
    else:
        w_det.append_row([proc_id, fase, paso, valor, 0, 0, 0])

def eliminar_expediente(w_proc, w_det, proc_id, radicado):
    """Elimina la fila del expediente en 'Procesos' y todo su historial en 'Detalles'."""
    cell = w_proc.find(str(radicado))
    if cell:
        w_proc.delete_rows(cell.row)

    datos = w_det.get_all_values()
    if datos:
        encabezados = datos[0]
        filas = datos[1:]
        filas_restantes = [f for f in filas if f and str(f[0]) != str(proc_id)]
        w_det.clear()
        w_det.append_row(encabezados)
        if filas_restantes:
            w_det.append_rows(filas_restantes)

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
def check_password():
    """Devuelve True si ya se escribió la contraseña correcta en esta sesión."""
    def password_entered():
        if st.session_state["password"] == st.secrets["app_password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.markdown('<div class="main-header">⚖️ Magistratura Cloud</div>', unsafe_allow_html=True)
    st.text_input("Contraseña", type="password", on_change=password_entered, key="password")
    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("😕 Contraseña incorrecta")
    return False

def main():
    w_proc, w_det = get_data()
    df_proc, _ = leer_datos(w_proc, w_det)
    
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
    if check_password():
        main()
