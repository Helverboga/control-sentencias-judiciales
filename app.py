import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import time
import random
import gspread
from gspread.exceptions import APIError
from google.oauth2.service_account import Credentials

# --- 1. CONFIGURACIÓN Y ESTILOS ---
st.set_page_config(
    page_title="Magistratura Cloud",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)


def con_reintentos(max_intentos=5, espera_inicial=2):
    """Decorador: si Google devuelve error 429 (cuota de lectura/escritura
    excedida), reintenta automáticamente con espera creciente (2s, 4s, 8s...)
    en vez de dejar que la aplicación truene con pantalla roja. Cualquier
    otro tipo de error (permisos, hoja no encontrada, etc.) se relanza de
    inmediato, sin reintentar -- reintentar esos no serviría de nada."""
    def decorador(func):
        def envoltura(*args, **kwargs):
            espera = espera_inicial
            ultimo_error = None
            for intento in range(max_intentos):
                try:
                    return func(*args, **kwargs)
                except APIError as e:
                    ultimo_error = e
                    es_cuota_excedida = "429" in str(e) or "Quota exceeded" in str(e)
                    if not es_cuota_excedida or intento == max_intentos - 1:
                        raise
                    time.sleep(espera + random.uniform(0, 1))
                    espera *= 2
            raise ultimo_error
        return envoltura
    return decorador


# Envoltorios de las operaciones de gspread que sí importan para la cuota
# (lecturas y escrituras) -- usar SIEMPRE estas funciones en vez de llamar
# a los métodos de gspread directamente, para que cualquier 429 puntual se
# resuelva solo.
@con_reintentos()
def leer_registros(ws):
    return ws.get_all_records()


@con_reintentos()
def leer_valores(ws):
    return ws.get_all_values()


@con_reintentos()
def agregar_fila(ws, fila):
    return ws.append_row(fila)


@con_reintentos()
def agregar_filas(ws, filas):
    return ws.append_rows(filas)


@con_reintentos()
def actualizar_celda(ws, fila, columna, valor):
    return ws.update_cell(fila, columna, valor)


@con_reintentos()
def buscar_celda(ws, texto):
    return ws.find(texto)


@con_reintentos()
def borrar_filas(ws, fila):
    return ws.delete_rows(fila)


@con_reintentos()
def limpiar_hoja(ws):
    return ws.clear()

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
    idx = FASE_ORDEN.index(fase_actual)
    if idx + 1 < len(FASE_ORDEN):
        return FASE_ORDEN[idx + 1]
    return None

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
        agregar_fila(w_proc, ["id", "radicado", "fecha", "estado", "fase_actual", "progreso"])

    try:
        w_det = sh.worksheet("Detalles")
    except Exception:
        w_det = sh.add_worksheet("Detalles", 2000, 10)
        agregar_fila(w_det, ["id_proc", "fase", "paso", "valor", "tiempo", "inicio", "activo"])

    return w_proc, w_det

@st.cache_data(ttl=5)
def leer_datos(_w_proc, _w_det):
    df_proc = pd.DataFrame(leer_registros(_w_proc))
    df_det = pd.DataFrame(leer_registros(_w_det))
    return df_proc, df_det

