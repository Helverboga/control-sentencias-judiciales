import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import json
import os
import shutil
import zipfile
from io import BytesIO

# Verificar e instalar dependencias necesarias
try:
    import openpyxl
except ImportError:
    st.error("⚠️ **Dependencia faltante**: Se necesita instalar openpyxl para la funcionalidad de Excel.")
    st.code("pip install openpyxl", language="bash")
    st.info("💡 Ejecuta el comando de arriba en tu terminal y reinicia la aplicación.")

# Configuración de la página
st.set_page_config(
    page_title="Control de Sentencias Judiciales",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados
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
    .step-item {
        background-color: white;
        padding: 10px;
        margin: 5px 0;
        border-radius: 5px;
        border-left: 3px solid #d4a574;
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

# Definición de las fases y pasos
FASES_PROCESO = {
    "I. Fase Propedéutica": {
        "tiempo_estimado": "Variable",
        "tiempo_limite_dias": None,  # Sin límite fijo
        "descripcion": "Completar cuando reciba el proyecto de auto de pruebas",
        "pasos": [
            "01) Copiar y pegar 0.Kit",
            "02) Cambiar nombre a 0. Kit", 
            "03) Crear carpeta en el mes correspondiente",
            "04) Descargar expediente digital e introducirlo en 01 y 02",
            "05) Aprovisionar de herramientas la carpeta",
            "06) Editar e imprimir",
            "07) Índice del expediente",
            "08) Foto del proceso",
            "09) Estructurar piezas procesales",
            "10) Reporte de pruebas",
            "11) Hago el fáctum",
            "12) Elaboro el auto de pruebas",
            "13) Comparo con auto de pruebas recibido, corrijo, y envío a notificación"
        ]
    },
    "II. Fase Lectura del Expediente": {
        "tiempo_estimado": "0.5 días",
        "tiempo_limite_dias": 0.5,
        "descripcion": "Agotar en medio día",
        "pasos": [
            "01) Lectura completa y comprensiva del expediente",
            "02) Identificación de puntos clave",
            "03) Toma de notas relevantes"
        ]
    },
    "III. Fase Elaboración de la Sentencia": {
        "tiempo_estimado": "5 días hábiles",
        "tiempo_limite_dias": 5.0,
        "descripcion": "Elaboración completa de la sentencia",
        "pasos": [
            "01) Empiezo a escribirla (elijo modelo, guardo y rotulo)",
            "02) Sintetizo los escritos fundamentales de las partes",
            "03) Agrego al borrador la síntesis",
            "04) Hago la investigación jurídica y resintetizo el litigio",
            "05) Alojo las investigaciones a la carpeta insumo",
            "06) Hago una investigación jurisprudencial de los temas debatidos",
            "07) Valoro individualmente y en conjunto las pruebas del plenario",
            "08) Elaboro las 6 etapas de la sentencia oral de manera escalonada",
            "09) Enriquezco jurisprudencialmente el proyecto",
            "10) Guardo el proyecto de fallo en la carpeta del proceso"
        ]
    },
    "IV. Fase Preparación Inteligente de la Audiencia": {
        "tiempo_estimado": "2 días",
        "tiempo_limite_dias": 2.0,
        "descripcion": "Preparación para audiencia",
        "pasos": [
            "01) Opero conforme el algoritmo",
            "02) Creo los presupuestos procesales y sustanciales del proceso",
            "03) Creo la capa",
            "04) Control de asistencia",
            "05) Elijo y hago el roteiro"
        ]
    }
}

# Funciones de base de datos
def init_database():
    """Inicializa la base de datos SQLite"""
    conn = sqlite3.connect('sentencias.db')
    cursor = conn.cursor()
    
    # Tabla de procesos
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS procesos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_proceso TEXT UNIQUE NOT NULL,
        fecha_inicio DATETIME DEFAULT CURRENT_TIMESTAMP,
        estado TEXT DEFAULT 'Activo',
        fase_actual TEXT DEFAULT 'I. Fase Propedéutica',
        progreso_total REAL DEFAULT 0.0,
        tiempo_total_segundos REAL DEFAULT 0.0
    )
    ''')
    
    # Tabla de seguimiento de fases
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS seguimiento_fases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        proceso_id INTEGER,
        fase TEXT,
        paso_actual INTEGER DEFAULT 0,
        tiempo_inicio DATETIME,
        tiempo_fin DATETIME,
        tiempo_pausa DATETIME,
        tiempo_total_segundos REAL DEFAULT 0,
        tiempo_pausado_segundos REAL DEFAULT 0,
        estado_cronometro TEXT DEFAULT 'Detenido',
        completada BOOLEAN DEFAULT FALSE,
        FOREIGN KEY (proceso_id) REFERENCES procesos (id)
    )
    ''')
    
    # Tabla de pasos completados
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pasos_completados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        proceso_id INTEGER,
        fase TEXT,
        paso_numero INTEGER,
        completado BOOLEAN DEFAULT FALSE,
        fecha_completado DATETIME,
        FOREIGN KEY (proceso_id) REFERENCES procesos (id)
    )
    ''')
    
    # Tabla de cronómetro en sesión
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS cronometro_sesion (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        proceso_id INTEGER,
        fase TEXT,
        tiempo_inicio_sesion DATETIME,
        tiempo_acumulado_anterior REAL DEFAULT 0,
        activo BOOLEAN DEFAULT FALSE,
        FOREIGN KEY (proceso_id) REFERENCES procesos (id)
    )
    ''')
    
    # Tabla de límites personalizados
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS limites_personalizados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        proceso_id INTEGER,
        fase TEXT,
        limite_dias REAL,
        FOREIGN KEY (proceso_id) REFERENCES procesos (id),
        UNIQUE(proceso_id, fase)
    )
    ''')
    
    conn.commit()
    conn.close()

# Función para formatear tiempo
def formatear_tiempo(segundos):
    """Formatea segundos a formato legible"""
    if segundos < 60:
        return f"{int(segundos)}s"
    elif segundos < 3600:
        minutos = int(segundos // 60)
        segundos_rest = int(segundos % 60)
        return f"{minutos}m {segundos_rest}s"
    elif segundos < 86400:
        horas = int(segundos // 3600)
        minutos = int((segundos % 3600) // 60)
        return f"{horas}h {minutos}m"
    else:
        dias = int(segundos // 86400)
        horas = int((segundos % 86400) // 3600)
        return f"{dias}d {horas}h"

def crear_proceso(numero_proceso):
    """Crea un nuevo proceso en la base de datos"""
    conn = sqlite3.connect('sentencias.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('INSERT INTO procesos (numero_proceso) VALUES (?)', (numero_proceso,))
        proceso_id = cursor.lastrowid
        
        # Crear entradas para todas las fases
        for fase in FASES_PROCESO.keys():
            cursor.execute('''
            INSERT INTO seguimiento_fases (proceso_id, fase) 
            VALUES (?, ?)
            ''', (proceso_id, fase))
            
            # Crear entradas para todos los pasos de cada fase
            for i, paso in enumerate(FASES_PROCESO[fase]["pasos"], 1):
                cursor.execute('''
                INSERT INTO pasos_completados (proceso_id, fase, paso_numero)
                VALUES (?, ?, ?)
                ''', (proceso_id, fase, i))
        
        conn.commit()
        return True, "Proceso creado exitosamente"
    except sqlite3.IntegrityError:
        return False, "Ya existe un proceso con ese número"
    finally:
        conn.close()

def obtener_procesos_activos():
    """Obtiene todos los procesos activos"""
    conn = sqlite3.connect('sentencias.db')
    df = pd.read_sql_query('''
    SELECT id, numero_proceso, fecha_inicio, fase_actual, progreso_total
    FROM procesos 
    WHERE estado = 'Activo'
    ORDER BY fecha_inicio DESC
    ''', conn)
    conn.close()
    return df

def obtener_proceso_detalle(proceso_id):
    """Obtiene el detalle completo de un proceso"""
    conn = sqlite3.connect('sentencias.db')
    cursor = conn.cursor()
    
    # Información del proceso
    cursor.execute('SELECT * FROM procesos WHERE id = ?', (proceso_id,))
    proceso = cursor.fetchone()
    
    # Información de fases
    cursor.execute('SELECT * FROM seguimiento_fases WHERE proceso_id = ?', (proceso_id,))
    fases = cursor.fetchall()
    
    # Información de pasos completados
    cursor.execute('SELECT * FROM pasos_completados WHERE proceso_id = ?', (proceso_id,))
    pasos = cursor.fetchall()
    
    conn.close()
    return proceso, fases, pasos

def actualizar_progreso_paso(proceso_id, fase, paso_numero, completado):
    """Actualiza el estado de completado de un paso"""
    conn = sqlite3.connect('sentencias.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    UPDATE pasos_completados 
    SET completado = ?, fecha_completado = CURRENT_TIMESTAMP
    WHERE proceso_id = ? AND fase = ? AND paso_numero = ?
    ''', (completado, proceso_id, fase, paso_numero))
    
    # Actualizar progreso total del proceso
    cursor.execute('''
    SELECT COUNT(*) as total, 
           SUM(CASE WHEN completado THEN 1 ELSE 0 END) as completados
    FROM pasos_completados 
    WHERE proceso_id = ?
    ''', (proceso_id,))
    
    total, completados = cursor.fetchone()
    progreso = (completados / total) * 100 if total > 0 else 0
    
    cursor.execute('UPDATE procesos SET progreso_total = ? WHERE id = ?', 
                  (progreso, proceso_id))
    
    conn.commit()
    conn.close()
    return progreso

