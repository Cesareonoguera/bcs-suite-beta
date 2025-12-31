import streamlit as st
import os
import tempfile
import datetime
import shutil

# --- IMPORTAMOS TUS MÓDULOS ---
import bcs_core
import bcs_injector
import bcs_5d
import bcs_6d
import bcs_4d
import bcs_7d 

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="BCS Suite - Versión Beta",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILOS CSS ---
st.markdown("""
<style>
    .main-header {font-size: 2rem; color: #2c3e50;}
    .sub-header {font-size: 1.2rem; color: #7f8c8d;}
    .stButton>button {width: 100%;}
</style>
""", unsafe_allow_html=True)

# --- INICIALIZAR MEMORIA (SESSION STATE) ---
# Esto evita que se borre todo al descargar un PDF
if 'procesado' not in st.session_state:
    st.session_state.procesado = False
if 'rutas_salida' not in st.session_state:
    st.session_state.rutas_salida = {}

# --- CABECERA ---
col_logo, col_titulo = st.columns([1, 4])
with col_logo:
    # Busca logo.jpg en minúsculas
    if os.path.exists("logo.jpg"):
        st.image("logo.jpg", use_container_width=True)
    else:
        st.write("🏗️")

with col_titulo:
    st.markdown('<div class="main-header">BIM CONSULTING SOLUTIONS</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Suite de Cálculo Estructural & ISO 19650 (Beta Privada)</div>', unsafe_allow_html=True)

st.divider()

# --- BARRA LATERAL ---
with st.sidebar:
    st.title("⚙️ Configuración")
    
    st.subheader("1. Datos de Obra")
    fecha_input = st.date_input("Fecha Inicio", datetime.date.today())
    rendimiento = st.number_input("Rendimiento (Tn/día)", value=1.5, min_value=0.1, step=0.1)
    rendimiento_kg = rendimiento * 1000.0

    st.subheader("2. Normativa ISO 19650")
    iso_status = st.selectbox("Estado (Status)", 
        ["S0 (WIP)", "S1 (Coordinación)", "S2 (Información)", "S3 (Revisión)", "A1 (Aprobado)"],
        index=2
    )
    iso_suitability = st.selectbox("Uso (Suitability)", 
        ["Para Información", "Para Coordinación", "Para Construcción", "Para Costes"],
        index=0
    )
    iso_status_code = iso_status.split(" ")[0]
    
    st.info("ℹ️ **Modo Prueba:** Generación gratuita de entregables.")

# --- ZONA PRINCIPAL ---

st.write("### 📂 Carga de Modelo BIM (IFC)")

# Clave única para detectar cambios de archivo
uploaded_file = st.file_uploader("Arrastra tu archivo .ifc aquí", type=["ifc"], key="uploader")

st.markdown("""
    <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; font-size: 0.85em; color: #555;">
        🔒 <strong>Privacidad y Seguridad:</strong> 
        Sus archivos se procesan en un entorno seguro y volátil. 
        <br>Por política de confidencialidad, <strong>el modelo IFC original y los resultados se eliminan permanentemente</strong> de nuestros servidores en cuanto cierra esta sesión o recarga la página. 
        BIM Consulting Solutions no conserva copias de su propiedad intelectual.
    </div>
    <br>
""", unsafe_allow_html=True)

# Si el usuario cambia el archivo, reseteamos la memoria
if uploaded_file and 'ultimo_archivo' not in st.session_state:
    st.session_state.ultimo_archivo = uploaded_file.name
elif uploaded_file and uploaded_file.name != st.session_state.ultimo_archivo:
    st.session_state.procesado = False
    st.session_state.ultimo_archivo = uploaded_file.name

