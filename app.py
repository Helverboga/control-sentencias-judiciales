import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Control Sentencias Cloud", page_icon="⚖️", layout="wide")

# --- CONEXIÓN CON GOOGLE SHEETS ---
def get_google_sheet():
    """Conecta con Google Sheets usando los Secretos de Streamlit"""
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    # Crear credenciales desde los secrets de Streamlit
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    # Abrir la hoja de cálculo
    try:
        sheet = client.open("DB_Control_Sentencias")
        return sheet
    except gspread.SpreadsheetNotFound:
        st.error("🚨 No encontré la hoja 'DB_Control_Sentencias'. ¡Créala en tu Drive y compártela con el robot!")
        st.stop()

def init_sheets():
    """Inicializa las pestañas si no existen"""
    sh = get_google_sheet()
    
    # 1. Hoja de PROCESOS
    try:
        w_proc = sh.worksheet("Procesos")
    except:
        w_proc = sh.add_worksheet(title="Procesos", rows="100", cols="10")
        w_proc.append_row(["id_unico", "radicado", "fecha_inicio", "estado", "fase_actual", "progreso", "alertas"])

    # 2. Hoja de TIEMPOS (Cronómetros)
    try:
        w_time = sh.worksheet("Tiempos")
    except:
        w_time = sh.add_worksheet(title="Tiempos", rows="1000", cols="5")
        w_time.append_row(["id_unico", "fase", "tiempo_acumulado", "ultimo_inicio", "estado_timer"])

    # 3. Hoja de PASOS (Checklist)
    try:
        w_steps = sh.worksheet("Pasos")
    except:
        w_steps = sh.add_worksheet(title="Pasos", rows="1000", cols="5")
        w_steps.append_row(["id_unico", "fase", "paso_index", "completado", "fecha_check"])

    return w_proc, w_time, w_steps

# --- DEFINICIÓN DE FASES (Tu lógica original) ---
FASES_PROCESO = {
    "I. Fase Propedéutica": {
        "limite_dias": None,
        "pasos": [
            "01) Copiar y pegar Kit", "02) Cambiar nombre carpeta", "03) Crear carpeta mes",
            "04) Descargar expediente", "05) Aprovisionar herramientas", "06) Editar e imprimir",
            "07) Índice del expediente", "08) Foto del proceso", "09) Estructurar piezas",
            "10) Reporte de pruebas", "11) Fáctum", "12) Auto de pruebas", "13) Enviar a notificación"
        ]
    },
    "II. Fase Lectura": {
        "limite_dias": 0.5,
        "pasos": ["01) Lectura comprensiva", "02) Identificar claves", "03) Toma de notas"]
    },
    "III. Fase Sentencia": {
        "limite_dias": 5.0,
        "pasos": [
            "01) Elegir modelo", "02) Sintetizar escritos", "03) Agregar síntesis",
            "04) Investigación jurídica", "05) Guardar insumos", "06) Jurisprudencia temas",
            "07) Valorar pruebas", "08) 6 etapas sentencia oral", "09) Enriquecer proyecto",
            "10) Guardar fallo final"
        ]
    },
    "IV. Fase Audiencia": {
        "limite_dias": 2.0,
        "pasos": ["01) Operar algoritmo", "02) Presupuestos proc/sust", "03) Crear capa", 
                  "04) Asistencia", "05) Roteiro"]
    }
}