# Funciones del cronómetro
def iniciar_cronometro_fase(proceso_id, fase):
    """Inicia el cronómetro para una fase específica"""
    conn = sqlite3.connect('sentencias.db')
    cursor = conn.cursor()
    
    # Pausar cualquier cronómetro activo de este proceso
    cursor.execute('''
    UPDATE cronometro_sesion 
    SET activo = FALSE 
    WHERE proceso_id = ? AND activo = TRUE
    ''', (proceso_id,))
    
    # Verificar si ya existe una entrada para esta fase
    cursor.execute('''
    SELECT id, tiempo_acumulado_anterior FROM cronometro_sesion 
    WHERE proceso_id = ? AND fase = ?
    ''', (proceso_id, fase))
    
    resultado = cursor.fetchone()
    ahora = datetime.now().isoformat()
    
    if resultado:
        # Actualizar entrada existente
        cursor.execute('''
        UPDATE cronometro_sesion 
        SET tiempo_inicio_sesion = ?, activo = TRUE
        WHERE proceso_id = ? AND fase = ?
        ''', (ahora, proceso_id, fase))
    else:
        # Crear nueva entrada
        cursor.execute('''
        INSERT INTO cronometro_sesion (proceso_id, fase, tiempo_inicio_sesion, activo)
        VALUES (?, ?, ?, TRUE)
        ''', (proceso_id, fase, ahora))
    
    # Actualizar estado en seguimiento_fases
    cursor.execute('''
    UPDATE seguimiento_fases 
    SET estado_cronometro = 'Activo', tiempo_inicio = COALESCE(tiempo_inicio, ?)
    WHERE proceso_id = ? AND fase = ?
    ''', (ahora, proceso_id, fase))
    
    conn.commit()
    conn.close()

def pausar_cronometro_fase(proceso_id, fase):
    """Pausa el cronómetro para una fase específica"""
    conn = sqlite3.connect('sentencias.db')
    cursor = conn.cursor()
    
    # Obtener tiempo de inicio de la sesión actual
    cursor.execute('''
    SELECT tiempo_inicio_sesion, tiempo_acumulado_anterior 
    FROM cronometro_sesion 
    WHERE proceso_id = ? AND fase = ? AND activo = TRUE
    ''', (proceso_id, fase))
    
    resultado = cursor.fetchone()
    if resultado:
        inicio_sesion, tiempo_anterior = resultado
        inicio_dt = datetime.fromisoformat(inicio_sesion)
        tiempo_sesion = (datetime.now() - inicio_dt).total_seconds()
        nuevo_tiempo_total = (tiempo_anterior or 0) + tiempo_sesion
        
        # Actualizar tiempo acumulado y desactivar
        cursor.execute('''
        UPDATE cronometro_sesion 
        SET tiempo_acumulado_anterior = ?, activo = FALSE
        WHERE proceso_id = ? AND fase = ?
        ''', (nuevo_tiempo_total, proceso_id, fase))
        
        # Actualizar en seguimiento_fases
        cursor.execute('''
        UPDATE seguimiento_fases 
        SET estado_cronometro = 'Pausado', tiempo_total_segundos = ?
        WHERE proceso_id = ? AND fase = ?
        ''', (nuevo_tiempo_total, proceso_id, fase))
    
    conn.commit()
    conn.close()

