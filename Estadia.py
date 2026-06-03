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

# Función para guardar el registro en la nube
def guardar_registro(fecha, hora_entrada, laboratorio, actividades, evidencia_url):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    datos = {
        "fecha": fecha,
        "hora_entrada": hora_entrada,
        "laboratorio": laboratorio,
        "actividades": actividades,
        "evidencia": evidencia_url,
        "timestamp_registro": timestamp
    }
    supabase.table("registros").insert(datos).execute()

# Función para cargar datos de la nube
def cargar_datos():
    respuesta = supabase.table("registros").select("*").order("id", desc=True).execute()
    # Convertir la respuesta a DataFrame de Pandas
    if respuesta.data:
        return pd.DataFrame(respuesta.data)
    else:
        return pd.DataFrame()

# Función para cerrar sesión
def cerrar_sesion():
    st.session_state["pwd_admin"] = ""

# Interfaz principal
st.title("📓 Control de Estadías")
st.subheader("Estudiante: Ricardo Salas Nava")
st.info("Horario asignado: **13:00 hrs a 19:00 hrs**")

tab1, tab2 = st.tabs(["📝 Nuevo Registro", "🔐 Historial y Exportación (Admin)"])

with tab1:
    with st.form("registro_form", clear_on_submit=True):
        st.write("### Captura de jornada")
        
        col1, col2 = st.columns(2)
        with col1:
            fecha = st.date_input("Fecha")
            hora_entrada = st.time_input("Hora de Entrada", value=datetime.strptime("13:00", "%H:%M").time())
            
        with col2:
            laboratorio = st.selectbox("Laboratorio de turno", ["Laboratorio 104", "Laboratorio 204", "Laboratorio 211", "Laboratorio 212"])
        
        actividades = st.text_area("Actividades Realizadas", height=150, 
                                   placeholder="1. Revisión de equipos...\n2. Mantenimiento a...\n3. Asistencia en...")
        
        st.write("### Evidencia Fotográfica")
        archivo_evidencia = st.file_uploader("Sube una foto de tu trabajo (Opcional)", type=['png', 'jpg', 'jpeg'])
        
        submit_button = st.form_submit_button(label="Guardar Registro Diario")
        
        if submit_button:
            if actividades.strip() == "":
                st.error("Por favor, describe las actividades realizadas antes de guardar.")
            else:
                url_evidencia = "Sin evidencia"
                
                # Proceso de subida de imagen a la nube
                if archivo_evidencia is not None:
                    timestamp_archivo = datetime.now().strftime("%Y%m%d_%H%M%S")
                    nombre_guardado = f"{timestamp_archivo}_{archivo_evidencia.name}"
                    
                    # Convertir el archivo a bytes para subirlo
                    file_bytes = archivo_evidencia.getvalue()
                    
                    # Subir al bucket 'evidencias'
                    supabase.storage.from_("evidencias").upload(
                        path=nombre_guardado, 
                        file=file_bytes, 
                        file_options={"content-type": archivo_evidencia.type}
                    )
                    
                    # Extraer el link público
                    url_evidencia = supabase.storage.from_("evidencias").get_public_url(nombre_guardado)
                
                guardar_registro(fecha.strftime("%Y-%m-%d"), hora_entrada.strftime("%H:%M"), laboratorio, actividades, url_evidencia)
                st.success("¡Registro guardado exitosamente en la nube!")

with tab2:
    st.write("### Área Exclusiva para Administrador")
    
    contrasena_admin = "admin123" 
    
    if "pwd_admin" not in st.session_state:
        st.session_state["pwd_admin"] = ""
    
    st.text_input("Ingresa la contraseña para ver y exportar los registros:", type="password", key="pwd_admin")
    
    if st.session_state["pwd_admin"] == contrasena_admin:
        col_msg, col_btn = st.columns([0.8, 0.2])
        with col_msg:
            st.success("Acceso concedido.")
        with col_btn:
            st.button("🚪 Cerrar Sesión", on_click=cerrar_sesion)
            
        df_registros = cargar_datos()
        
        if not df_registros.empty:
            st.write("### 📊 Asistencia por Laboratorio")
            conteo_labs = df_registros['laboratorio'].value_counts()
            st.bar_chart(conteo_labs)
            
            st.write("---")
            st.write("### 📋 Tabla de Registros")
            
            df_mostrar = df_registros.rename(columns={
                'id': 'ID', 'fecha': 'Fecha', 'hora_entrada': 'Entrada', 
                'laboratorio': 'Laboratorio', 'actividades': 'Actividades', 
                'evidencia': 'Archivo Evidencia', 'timestamp_registro': 'Capturado el'
            })
            st.dataframe(df_mostrar, width='stretch', hide_index=True)
            
            st.write("### 🖼️ Ver Evidencias")
            registros_con_foto = df_mostrar[df_mostrar['Archivo Evidencia'] != 'Sin evidencia']
            
            if not registros_con_foto.empty:
                opciones_fotos = registros_con_foto['Archivo Evidencia'].tolist()
                foto_seleccionada = st.selectbox("Selecciona un enlace de imagen para ver:", opciones_fotos)
                
                if foto_seleccionada:
                    st.image(foto_seleccionada, width='stretch')
            else:
                st.info("Aún no hay fotografías subidas.")

            st.write("---")
            
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