def vista_nuevo_proceso(w_proc, df_proc):
    st.markdown('<div class="main-header">➕ Nuevo Expediente</div>', unsafe_allow_html=True)
    with st.form("new_frm"):
        col1, col2 = st.columns(2)
        with col1:
            rad = st.text_input("Número de Radicado", placeholder="Ej: 2026-001")
        with col2:
            st.info("El proceso iniciará en Fase I automáticamente.")

        if st.form_submit_button("🚀 Crear Expediente"):
            existe = False
            if not df_proc.empty and 'radicado' in df_proc.columns:
                if str(rad) in df_proc['radicado'].astype(str).values:
                    existe = True

            if existe:
                st.error("¡Este radicado ya existe!")
            elif not rad:
                st.error("Debes escribir un radicado.")
            else:
                new_id = int(time.time())
                fecha = datetime.now().strftime("%Y-%m-%d")
                agregar_fila(w_proc, [new_id, rad, fecha, "Activo", "I. Fase Propedéutica", 0])
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

    st.info(f"📌 **Radicado:** {row['radicado']} | **Fase Actual:** {row['fase_actual']} | **Progreso Global:** {row['progreso']}%")

    _, data_det = leer_datos(w_proc, w_det)
    df_d = data_det.copy() if not data_det.empty else pd.DataFrame()

    cols_obligatorias = ["id_proc", "fase", "paso", "valor", "tiempo", "inicio", "activo"]
    if df_d.empty or not set(cols_obligatorias).issubset(df_d.columns):
        df_d = pd.DataFrame(columns=cols_obligatorias)

    if not df_d.empty:
        df_d = df_d[df_d['id_proc'] == proc_id]

    listado = FASES_PROCESO.items()
    total_ok = 0
    for fase, info in listado:
        expandir = (fase == row['fase_actual'])
        with st.expander(f"📁 {fase}", expanded=expandir):
            st.caption(f"_{info['descripcion']}_")

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

            if expandir and len(pasos) > 0 and prog == 1:
                try:
                    cell = buscar_celda(w_proc, str(sel))
                except Exception:
                    cell = None

                if cell:
                    sig = siguiente_fase(fase)
                    if sig:
                        actualizar_celda(w_proc, cell.row, 5, sig)
                        st.success(f"✅ Fase completada. El expediente avanzó a: {sig}")
                    else:
                        actualizar_celda(w_proc, cell.row, 4, "Finalizado")
                        st.success("🏁 ¡Expediente completado en todas sus fases!")
                    leer_datos.clear()
                    time.sleep(1)
                    st.rerun()

    progreso_ponderado = round((total_ok / TOTAL_PASOS) * 100) if TOTAL_PASOS > 0 else 0
    if progreso_ponderado != int(row['progreso']):
        try:
            cell = buscar_celda(w_proc, str(sel))
            if cell:
                actualizar_celda(w_proc, cell.row, 6, progreso_ponderado)
                leer_datos.clear()
        except Exception:
            pass

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
    datos = leer_valores(w_det)
    fila_encontrada = None
    for idx, f in enumerate(datos[1:], start=2):
        if len(f) >= 4 and str(f[0]) == str(proc_id) and f[1] == fase and str(f[2]) == str(paso):
            fila_encontrada = idx
            break
    if fila_encontrada:
        actualizar_celda(w_det, fila_encontrada, 4, valor)
    else:
        agregar_fila(w_det, [proc_id, fase, paso, valor, 0, 0, 0])

def eliminar_expediente(w_proc, w_det, proc_id, radicado):
    cell = buscar_celda(w_proc, str(radicado))
    if cell:
        borrar_filas(w_proc, cell.row)

    datos = leer_valores(w_det)
    if datos:
        encabezados = datos[0]
        filas = datos[1:]
        filas_restantes = [f for f in filas if f and str(f[0]) != str(proc_id)]
        limpiar_hoja(w_det)
        agregar_fila(w_det, encabezados)
        if filas_restantes:
            agregar_filas(w_det, filas_restantes)

def vista_reportes(df_proc):
    st.markdown('<div class="main-header">📊 Dashboard y Reportes</div>', unsafe_allow_html=True)

    if df_proc.empty:
        st.warning("No hay datos para mostrar aún.")
        return

    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="metric-card"><h1>{len(df_proc)}</h1>Total Expedientes</div>', unsafe_allow_html=True)

    promedio = 0
    if 'progreso' in df_proc.columns:
        promedio = pd.to_numeric(df_proc['progreso'], errors='coerce').mean()

    c2.markdown(f'<div class="metric-card"><h1>{promedio:.1f}%</h1>Avance Promedio</div>', unsafe_allow_html=True)

    activos = 0
    if 'estado' in df_proc.columns:
        activos = len(df_proc[df_proc['estado'] == 'Activo'])

    c3.markdown(f'<div class="metric-card"><h1>{activos}</h1>En Trámite</div>', unsafe_allow_html=True)

    st.markdown("---")

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

def check_password():
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

    cols_proc = ["id", "radicado", "fecha", "estado", "fase_actual", "progreso"]
    if df_proc.empty or not set(cols_proc).issubset(df_proc.columns):
        df_proc = pd.DataFrame(columns=cols_proc)

    st.sidebar.title("⚖️ Magistratura")
    st.sidebar.markdown("---")

    opcion = st.sidebar.radio("Navegación",
        ["🏠 Dashboard", "➕ Nuevo Proceso", "📂 Mis Expedientes", "📈 Reportes"]
    )

    st.sidebar.markdown("---")
    st.sidebar.caption("🟢 Sistema Online v2.0")

    if opcion == "🏠 Dashboard":
        vista_reportes(df_proc)
    elif opcion == "➕ Nuevo Proceso":
        vista_nuevo_proceso(w_proc, df_proc)
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