def finalizar_cronometro_fase(proceso_id, fase):
    """Finaliza el cronómetro para una fase específica"""
    pausar_cronometro_fase(proceso_id, fase)
    
    conn = sqlite3.connect('sentencias.db')
    cursor = conn.cursor()
    
    # Marcar como finalizado
    cursor.execute('''
    UPDATE seguimiento_fases 
    SET estado_cronometro = 'Finalizado', tiempo_fin = ?, completada = TRUE
    WHERE proceso_id = ? AND fase = ?
    ''', (datetime.now().isoformat(), proceso_id, fase))
    
    # Actualizar fase actual del proceso a la siguiente fase
    fases_lista = list(FASES_PROCESO.keys())
    try:
        indice_actual = fases_lista.index(fase)
        if indice_actual < len(fases_lista) - 1:
            siguiente_fase = fases_lista[indice_actual + 1]
            cursor.execute('''
            UPDATE procesos 
            SET fase_actual = ?
            WHERE id = ?
            ''', (siguiente_fase, proceso_id))
    except ValueError:
        pass
    
    conn.commit()
    conn.close()

def obtener_tiempo_actual_fase(proceso_id, fase):
    """Obtiene el tiempo actual transcurrido en una fase"""
    conn = sqlite3.connect('sentencias.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT tiempo_inicio_sesion, tiempo_acumulado_anterior, activo 
    FROM cronometro_sesion 
    WHERE proceso_id = ? AND fase = ?
    ''', (proceso_id, fase))
    
    resultado = cursor.fetchone()
    conn.close()
    
    if not resultado:
        return 0, False
    
    inicio_sesion, tiempo_anterior, activo = resultado
    tiempo_total = tiempo_anterior or 0
    
    if activo and inicio_sesion:
        inicio_dt = datetime.fromisoformat(inicio_sesion)
        tiempo_sesion = (datetime.now() - inicio_dt).total_seconds()
        tiempo_total += tiempo_sesion
    
    return tiempo_total, bool(activo)

# Funciones del Sistema de Alertas
def calcular_estado_alerta(tiempo_segundos, limite_dias):
    """Calcula el estado de alerta basado en el tiempo transcurrido"""
    if limite_dias is None:
        return "sin_limite", "⚪", "#6c757d"  # Sin límite
    
    limite_segundos = limite_dias * 24 * 3600
    porcentaje_usado = (tiempo_segundos / limite_segundos) * 100
    
    if porcentaje_usado < 60:
        return "normal", "🟢", "#28a745"  # Verde - Normal
    elif porcentaje_usado < 80:
        return "precaucion", "🟡", "#ffc107"  # Amarillo - Precaución
    elif porcentaje_usado < 100:
        return "advertencia", "🟠", "#fd7e14"  # Naranja - Advertencia
    else:
        return "critico", "🔴", "#dc3545"  # Rojo - Crítico

def obtener_procesos_con_alertas():
    """Obtiene todos los procesos activos con información de alertas"""
    conn = sqlite3.connect('sentencias.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT p.id, p.numero_proceso, p.fase_actual, p.progreso_total,
           sf.fase, sf.tiempo_total_segundos, sf.completada,
           cs.tiempo_acumulado_anterior, cs.activo, cs.tiempo_inicio_sesion,
           lp.limite_dias as limite_personalizado
    FROM procesos p
    LEFT JOIN seguimiento_fases sf ON p.id = sf.proceso_id
    LEFT JOIN cronometro_sesion cs ON p.id = cs.proceso_id AND sf.fase = cs.fase
    LEFT JOIN limites_personalizados lp ON p.id = lp.proceso_id AND sf.fase = lp.fase
    WHERE p.estado = 'Activo'
    ORDER BY p.id, sf.fase
    ''')
    
    resultados = cursor.fetchall()
    conn.close()
    
    procesos_alertas = {}
    
    for resultado in resultados:
        proceso_id, numero_proceso, fase_actual, progreso_total, fase, tiempo_sf, completada, tiempo_cs, activo, inicio_sesion, limite_personalizado = resultado
        
        if proceso_id not in procesos_alertas:
            procesos_alertas[proceso_id] = {
                'numero_proceso': numero_proceso,
                'fase_actual': fase_actual,
                'progreso_total': progreso_total,
                'fases': {},
                'alertas_criticas': 0,
                'alertas_advertencia': 0,
                'cronometros_activos': 0
            }
        
        if fase:
            # Calcular tiempo real de la fase
            tiempo_real = tiempo_cs if tiempo_cs is not None else (tiempo_sf or 0)
            
            if activo and inicio_sesion:
                try:
                    inicio_dt = datetime.fromisoformat(inicio_sesion)
                    tiempo_sesion = (datetime.now() - inicio_dt).total_seconds()
                    tiempo_real += tiempo_sesion
                except:
                    pass
            
            # Obtener límite de tiempo (personalizado o por defecto)
            limite_dias = limite_personalizado if limite_personalizado is not None else FASES_PROCESO.get(fase, {}).get('tiempo_limite_dias')
            
            # Calcular estado de alerta
            estado, emoji, color = calcular_estado_alerta(tiempo_real, limite_dias)
            
            procesos_alertas[proceso_id]['fases'][fase] = {
                'tiempo_segundos': tiempo_real,
                'limite_dias': limite_dias,
                'limite_personalizado': limite_personalizado is not None,
                'completada': bool(completada),
                'activo': bool(activo),
                'estado_alerta': estado,
                'emoji_alerta': emoji,
                'color_alerta': color,
                'porcentaje_tiempo': (tiempo_real / (limite_dias * 24 * 3600 * 1.0)) * 100 if limite_dias else 0
            }
            
            # Contar alertas
            if estado == 'critico':
                procesos_alertas[proceso_id]['alertas_criticas'] += 1
            elif estado in ['advertencia', 'precaucion']:
                procesos_alertas[proceso_id]['alertas_advertencia'] += 1
            
            if activo:
                procesos_alertas[proceso_id]['cronometros_activos'] += 1
    
    return procesos_alertas