if uploaded_file is not None:
    st.success(f"Archivo cargado: **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} KB)")
    st.write("") 
    
    # BOTÓN DE PROCESAR
    # Solo mostramos el botón si NO hemos procesado ya este archivo
    if not st.session_state.procesado:
        if st.button("🚀 PROCESAR Y GENERAR ENTREGABLES", type="primary"):
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # --- PROCESO DE CÁLCULO ---
                status_text.text("⏳ Leyendo geometría del archivo...")
                progress_bar.progress(10)
                
                tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".ifc")
                tfile.write(uploaded_file.getvalue())
                tfile.close()
                ruta_temporal = tfile.name
                
                nombre_base = os.path.splitext(uploaded_file.name)[0]
                
                # Definir rutas de salida
                rutas = {
                    "pdf_5d": f"{nombre_base}_5D_Presupuesto.pdf",
                    "pdf_6d": f"{nombre_base}_6D_Huella.pdf",
                    "pdf_4d": f"{nombre_base}_4D_Planificacion.pdf",
                    "pdf_7d": f"{nombre_base}_7D_Libro.pdf",
                    "ifc_final": f"{nombre_base}_BCS_Enriquecido.ifc"
                }

                # Guardamos rutas en memoria
                st.session_state.rutas_salida = rutas

                status_text.text("🧠 Analizando estructura...")
                progress_bar.progress(30)
                datos, ifc_obj = bcs_core.extraer_datos_modelo(ruta_temporal)
                
                if not datos:
                    st.error("❌ No se encontraron elementos estructurales.")
                else:
                    status_text.text("💰 Calculando Presupuesto y Huella...")
                    progress_bar.progress(50)
                    bcs_5d.generar_presupuesto(datos, rutas["pdf_5d"])
                    bcs_6d.generar_informe_sostenibilidad(datos, rutas["pdf_6d"])
                    
                    status_text.text("📅 Generando Planificación...")
                    progress_bar.progress(70)
                    bcs_4d.generar_informe_4d(datos, fecha_input, rendimiento_kg, rutas["pdf_4d"])
                    bcs_7d.generar_informe_7d(datos, rutas["pdf_7d"])
                    
                    status_text.text("💉 Inyectando ISO 19650...")
                    progress_bar.progress(90)
                    bcs_injector.generar_ifc_enriquecido(
                        ifc_file=ifc_obj,
                        ruta_salida=rutas["ifc_final"],
                        datos=datos,
                        iso_status=iso_status_code,
                        iso_suitability=iso_suitability
                    )
                    
                    progress_bar.progress(100)
                    status_text.text("✅ ¡Proceso finalizado!")
                    
                    # MARCAMOS COMO PROCESADO PARA QUE NO DESAPAREZCA
                    st.session_state.procesado = True
                    st.rerun() # Recargamos para mostrar los resultados fijos

            except Exception as e:
                st.error(f"Error: {e}")
                print(e)
            finally:
                if os.path.exists(ruta_temporal): os.unlink(ruta_temporal)

    # --- ZONA DE RESULTADOS (PERSISTENTE) ---
    if st.session_state.procesado:
        st.divider()
        st.subheader("📥 Descarga de Entregables")
        
        # Recuperamos las rutas de la memoria
        rutas = st.session_state.rutas_salida
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Documentación PDF**")
            # Leemos los archivos al momento de crear el botón
            # Usamos try/except por si el usuario borró los archivos temp manualmente
            try:
                with open(rutas["pdf_5d"], "rb") as f:
                    st.download_button("💰 5D: Presupuesto", f, file_name=rutas["pdf_5d"])
                with open(rutas["pdf_6d"], "rb") as f:
                    st.download_button("🌍 6D: Huella de Carbono", f, file_name=rutas["pdf_6d"])
                with open(rutas["pdf_4d"], "rb") as f:
                    st.download_button("📅 4D: Planificación", f, file_name=rutas["pdf_4d"])
                with open(rutas["pdf_7d"], "rb") as f:
                    st.download_button("🛠️ 7D: Mantenimiento", f, file_name=rutas["pdf_7d"])
            except FileNotFoundError:
                st.warning("⚠️ Los archivos temporales han expirado. Por favor, procesa de nuevo.")
                st.session_state.procesado = False
                st.rerun()

        with col2:
            st.write("**Modelo BIM Enriquecido**")
            st.write(f"Estado: **{iso_status_code}** | Uso: **{iso_suitability}**")
            try:
                with open(rutas["ifc_final"], "rb") as f:
                    st.download_button(
                        "📦 DESCARGAR IFC FINAL", 
                        f, 
                        file_name=rutas["ifc_final"],
                        mime="application/x-step",
                        type="primary"
                    )
            except FileNotFoundError:
                pass
        
        st.divider()
        if st.button("🔄 Reiniciar / Procesar Nuevo Archivo"):
            st.session_state.procesado = False
            st.rerun()

else:
    st.info("👈 Utiliza el panel lateral para configurar la obra y sube tu archivo aquí.")