import streamlit as st
from datetime import datetime
import pandas as pd
from supabase import create_client, Client

# Configuración de página
st.set_page_config(page_title="Bitácora de Estadías - Ricardo", page_icon="📓", layout="centered")

# --- CONEXIÓN A SUPABASE ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

# --- FUNCIONES PRINCIPALES ---

def guardar_registro(fecha, hora_entrada, hora_salida, laboratorio, actividades, evidencia_url):
    """Inserta un nuevo registro en la tabla 'registros' de Supabase."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    datos = {
        "fecha": fecha,
        "hora_entrada": hora_entrada,
        "hora_salida": hora_salida,
        "laboratorio": laboratorio,
        "actividades": actividades,
        "evidencia": evidencia_url,
        "timestamp_registro": timestamp
    }
    try:
        supabase.table("registros").insert(datos).execute()
        return True, None
    except Exception as e:
        return False, str(e)


def cargar_datos():
    """Carga todos los registros desde Supabase y los devuelve como DataFrame."""
    try:
        respuesta = supabase.table("registros").select("*").execute()
        if respuesta.data:
            df = pd.DataFrame(respuesta.data)
            df = df.sort_values("id", ascending=False).reset_index(drop=True)
            return df, None
        else:
            return pd.DataFrame(), None
    except Exception as e:
        return pd.DataFrame(), str(e)


def subir_evidencia(archivo):
    """Sube una imagen al bucket 'evidencias' y devuelve su URL pública."""
    try:
        timestamp_archivo = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_guardado = f"{timestamp_archivo}_{archivo.name}"
        file_bytes = archivo.getvalue()

        supabase.storage.from_("evidencias").upload(
            path=nombre_guardado,
            file=file_bytes,
            file_options={"content-type": archivo.type}
        )

        url_publica = supabase.storage.from_("evidencias").get_public_url(nombre_guardado)
        return url_publica, None
    except Exception as e:
        return None, str(e)


def cerrar_sesion():
    """Limpia la contraseña del estado de sesión."""
    st.session_state["pwd_admin"] = ""


# --- INTERFAZ PRINCIPAL ---

st.title("📓 Control de Estadías")
st.subheader("Estudiante: Ricardo Salas Nava")
st.info("Horario asignado: **13:00 hrs a 19:00 hrs**")

tab1, tab2 = st.tabs(["📝 Nuevo Registro", "🔐 Historial y Exportación (Admin)"])


# ==================== TAB 1: NUEVO REGISTRO ====================
with tab1:
    with st.form("registro_form", clear_on_submit=True):
        st.write("### Captura de jornada")

        col1, col2 = st.columns(2)
        with col1:
            fecha = st.date_input("Fecha", value=datetime.now().date())
            hora_entrada = st.time_input(
                "Hora de Entrada",
                value=datetime.now().time().replace(second=0, microsecond=0)
            )
        with col2:
            laboratorio = st.selectbox(
                "Laboratorio de turno",
                ["Laboratorio 104", "Laboratorio 204", "Laboratorio 211", "Laboratorio 212"]
            )
            hora_salida = st.time_input(
                "Hora de Salida",
                value=datetime.now().time().replace(second=0, microsecond=0)
            )

        actividades = st.text_area(
            "Actividades Realizadas",
            height=150,
            placeholder="1. Revisión de equipos...\n2. Mantenimiento a...\n3. Asistencia en..."
        )

        st.write("### Evidencia Fotográfica")
        archivo_evidencia = st.file_uploader(
            "Sube una foto de tu trabajo (Opcional)",
            type=['png', 'jpg', 'jpeg']
        )

        submit_button = st.form_submit_button(label="Guardar Registro Diario")

        if submit_button:
            # Validaciones
            if actividades.strip() == "":
                st.error("Por favor, describe las actividades realizadas antes de guardar.")
            elif len(actividades.strip()) < 20:
                st.error("Por favor describe las actividades con más detalle (mínimo 20 caracteres).")
            elif hora_salida <= hora_entrada:
                st.error("La hora de salida debe ser mayor a la hora de entrada.")
            else:
                url_evidencia = "Sin evidencia"

                # Subida de imagen
                if archivo_evidencia is not None:
                    with st.spinner("Subiendo evidencia fotográfica..."):
                        url_evidencia, error_upload = subir_evidencia(archivo_evidencia)
                    if error_upload:
                        st.warning(f"No se pudo subir la foto, pero el registro se guardará sin evidencia. Error: {error_upload}")
                        url_evidencia = "Sin evidencia"

                # Guardar registro
                with st.spinner("Guardando registro..."):
                    exito, error_guardado = guardar_registro(
                        fecha.strftime("%Y-%m-%d"),
                        hora_entrada.strftime("%H:%M"),
                        hora_salida.strftime("%H:%M"),
                        laboratorio,
                        actividades,
                        url_evidencia
                    )

                if exito:
                    st.success("¡Registro guardado exitosamente en la nube!")
                else:
                    st.error(f"Error al guardar el registro: {error_guardado}")


# ==================== TAB 2: HISTORIAL ADMIN ====================
with tab2:
    st.write("### Área Exclusiva para Administrador")

   
    contrasena_admin = st.secrets["ADMIN_PASSWORD"]

    if "pwd_admin" not in st.session_state:
        st.session_state["pwd_admin"] = ""

    st.text_input(
        "Ingresa la contraseña para ver y exportar los registros:",
        type="password",
        key="pwd_admin"
    )

    if st.session_state["pwd_admin"] == contrasena_admin:
        col_msg, col_btn = st.columns([0.8, 0.2])
        with col_msg:
            st.success("Acceso concedido.")
        with col_btn:
            st.button("🚪 Cerrar Sesión", on_click=cerrar_sesion)

        # Cargar datos con manejo de errores
        df_registros, error_carga = cargar_datos()

        if error_carga:
            st.error(f"Error al cargar los registros: {error_carga}")
        elif not df_registros.empty:

            st.write("### 📊 Asistencia por Laboratorio")
            conteo_labs = df_registros['laboratorio'].value_counts()
            st.bar_chart(conteo_labs)

            st.write("---")
            st.write("### 📋 Tabla de Registros")

            # Renombrar columnas para visualización
            columnas_rename = {
                'id': 'ID',
                'fecha': 'Fecha',
                'hora_entrada': 'Entrada',
                'hora_salida': 'Salida',
                'laboratorio': 'Laboratorio',
                'actividades': 'Actividades',
                'evidencia': 'Archivo Evidencia',
                'timestamp_registro': 'Capturado el'
            }
            # Solo renombrar columnas que existan en el DataFrame
            columnas_presentes = {k: v for k, v in columnas_rename.items() if k in df_registros.columns}
            df_mostrar = df_registros.rename(columns=columnas_presentes)

            st.dataframe(df_mostrar, use_container_width=True, hide_index=True)

            # Visualización de evidencias fotográficas
            st.write("### 🖼️ Ver Evidencias")
            registros_con_foto = df_mostrar[df_mostrar['Archivo Evidencia'] != 'Sin evidencia']

            if not registros_con_foto.empty:
                opciones_fotos = registros_con_foto['Archivo Evidencia'].tolist()
                foto_seleccionada = st.selectbox("Selecciona un enlace de imagen para ver:", opciones_fotos)
                if foto_seleccionada:
                    st.image(foto_seleccionada, use_container_width=True)
            else:
                st.info("Aún no hay fotografías subidas.")

            st.write("---")

            # Exportación a CSV
            df_para_excel = df_mostrar.copy()
            df_para_excel.insert(0, "Estudiante", "Ricardo Salas Nava")

            csv = df_para_excel.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 Descargar todo a Excel",
                data=csv,
                file_name=f'bitacora_ricardo_{datetime.now().strftime("%Y%m%d")}.csv',
                mime='text/csv',
            )
        else:
            st.info("Aún no hay registros en la base de datos de la nube.")

    elif st.session_state["pwd_admin"] != "":
        st.error("Contraseña incorrecta. Acceso denegado.")