def mostrar_alerta_fase(fase, tiempo_segundos, limite_dias, estado_alerta, emoji_alerta, color_alerta, es_personalizado=False):
    """Muestra la alerta visual de una fase"""
    if limite_dias is None:
        return f"{emoji_alerta} Sin límite de tiempo"
    
    tiempo_limite_segundos = limite_dias * 24 * 3600
    porcentaje = (tiempo_segundos / tiempo_limite_segundos) * 100
    tiempo_restante_segundos = max(0, tiempo_limite_segundos - tiempo_segundos)
    
    sufijo_personalizado = " (límite personalizado)" if es_personalizado else ""
    
    if estado_alerta == "normal":
        return f"{emoji_alerta} Tiempo normal ({porcentaje:.1f}% usado){sufijo_personalizado}"
    elif estado_alerta == "precaucion":
        return f"{emoji_alerta} **Atención**: {formatear_tiempo(tiempo_restante_segundos)} restantes{sufijo_personalizado}"
    elif estado_alerta == "advertencia":
        return f"{emoji_alerta} **ADVERTENCIA**: ¡Solo {formatear_tiempo(tiempo_restante_segundos)} restantes!{sufijo_personalizado}"
    else:  # crítico
        tiempo_excedido = tiempo_segundos - tiempo_limite_segundos
        return f"{emoji_alerta} **¡TIEMPO EXCEDIDO!** Por {formatear_tiempo(tiempo_excedido)}{sufijo_personalizado}"

def obtener_resumen_alertas():
    """Obtiene un resumen de todas las alertas del sistema"""
    procesos = obtener_procesos_con_alertas()
    
    total_criticas = sum(p['alertas_criticas'] for p in procesos.values())
    total_advertencias = sum(p['alertas_advertencia'] for p in procesos.values())
    total_cronometros = sum(p['cronometros_activos'] for p in procesos.values())
    
    procesos_criticos = [p for p in procesos.values() if p['alertas_criticas'] > 0]
    procesos_advertencia = [p for p in procesos.values() if p['alertas_advertencia'] > 0]
    
    return {
        'total_criticas': total_criticas,
        'total_advertencias': total_advertencias,
        'total_cronometros': total_cronometros,
        'procesos_criticos': procesos_criticos,
        'procesos_advertencia': procesos_advertencia,
        'procesos_datos': procesos
    }

# Funciones del Sistema de Backup
def crear_carpeta_backups():
    """Crea la carpeta de backups si no existe"""
    if not os.path.exists('backups'):
        os.makedirs('backups')
    return 'backups'

def realizar_backup_automatico():
    """Realiza un backup automático de la base de datos"""
    try:
        carpeta_backups = crear_carpeta_backups()
        fecha_actual = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_backup = f"sentencias_backup_{fecha_actual}.db"
        ruta_backup = os.path.join(carpeta_backups, nombre_backup)
        
        # Copiar la base de datos actual
        if os.path.exists('sentencias.db'):
            shutil.copy2('sentencias.db', ruta_backup)
            
            # Limpiar backups antiguos (mantener solo los últimos 7)
            limpiar_backups_antiguos(carpeta_backups)
            
            return True, ruta_backup
        return False, "No existe base de datos para respaldar"
    except Exception as e:
        return False, f"Error en backup: {str(e)}"

def limpiar_backups_antiguos(carpeta_backups, mantener=7):
    """Mantiene solo los backups más recientes"""
    try:
        archivos_backup = [f for f in os.listdir(carpeta_backups) if f.startswith('sentencias_backup_') and f.endswith('.db')]
        archivos_backup.sort(reverse=True)  # Más recientes primero
        
        # Eliminar archivos antiguos
        for archivo_antiguo in archivos_backup[mantener:]:
            os.remove(os.path.join(carpeta_backups, archivo_antiguo))
    except Exception as e:
        print(f"Error limpiando backups: {e}")

def obtener_lista_backups():
    """Obtiene la lista de backups disponibles"""
    try:
        carpeta_backups = crear_carpeta_backups()
        archivos_backup = [f for f in os.listdir(carpeta_backups) if f.startswith('sentencias_backup_') and f.endswith('.db')]
        
        backups_info = []
        for archivo in archivos_backup:
            ruta_completa = os.path.join(carpeta_backups, archivo)
            fecha_modificacion = os.path.getmtime(ruta_completa)
            fecha_legible = datetime.fromtimestamp(fecha_modificacion).strftime('%Y-%m-%d %H:%M:%S')
            tamano = os.path.getsize(ruta_completa)
            
            backups_info.append({
                'archivo': archivo,
                'fecha': fecha_legible,
                'tamano_kb': round(tamano / 1024, 2),
                'ruta': ruta_completa
            })
        
        # Ordenar por fecha más reciente primero
        backups_info.sort(key=lambda x: x['fecha'], reverse=True)
        return backups_info
    except Exception as e:
        return []

def restaurar_desde_backup(ruta_backup):
    """Restaura la base de datos desde un backup"""
    try:
        if os.path.exists(ruta_backup):
            # Crear backup de la base actual antes de restaurar
            realizar_backup_automatico()
            
            # Restaurar desde backup
            shutil.copy2(ruta_backup, 'sentencias.db')
            return True, "Base de datos restaurada exitosamente"
        else:
            return False, "Archivo de backup no encontrado"
    except Exception as e:
        return False, f"Error restaurando: {str(e)}"

def verificar_backup_diario():
    """Verifica si ya se hizo backup hoy, si no lo crea"""
    try:
        carpeta_backups = crear_carpeta_backups()
        hoy = datetime.now().strftime("%Y%m%d")
        
        # Buscar si ya existe un backup de hoy
        archivos_hoy = [f for f in os.listdir(carpeta_backups) if hoy in f]
        
        if not archivos_hoy:
            # No hay backup de hoy, crear uno
            return realizar_backup_automatico()
        
        return True, "Backup diario ya existe"
    except Exception as e:
        return False, f"Error verificando backup diario: {str(e)}"