# --- FUNCIONES DE LÓGICA ---
def formatear_tiempo(segundos):
    if segundos < 60: return f"{int(segundos)}s"
    minutes = int(segundos // 60)
    if minutes < 60: return f"{minutes}m {int(segundos % 60)}s"
    hours = int(minutes // 60)
    return f"{hours}h {minutes % 60}m"

# --- INTERFAZ PRINCIPAL ---
def main():
    st.title("⚖️ Control de Sentencias (Cloud Sync)")
    
    # Inicializar DB
    if 'db_ready' not in st.session_state:
        with st.spinner("Conectando con Google Sheets..."):
            init_sheets()
        st.session_state.db_ready = True
    
    sh = get_google_sheet()
    w_proc = sh.worksheet("Procesos")
    w_time = sh.worksheet("Tiempos")
    w_steps = sh.worksheet("Pasos")

    # Sidebar
    menu = st.sidebar.radio("Menú", ["🏠 Dashboard", "➕ Nuevo Proceso", "📂 Mis Procesos"])

    # 1. NUEVO PROCESO
    if menu == "➕ Nuevo Proceso":
        st.header("Registrar Nuevo Proceso")
        with st.form("new_proc"):
            radicado = st.text_input("Número de Radicado (Ej: 2025-001)")
            if st.form_submit_button("Crear Expediente"):
                # Verificar duplicados
                df_p = pd.DataFrame(w_proc.get_all_records())
                if not df_p.empty and str(radicado) in df_p['radicado'].astype(str).values:
                    st.error("¡Ese radicado ya existe!")
                else:
                    # Crear ID único basado en timestamp
                    new_id = int(time.time())
                    fecha = datetime.now().strftime("%Y-%m-%d")
                    w_proc.append_row([new_id, radicado, fecha, "Activo", "I. Fase Propedéutica", 0, "Normal"])
                    st.success(f"Proceso {radicado} creado en la Nube ☁️")
                    time.sleep(1)
                    st.rerun()

    # 2. DASHBOARD / MIS PROCESOS
    elif menu in ["🏠 Dashboard", "📂 Mis Procesos"]:
        # Cargar datos
        df_proc = pd.DataFrame(w_proc.get_all_records())
        
        if df_proc.empty:
            st.info("No hay procesos activos. Ve a 'Nuevo Proceso' para comenzar.")
            return

        # Selector de proceso
        lista_procs = df_proc['radicado'].tolist()
        seleccion = st.selectbox("Seleccionar Proceso para trabajar:", lista_procs)
        
        # Obtener datos del proceso seleccionado
        proc_data = df_proc[df_proc['radicado'] == seleccion].iloc[0]
        id_actual = int(proc_data['id_unico'])
        
        st.divider()
        col1, col2, col3 = st.columns(3)
        col1.metric("📅 Radicado", proc_data['radicado'])
        col2.metric("🚀 Fase Actual", proc_data['fase_actual'])
        col3.metric("📈 Progreso", f"{proc_data['progreso']}%")
        
        st.divider()

        # --- GESTOR DE FASES ---
        df_times = pd.DataFrame(w_time.get_all_records())
        df_steps = pd.DataFrame(w_steps.get_all_records())

        for fase_nombre, info in FASES_PROCESO.items():
            with st.expander(f"📂 {fase_nombre}", expanded=(fase_nombre == proc_data['fase_actual'])):
                
                # A. Lógica del Cronómetro
                # Buscar datos de tiempo para este proceso y fase
                tiempo_row = df_times[(df_times['id_unico'] == id_actual) & (df_times['fase'] == fase_nombre)]
                
                tiempo_acumulado = 0.0
                estado_timer = "Stop"
                ultimo_inicio = 0.0
                
                if not tiempo_row.empty:
                    tiempo_acumulado = float(tiempo_row.iloc[0]['tiempo_acumulado'])
                    estado_timer = tiempo_row.iloc[0]['estado_timer']
                    ultimo_inicio = float(tiempo_row.iloc[0]['ultimo_inicio'])

                # Calcular tiempo real si está corriendo
                tiempo_mostrar = tiempo_acumulado
                if estado_timer == "Running":
                    tiempo_mostrar += (time.time() - ultimo_inicio)
                    # Auto-refresh para ver el cronómetro andar
                    time.sleep(1) 
                    st.rerun()

                c1, c2, c3 = st.columns([2,1,1])
                c1.markdown(f"⏱️ **Tiempo invertido:** `{formatear_tiempo(tiempo_mostrar)}`")
                
                # Botones de control (Play/Pause)
                if estado_timer == "Stop":
                    if c2.button("▶️ Iniciar", key=f"start_{fase_nombre}"):
                        # Si no existe fila, crearla, si existe actualizar
                        cell = w_time.find(str(id_actual)) # Búsqueda simplificada
                        # Lógica robusta de actualización:
                        if tiempo_row.empty:
                            w_time.append_row([id_actual, fase_nombre, 0.0, time.time(), "Running"])
                        else:
                            # Encontrar la fila exacta (esto requiere filtro en GSheets, simplificamos borrando y agregando para evitar complejidad de índices)
                            # Para producción: usar row index. Aquí usaremos lógica de append simple y limpieza periódica o filtrado
                            # MÉTODO SEGURO: Usar celdas específicas. (Simplificado para este ejemplo: Borrar fila vieja y poner nueva)
                            row_index = tiempo_row.index[0] + 2 # +2 por header y 0-index
                            w_time.update_cell(row_index, 4, time.time()) # Actualizar ultimo_inicio
                            w_time.update_cell(row_index, 5, "Running") # Actualizar estado
                        st.rerun()
                else:
                    if c2.button("⏸️ Pausar", key=f"pause_{fase_nombre}"):
                        nuevo_acumulado = tiempo_acumulado + (time.time() - ultimo_inicio)
                        row_index = tiempo_row.index[0] + 2
                        w_time.update_cell(row_index, 3, nuevo_acumulado)
                        w_time.update_cell(row_index, 5, "Stop")
                        st.rerun()

                # B. Checklist de Pasos
                st.markdown("---")
                pasos_fase = info['pasos']
                
                # Filtrar pasos guardados
                pasos_guardados = df_steps[(df_steps['id_unico'] == id_actual) & (df_steps['fase'] == fase_nombre)]
                indices_completados = pasos_guardados['paso_index'].tolist()

                completed_count = 0
                for i, paso_txt in enumerate(pasos_fase):
                    check_key = f"chk_{id_actual}_{fase_nombre}_{i}"
                    is_checked = i in indices_completados
                    
                    if st.checkbox(paso_txt, value=is_checked, key=check_key):
                        completed_count += 1
                        if not is_checked:
                            # Guardar nuevo check en Nube
                            w_steps.append_row([id_actual, fase_nombre, i, "TRUE", str(datetime.now())])
                            st.rerun()
                    else:
                        if is_checked:
                            # Si se desmarca, habría que borrar de la hoja (complejo en gspread simple)
                            # Por ahora, advertimos:
                            st.warning("Para desmarcar, contacta al admin (o borra en el Excel).")

                # Actualizar Progreso General
                if len(pasos_fase) > 0:
                    avance = (completed_count / len(pasos_fase)) * 100
                    # (Aquí se podría actualizar la celda de progreso en w_proc)

if __name__ == "__main__":
    main()