def exportar_datos_excel():
    """Exporta todos los datos a un archivo Excel"""
    try:
        # Verificar que openpyxl esté disponible
        try:
            import openpyxl
        except ImportError:
            return False, None, "Error: openpyxl no está instalado. Ejecute: pip install openpyxl"
        
        conn = sqlite3.connect('sentencias.db')
        
        # Crear un buffer para el archivo Excel
        buffer = BytesIO()
        
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            # Exportar procesos
            df_procesos = pd.read_sql_query('''
            SELECT 
                numero_proceso as "Número de Proceso",
                fecha_inicio as "Fecha de Inicio", 
                estado as "Estado",
                fase_actual as "Fase Actual",
                ROUND(progreso_total, 2) as "Progreso (%)",
                ROUND(tiempo_total_segundos/3600, 2) as "Tiempo Total (horas)"
            FROM procesos 
            ORDER BY fecha_inicio DESC
            ''', conn)
            
            if not df_procesos.empty:
                df_procesos.to_excel(writer, sheet_name='Procesos', index=False)
            else:
                # Si no hay datos, crear una hoja con mensaje
                df_vacio = pd.DataFrame({'Mensaje': ['No hay procesos registrados']})
                df_vacio.to_excel(writer, sheet_name='Procesos', index=False)
            
            # Crear hoja de estadísticas detalladas
            estadisticas = []
            
            # Estadísticas generales
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM procesos WHERE estado = "Activo"')
            procesos_activos = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM procesos')
            total_procesos = cursor.fetchone()[0]
            
            cursor.execute('SELECT AVG(progreso_total) FROM procesos WHERE estado = "Activo"')
            progreso_promedio = cursor.fetchone()[0] or 0
            
            cursor.execute('SELECT COUNT(*) FROM cronometro_sesion WHERE activo = TRUE')
            cronometros_activos = cursor.fetchone()[0]
            
            estadisticas.extend([
                ['Total de Procesos', total_procesos],
                ['Procesos Activos', procesos_activos],
                ['Procesos Completados', total_procesos - procesos_activos],
                ['Progreso Promedio (%)', round(progreso_promedio, 2)],
                ['Cronómetros Activos', cronometros_activos],
                ['Fecha de Exportación', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
                ['Versión de la Aplicación', 'Control de Sentencias v3.0']
            ])
            
            df_stats = pd.DataFrame(estadisticas, columns=['Métrica', 'Valor'])
            df_stats.to_excel(writer, sheet_name='Estadísticas', index=False)
        
        conn.close()
        buffer.seek(0)
        
        return True, buffer, "exportacion_sentencias.xlsx"
        
    except Exception as e:
        return False, None, f"Error exportando: {str(e)}"

# Funciones de las interfaces principales
def mostrar_dashboard():
    """Muestra el dashboard principal"""
    st.header("📊 Dashboard - Resumen General")
    
    # Obtener procesos activos y resumen de alertas
    procesos_df = obtener_procesos_activos()
    resumen_alertas = obtener_resumen_alertas()
    
    if procesos_df.empty:
        st.info("👋 ¡Bienvenido! No hay procesos activos. Cree su primer proceso usando el menú lateral.")
        return
    
    # SISTEMA DE ALERTAS PROMINENTE
    if resumen_alertas['total_criticas'] > 0 or resumen_alertas['total_advertencias'] > 0:
        st.markdown("---")
        st.markdown("## 🚨 **ALERTAS DEL SISTEMA**")
        
        # Alertas críticas
        if resumen_alertas['total_criticas'] > 0:
            st.error(f"🔴 **{resumen_alertas['total_criticas']} ALERTA(S) CRÍTICA(S)** - ¡Tiempo excedido!")
            
            with st.expander("🔴 Ver Procesos Críticos", expanded=True):
                for proceso in resumen_alertas['procesos_criticos']:
                    st.markdown(f"**📋 {proceso['numero_proceso']}**")
                    for fase, info in proceso['fases'].items():
                        if info['estado_alerta'] == 'critico':
                            limite_dias = info['limite_dias']
                            tiempo_excedido = info['tiempo_segundos'] - (limite_dias * 24 * 3600)
                            st.markdown(f"  - {fase}: ⚠️ **Excedido por {formatear_tiempo(tiempo_excedido)}**")
        
        # Alertas de advertencia
        if resumen_alertas['total_advertencias'] > 0:
            st.warning(f"🟡 **{resumen_alertas['total_advertencias']} Advertencia(s)** - Acercándose al límite")
        
        st.markdown("---")
    
    # Métricas principales (actualizadas con alertas)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        color = "#dc3545" if resumen_alertas['total_criticas'] > 0 else "#1f4e79"
        st.markdown(f'''
        <div class="metric-card" style="background: linear-gradient(135deg, {color}, {color}dd);">
            <h3>📋 Procesos Activos</h3>
            <h2>{len(procesos_df)}</h2>
        </div>
        ''', unsafe_allow_html=True)
    
    with col2:
        progreso_promedio = procesos_df['progreso_total'].mean()
        st.markdown(f'''
        <div class="metric-card">
            <h3>📈 Progreso Promedio</h3>
            <h2>{progreso_promedio:.1f}%</h2>
        </div>
        ''', unsafe_allow_html=True)
    
    with col3:
        color = "#ffc107" if resumen_alertas['total_advertencias'] > 0 else "#1f4e79"
        st.markdown(f'''
        <div class="metric-card" style="background: linear-gradient(135deg, {color}, {color}dd);">
            <h3>🚨 Alertas Activas</h3>
            <h2>{resumen_alertas['total_criticas'] + resumen_alertas['total_advertencias']}</h2>
        </div>
        ''', unsafe_allow_html=True)
    
    with col4:
        st.markdown(f'''
        <div class="metric-card">
            <h3>🔄 Cronómetros Activos</h3>
            <h2>{resumen_alertas['total_cronometros']}</h2>
        </div>
        ''', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Información de cronómetros activos con alertas
    if resumen_alertas['total_cronometros'] > 0:
        st.subheader("⏱️ Cronómetros en Ejecución")
        
        for proceso_id, proceso_data in resumen_alertas['procesos_datos'].items():
            if proceso_data['cronometros_activos'] > 0:
                for fase, info in proceso_data['fases'].items():
                    if info['activo']:
                        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                        
                        with col1:
                            st.write(f"📋 **{proceso_data['numero_proceso']}**")
                        with col2:
                            st.write(f"🎯 {fase}")
                        with col3:
                            tiempo_formateado = formatear_tiempo(info['tiempo_segundos'])
                            st.write(f"⏱️ {tiempo_formateado}")
                        with col4:
                            st.markdown(f"**{info['emoji_alerta']}**")
                        
                        # Mostrar mensaje de alerta si es necesario
                        if info['estado_alerta'] in ['advertencia', 'critico']:
                            mensaje_alerta_completo = mostrar_alerta_fase(
                                fase, info['tiempo_segundos'], info['limite_dias'],
                                info['estado_alerta'], info['emoji_alerta'], info['color_alerta'],
                                info.get('limite_personalizado', False)
                            )
                            st.markdown(f"**{mensaje_alerta_completo}**")
        
        st.markdown("---")
    
    # Gráfico de progreso general con alertas
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📊 Estado de Procesos con Alertas")
        
        if not procesos_df.empty:
            # Crear DataFrame con información de alertas para el gráfico
            datos_grafico = []
            for proceso_id, proceso_data in resumen_alertas['procesos_datos'].items():
                alertas_total = proceso_data['alertas_criticas'] + proceso_data['alertas_advertencia']
                color_barra = "Crítico" if proceso_data['alertas_criticas'] > 0 else \
                             "Advertencia" if proceso_data['alertas_advertencia'] > 0 else "Normal"
                
                datos_grafico.append({
                    'numero_proceso': proceso_data['numero_proceso'],
                    'progreso_total': proceso_data['progreso_total'],
                    'estado_alerta': color_barra,
                    'alertas_total': alertas_total
                })
            
            df_grafico = pd.DataFrame(datos_grafico)
            
            # Mapeo de colores para alertas
            color_map = {
                'Normal': '#28a745',
                'Advertencia': '#ffc107', 
                'Crítico': '#dc3545'
            }
            
            fig = px.bar(
                df_grafico,
                x='numero_proceso',
                y='progreso_total',
                title="Progreso y Estado de Alertas por Proceso",
                color='estado_alerta',
                color_discrete_map=color_map,
                hover_data=['alertas_total']
            )
            fig.update_layout(
                xaxis_title="Número de Proceso",
                yaxis_title="Progreso (%)",
                legend_title="Estado"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🔄 Controles")
        
        # Panel de control de alertas
        st.info("💡 Seleccione un proceso específico en 'Gestionar Procesos' para ver el detalle completo y controlar los cronómetros.")
        
        # Botón de actualización con indicador de estado
        if st.button("🔄 Actualizar Dashboard", key="refresh_dashboard"):
            st.rerun()
        
        # Estadísticas rápidas de alertas
        st.markdown("### 📊 Resumen de Alertas")
        if resumen_alertas['total_criticas'] > 0:
            st.metric("🔴 Críticas", resumen_alertas['total_criticas'])
        if resumen_alertas['total_advertencias'] > 0:
            st.metric("🟡 Advertencias", resumen_alertas['total_advertencias'])
        if resumen_alertas['total_cronometros'] > 0:
            st.metric("⏱️ Cronómetros", resumen_alertas['total_cronometros'])

def crear_nuevo_proceso():
    """Interfaz para crear un nuevo proceso"""
    st.header("➕ Crear Nuevo Proceso")
    
    with st.form("nuevo_proceso"):
        st.markdown("### 📝 Información del Proceso")
        numero_proceso = st.text_input(
            "Número de Proceso *",
            placeholder="Ej: 2024-00001",
            help="Ingrese el número único del proceso judicial"
        )
        
        st.markdown("### ℹ️ Información de las Fases")
        
        # Mostrar información de las fases con límites
        for fase, info in FASES_PROCESO.items():
            limite_mostrar = info["tiempo_estimado"]
            if info.get("tiempo_limite_dias"):
                limite_mostrar = f"{info['tiempo_limite_dias']} días"
            
            st.markdown(f'''
            <div class="phase-card">
                <h4>{fase}</h4>
                <p><strong>Tiempo límite:</strong> {limite_mostrar}</p>
                <p><strong>Descripción:</strong> {info["descripcion"]}</p>
                <p><strong>Pasos:</strong> {len(info["pasos"])} pasos a completar</p>
            </div>
            ''', unsafe_allow_html=True)
        
        submitted = st.form_submit_button("🔄 Crear Proceso", type="primary")
        
        if submitted:
            if numero_proceso.strip():
                # Crear el proceso
                exito, mensaje = crear_proceso(numero_proceso.strip())
                if exito:
                    st.success(f"✅ {mensaje}")
                    st.balloons()
                else:
                    st.error(f"❌ {mensaje}")
            else:
                st.error("❌ Por favor ingrese un número de proceso válido")

def gestionar_procesos():
    """Interfaz para gestionar procesos existentes"""
    st.header("📊 Gestión de Procesos")
    
    procesos_df = obtener_procesos_activos()
    
    if procesos_df.empty:
        st.info("📂 No hay procesos activos. Cree su primer proceso.")
        return
    
    # Selector de proceso
    proceso_seleccionado = st.selectbox(
        "Seleccione un proceso:",
        options=procesos_df['id'].tolist(),
        format_func=lambda x: f"{procesos_df[procesos_df['id']==x]['numero_proceso'].iloc[0]} - {procesos_df[procesos_df['id']==x]['progreso_total'].iloc[0]:.1f}% completado",
        key="selector_proceso"
    )
    
    if proceso_seleccionado:
        mostrar_detalle_proceso(proceso_seleccionado)

def mostrar_detalle_proceso(proceso_id):
    """Muestra el detalle completo de un proceso"""
    proceso, fases, pasos = obtener_proceso_detalle(proceso_id)
    
    if not proceso:
        st.error("❌ No se encontró el proceso")
        return
    
    # Obtener información de alertas para este proceso
    resumen_alertas = obtener_resumen_alertas()
    proceso_alertas = resumen_alertas['procesos_datos'].get(proceso_id, {})
    
    # Información del proceso con alertas
    st.markdown(f"### 📋 Proceso: {proceso[1]}")
    
    # Mostrar alertas del proceso si las hay
    if proceso_alertas.get('alertas_criticas', 0) > 0:
        st.error("🔴 **ESTE PROCESO TIENE ALERTAS CRÍTICAS** - ¡Tiempo excedido en una o más fases!")
    elif proceso_alertas.get('alertas_advertencia', 0) > 0:
        st.warning("🟡 **Este proceso tiene advertencias de tiempo** - Se está acercando a los límites")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📅 Fecha de Inicio", proceso[2][:10])
    with col2:
        st.metric("📊 Progreso Total", f"{proceso[5]:.1f}%")
    with col3:
        st.metric("🎯 Fase Actual", proceso[4])
    with col4:
        alertas_totales = proceso_alertas.get('alertas_criticas', 0) + proceso_alertas.get('alertas_advertencia', 0)
        color_alertas = "🔴" if proceso_alertas.get('alertas_criticas', 0) > 0 else \
                      "🟡" if proceso_alertas.get('alertas_advertencia', 0) > 0 else "🟢"
        st.metric("🚨 Alertas", f"{color_alertas} {alertas_totales}")
    
    # Barra de progreso general
    st.progress(proceso[5] / 100)
    
    # Auto-refresh para cronómetros activos
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🔄 Actualizar Cronómetros", key="refresh_timers"):
            st.rerun()
    with col2:
        if proceso_alertas.get('alertas_criticas', 0) > 0:
            st.markdown("🚨 **Refresh automático cada 5 segundos debido a alertas críticas**")
    
    st.markdown("---")
    
    # Mostrar cada fase con sus pasos, cronómetro y alertas
    for fase_nombre, fase_info in FASES_PROCESO.items():
        
        # Obtener información de alertas para esta fase
        fase_alertas = proceso_alertas.get('fases', {}).get(fase_nombre, {})
        estado_alerta = fase_alertas.get('estado_alerta', 'normal')
        emoji_alerta = fase_alertas.get('emoji_alerta', '⚪')
        color_alerta = fase_alertas.get('color_alerta', '#6c757d')
        
        # Color del expander basado en el estado de alerta
        expanded_default = estado_alerta in ['critico', 'advertencia'] or fase_nombre == proceso[4]
        
        with st.expander(f"{emoji_alerta} {fase_nombre} - {len(fase_info['pasos'])} pasos", expanded=expanded_default):
            
            # SISTEMA DE ALERTAS PARA LA FASE
            if fase_alertas.get('limite_dias') is not None:
                tiempo_fase = fase_alertas.get('tiempo_segundos', 0)
                limite_dias = fase_alertas.get('limite_dias')
                
                mensaje_alerta = mostrar_alerta_fase(
                    fase_nombre, tiempo_fase, limite_dias,
                    estado_alerta, emoji_alerta, color_alerta,
                    fase_alertas.get('limite_personalizado', False)
                )
                
                if estado_alerta == 'critico':
                    st.error(f"🚨 **TIEMPO CRÍTICO**: {mensaje_alerta}")
                elif estado_alerta == 'advertencia':
                    st.warning(f"⚠️ **ADVERTENCIA**: {mensaje_alerta}")
                elif estado_alerta == 'precaucion':
                    st.info(f"⚡ **PRECAUCIÓN**: {mensaje_alerta}")
                else:
                    st.success(f"✅ **Estado Normal**: {mensaje_alerta}")
            
            # Obtener tiempo actual y estado del cronómetro
            tiempo_actual, cronometro_activo = obtener_tiempo_actual_fase(proceso_id, fase_nombre)
            
            # Calcular progreso de la fase
            pasos_fase = [p for p in pasos if p[2] == fase_nombre]
            pasos_completados = len([p for p in pasos_fase if p[4]])
            progreso_fase = (pasos_completados / len(pasos_fase)) * 100 if pasos_fase else 0
            
            # Layout de la fase con cronómetro
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.metric(f"📊 Progreso de Pasos", f"{progreso_fase:.1f}%")
                st.progress(progreso_fase / 100)
            
            with col2:
                tiempo_formateado = formatear_tiempo(tiempo_actual)
                color_tiempo = "🟢" if cronometro_activo else "🔴" if tiempo_actual > 0 else "⚪"
                st.metric("⏱️ Tiempo Cronómetro", f"{color_tiempo} {tiempo_formateado}")
                
                # Mostrar estado del cronómetro
                if cronometro_activo:
                    st.success("🔄 Cronómetro ACTIVO")
                elif tiempo_actual > 0:
                    st.warning("⏸️ Cronómetro PAUSADO")
                else:
                    st.info("⏹️ No iniciado")
            
            with col3:
                st.markdown("**🎮 Controles de Cronómetro:**")
                
                # Botones de control del cronómetro
                col_btn1, col_btn2, col_btn3 = st.columns(3)
                
                with col_btn1:
                    if st.button("▶️", key=f"start_{proceso_id}_{fase_nombre}", 
                               help="Iniciar cronómetro"):
                        iniciar_cronometro_fase(proceso_id, fase_nombre)
                        st.rerun()
                
                with col_btn2:
                    if st.button("⏸️", key=f"pause_{proceso_id}_{fase_nombre}",
                               help="Pausar cronómetro"):
                        pausar_cronometro_fase(proceso_id, fase_nombre)
                        st.rerun()
                
                with col_btn3:
                    if st.button("⏹️", key=f"stop_{proceso_id}_{fase_nombre}",
                               help="Finalizar fase"):
                        finalizar_cronometro_fase(proceso_id, fase_nombre)
                        st.success(f"✅ Fase {fase_nombre} finalizada!")
                        st.rerun()
            
            st.markdown("---")
            
            # Mostrar cada paso
            st.markdown("**📋 Lista de Pasos:**")
            for i, paso_texto in enumerate(fase_info["pasos"], 1):
                # Buscar el estado del paso
                paso_actual = next((p for p in pasos_fase if p[3] == i), None)
                completado = paso_actual[4] if paso_actual else False
                
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    status_icon = "✅" if completado else "⏳"
                    st.markdown(f"{status_icon} **{paso_texto}**")
                
                with col2:
                    nuevo_estado = st.checkbox(
                        "✓",
                        value=completado,
                        key=f"paso_{proceso_id}_{fase_nombre}_{i}",
                        help="Marcar como completado"
                    )
                    
                    # Si cambió el estado, actualizar en la base de datos
                    if nuevo_estado != completado:
                        nuevo_progreso = actualizar_progreso_paso(proceso_id, fase_nombre, i, nuevo_estado)
                        st.rerun()
            
            st.markdown("<br>", unsafe_allow_html=True)

def mostrar_reportes():
    """Muestra reportes y estadísticas"""
    st.header("📈 Reportes y Estadísticas")
    
    procesos_df = obtener_procesos_activos()
    
    if procesos_df.empty:
        st.info("📊 No hay datos suficientes para generar reportes.")
        return
    
    # Pestañas para organizar los reportes
    tab1, tab2, tab3 = st.tabs(["📊 Progreso General", "⏱️ Análisis de Tiempos", "📋 Detalle de Procesos"])
    
    with tab1:
        # Distribución de progreso
        st.subheader("📊 Distribución de Progreso")
        
        ranges = ['0-20%', '21-40%', '41-60%', '61-80%', '81-100%']
        counts = [
            len(procesos_df[procesos_df['progreso_total'] <= 20]),
            len(procesos_df[(procesos_df['progreso_total'] > 20) & (procesos_df['progreso_total'] <= 40)]),
            len(procesos_df[(procesos_df['progreso_total'] > 40) & (procesos_df['progreso_total'] <= 60)]),
            len(procesos_df[(procesos_df['progreso_total'] > 60) & (procesos_df['progreso_total'] <= 80)]),
            len(procesos_df[procesos_df['progreso_total'] > 80])
        ]
        
        fig = px.pie(
            values=counts,
            names=ranges,
            title="Distribución de Procesos por Rango de Progreso",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.subheader("⏱️ Análisis de Tiempos por Fase")
        st.info("⏱️ Aún no hay datos de tiempo registrados. Inicie el cronómetro en alguna fase para ver estadísticas.")
    
    with tab3:
        # Tabla de procesos
        st.subheader("📋 Lista Detallada de Procesos")
        st.dataframe(
            procesos_df[['numero_proceso', 'fecha_inicio', 'fase_actual', 'progreso_total']],
            use_container_width=True
        )

def mostrar_sistema_backup():
    """Interfaz del sistema de backup y exportación"""
    st.header("💾 Sistema de Backup y Exportación")
    
    # Información del estado actual
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Verificar si existe la base de datos
        db_existe = os.path.exists('sentencias.db')
        db_tamano = os.path.getsize('sentencias.db') / 1024 if db_existe else 0  # KB
        st.metric("📁 Base de Datos", f"{'Existe' if db_existe else 'No existe'}")
        st.metric("💽 Tamaño", f"{db_tamano:.1f} KB")
    
    with col2:
        # Contar backups disponibles
        backups_lista = obtener_lista_backups()
        st.metric("🗂️ Backups Disponibles", len(backups_lista))
        if backups_lista:
            ultimo_backup = backups_lista[0]['fecha']
            st.metric("🕒 Último Backup", ultimo_backup)
    
    with col3:
        # Verificar backup de hoy
        hoy = datetime.now().strftime("%Y%m%d")
        backup_hoy = any(hoy in backup['archivo'] for backup in backups_lista)
        st.metric("📅 Backup de Hoy", "✅ Sí" if backup_hoy else "❌ No")
    
    st.markdown("---")
    
    # Pestañas del sistema de backup
    tab1, tab2 = st.tabs(["🔄 Crear Backup", "📊 Exportar Datos"])
    
    with tab1:
        st.subheader("🔄 Crear Nuevo Backup")
        
        st.info("💡 **Backup Automático**: La aplicación crea automáticamente un backup diario. También puedes crear backups manuales cuando quieras.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🆕 Crear Backup Manual", type="primary", help="Crea un backup inmediato de todos tus datos"):
                with st.spinner("Creando backup..."):
                    exito, resultado = realizar_backup_automatico()
                    
                    if exito:
                        st.success(f"✅ **Backup creado exitosamente!**")
                        st.success(f"📁 Guardado en: `{os.path.basename(resultado)}`")
                        st.balloons()
                    else:
                        st.error(f"❌ Error creando backup: {resultado}")
        
        with col2:
            st.markdown("**📊 ¿Qué incluye el backup?**")
            st.markdown("""
            - ✅ Todos los procesos
            - ✅ Cronómetros y tiempos
            - ✅ Pasos completados  
            - ✅ Límites personalizados
            - ✅ Configuraciones
            """)
    
    with tab2:
        st.subheader("📊 Exportar Datos")
        
        st.info("💡 Exporta todos tus datos a un archivo Excel profesional que puedes abrir en cualquier computadora.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📊 Exportar a Excel", type="primary", help="Genera un archivo Excel con todos los datos"):
                with st.spinner("Generando archivo Excel..."):
                    exito, buffer, nombre_archivo = exportar_datos_excel()
                    
                    if exito:
                        st.success("✅ **Archivo Excel generado exitosamente!**")
                        
                        # Botón de descarga
                        st.download_button(
                            label="📥 Descargar Excel",
                            data=buffer,
                            file_name=f"sentencias_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                            help="Descarga el archivo Excel con todos tus datos"
                        )
                        st.balloons()
                    else:
                        st.error(f"❌ Error generando Excel: {nombre_archivo}")
        
        with col2:
            st.markdown("**📋 ¿Qué incluye el Excel?**")
            st.markdown("""
            - 📊 **Procesos**: Lista completa con estados
            - 📈 **Estadísticas**: Resumen general
            """)

# Inicializar base de datos
init_database()

def verificar_dependencias():
    """Verifica que todas las dependencias estén instaladas"""
    dependencias_faltantes = []
    
    try:
        import openpyxl
    except ImportError:
        dependencias_faltantes.append("openpyxl")
    
    return dependencias_faltantes

def main():
    st.markdown('<h1 class="main-header">⚖️ Control de Sentencias Judiciales</h1>', unsafe_allow_html=True)
    
    # Verificar dependencias
    dependencias_faltantes = verificar_dependencias()
    if dependencias_faltantes:
        st.sidebar.error("⚠️ Dependencias faltantes")
        st.sidebar.markdown("Ejecuta en tu terminal:")
        for dep in dependencias_faltantes:
            st.sidebar.code(f"pip install {dep}")
        st.sidebar.info("💡 Reinicia la aplicación después de instalar")
    
    # Verificar backup diario automático al iniciar
    exito_backup, _ = verificar_backup_diario()
    if exito_backup:
        st.sidebar.success("✅ Backup diario OK")
    else:
        st.sidebar.warning("⚠️ Error en backup automático")
    
    # Sidebar para navegación
    st.sidebar.title("📋 Menú Principal")
    opcion = st.sidebar.radio(
        "Seleccione una opción:",
        ["🏠 Dashboard", "➕ Nuevo Proceso", "📊 Gestionar Procesos", "📈 Reportes", "💾 Sistema de Backup"]
    )
    
    if opcion == "🏠 Dashboard":
        mostrar_dashboard()
    elif opcion == "➕ Nuevo Proceso":
        crear_nuevo_proceso()
    elif opcion == "📊 Gestionar Procesos":
        gestionar_procesos()
    elif opcion == "📈 Reportes":
        mostrar_reportes()
    elif opcion == "💾 Sistema de Backup":
        mostrar_sistema_backup()
    
    # Información adicional en la barra lateral
    st.sidebar.markdown("---")
    
    # Estado del backup
    st.sidebar.markdown("### 💾 Estado del Backup")
    # Verificar backup de hoy
    backups_lista = obtener_lista_backups()
    hoy = datetime.now().strftime("%Y%m%d")
    backup_hoy = any(hoy in backup['archivo'] for backup in backups_lista)
    
    if backup_hoy:
        st.sidebar.success("✅ Backup de hoy creado")
    else:
        st.sidebar.warning("⚠️ No hay backup de hoy")
    
    st.sidebar.markdown(f"**📊 {len(backups_lista)} backups disponibles**")
    
    if st.sidebar.button("🔄 Actualizar Estado"):
        st.rerun()

if __name__ == "__main__":
    main()