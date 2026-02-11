import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import os
from datetime import datetime, timedelta
from fpdf import FPDF

# 1. Configuración de página
try:
    st.set_page_config(page_title="Servicios de PB Banfield México", layout="wide", page_icon="banfield.ico")
except:
    st.set_page_config(page_title="Servicios de PB Banfield México", layout="wide", page_icon="🐾")

# --- ESTILOS CSS PARA MEJORAR LA INTERFAZ ---
st.markdown("""
    <style>
    .stMultiSelect div div div div { padding: 2px !important; font-size: 14px !important; }
    .stSelectbox div div div div { padding: 2px !important; font-size: 14px !important; }
    .st-emotion-cache-16ids93 { gap: 0.5rem; }
    .cliente-box {
        padding: 15px;
        border-radius: 8px;
        background-color: #f8f9fa;
        border-left: 5px solid #004a99;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN A GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=10)
def load_data():
    file = 'servicios por vencer 2026-1.xlsx'
    # LECTURA TURBO CON CALAMINE
    df_s = pd.read_excel(file, sheet_name='Servicios Loop', engine='calamine')
    
    # Estandarización de columnas
    df_s = df_s.rename(columns={'Fecha Fin': 'Fecha de Vencimiento', 'Nivel': 'Nivel de PB'})
    
    # Crear base única de mascotas por su ID (No de PB)
    cols_base = ['No de PB', 'Mascota', 'Propietario', 'Fecha de Vencimiento', 'Nivel de PB']
    df_base = df_s[cols_base].drop_duplicates(subset=['No de PB'])
    
    df_base['Fecha de Vencimiento'] = pd.to_datetime(df_base['Fecha de Vencimiento']).dt.date
    df_base['No de PB'] = df_base['No de PB'].astype(str)
    df_s['No de PB'] = df_s['No de PB'].astype(str)
    
    return df_base, df_s

def generar_pdf(df_print):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, "Lista de Gestion Loop - Banfield", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", "B", 9)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(25, 8, "Vence", 1, 0, "C", True)
    pdf.cell(30, 8, "Mascota", 1, 0, "C", True)
    pdf.cell(55, 8, "Propietario", 1, 0, "C", True)
    pdf.cell(25, 8, "Nivel", 1, 0, "C", True)
    pdf.cell(55, 8, "Estatus/Notas", 1, 1, "C", True)
    pdf.set_font("Arial", "", 8)
    for _, row in df_print.iterrows():
        pdf.cell(25, 7, str(row['Fecha de Vencimiento']), 1)
        pdf.cell(30, 7, str(row['Mascota'])[:15], 1)
        pdf.cell(55, 7, str(row['Propietario'])[:30], 1)
        pdf.cell(25, 7, str(row['Nivel de PB'])[:12], 1)
        pdf.cell(55, 7, "", 1, 1)
    return bytes(pdf.output())

# --- INICIO DE EJECUCIÓN ---
try:
    if os.path.exists("banfield.ico"):
        st.sidebar.image("banfield.ico", width=60)

    df_base, df_servicios = load_data()
    
    # Leer memoria desde Google Sheets
    try:
        df_memoria = conn.read(ttl=0)
    except:
        df_memoria = pd.DataFrame(columns=['No de PB', 'Contactado', 'Agendado', 'Notas'])

    df_maestro = pd.merge(df_base, df_memoria, on="No de PB", how="left")
    df_maestro[['Contactado', 'Agendado']] = df_maestro[['Contactado', 'Agendado']].fillna(False)
    df_maestro['Notas'] = df_maestro['Notas'].fillna("")

    # --- BARRA LATERAL ---
    with st.sidebar:
        st.header("🔎 Consulta Rápida")
        # CAMBIO DE NOMBRE AQUÍ
        pb_input = st.text_input("Ingresa el Número de PB a consultar:", placeholder="Ej: 123456")
        
        st.divider()
        st.header("📅 Filtros de Lista")
        hoy = datetime.now().date()
        rango = st.date_input("Periodo de Vencimiento:", value=(hoy, hoy + timedelta(days=30)))
        
        lista_serv = sorted(df_servicios['Descripción'].unique().tolist())
        servs_sel = st.multiselect("Filtrar por Servicios:", lista_serv)
        
        if st.button("🔄 Actualizar Datos"):
            st.cache_data.clear()
            st.rerun()
        
        # Espacio para que el menú abra hacia abajo
        st.markdown("<br>"*8, unsafe_allow_html=True)

    # --- LÓGICA DE PANTALLA ---
    if pb_input:
        # --- VISTA: FICHA INDIVIDUAL ---
        perfil = df_maestro[df_maestro['No de PB'] == pb_input]
        
        if not perfil.empty:
            row = perfil.iloc[0]
            st.title(f"🐶 Mascota: {row['Mascota']}")
            
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("Vencimiento", str(row['Fecha de Vencimiento']))
            with c2: st.metric("Nivel de PB", row['Nivel de PB'])
            with c3: st.metric("No de PB", row['No de PB'])
            
            st.markdown(f"""
            <div class="cliente-box">
                <b>Propietario:</b> {row['Propietario']}<br>
                <b>Estatus:</b> {'📞 Contactado' if row['Contactado'] else '⚪ Pendiente'} | 
                {'📅 Agendado' if row['Agendado'] else '⏳ Sin cita'}
            </div>
            """, unsafe_allow_html=True)
            
            st.subheader("📋 Servicios Incluidos")
            serv_ind = df_servicios[df_servicios['No de PB'] == pb_input][['Descripción', 'Cantidad']]
            st.dataframe(serv_ind, use_container_width=True, hide_index=True)
            
            st.subheader("📝 Registrar Gestión")
            ca, cb = st.columns(2)
            with ca:
                up_c = st.checkbox("Ya se contactó", value=row['Contactado'], key="c_i")
                up_a = st.checkbox("Ya agendó cita", value=row['Agendado'], key="a_i")
            with cb:
                up_n = st.text_area("Notas de la llamada:", value=row['Notas'], key="n_i")
            
            if st.button("💾 Guardar Gestión del PB " + pb_input):
                df_up = pd.DataFrame({'No de PB': [pb_input], 'Contactado': [up_c], 'Agendado': [up_a], 'Notas': [up_n]})
                conn.update(data=df_up)
                st.success("Gestión guardada correctamente.")
                st.cache_data.clear()
        else:
            st.warning(f"No se encontró información para el Número de PB: {pb_input}")
            
    else:
        # --- VISTA: LISTA GENERAL ---
        st.title("🐾 Panel de Gestión Banfield")
        
        res = df_maestro.copy()
        if isinstance(rango, tuple) and len(rango) == 2:
            res = res[(res['Fecha de Vencimiento'] >= rango[0]) & (res['Fecha de Vencimiento'] <= rango[1])]
        
        if servs_sel:
            ids_v = df_servicios[df_servicios['Descripción'].isin(servs_sel)]['No de PB'].unique()
            res = res[res['No de PB'].isin(ids_v)]

        col_t, col_p = st.columns([3, 1])
        with col_t:
            st.subheader(f"📋 Lista para Distribución ({len(res)})")
        with col_p:
            if not res.empty:
                pdf_bytes = generar_pdf(res)
                st.download_button("📥 Generar PDF", data=pdf_bytes, file_name="lista_banfield.pdf", mime="application/pdf")

        df_editado = st.data_editor(
            res[['Fecha de Vencimiento', 'Mascota', 'Propietario', 'Nivel de PB', 'Contactado', 'Agendado', 'Notas', 'No de PB']],
            column_config={
                "Contactado": st.column_config.CheckboxColumn("📞"),
                "Agendado": st.column_config.CheckboxColumn("📅"),
                "Notas": st.column_config.TextColumn("Notas", width="large"),
                "No de PB": st.column_config.TextColumn("ID", disabled=True),
            },
            disabled=['Fecha de Vencimiento', 'Mascota', 'Propietario', 'Nivel de PB'],
            hide_index=True, use_container_width=True, key="editor_vFinal"
        )

        if st.button("💾 GUARDAR CAMBIOS DE LA LISTA", type="primary"):
            df_para_sh = df_editado[['No de PB', 'Contactado', 'Agendado', 'Notas']]
            conn.update(data=df_para_sh)
            st.success("✅ Sincronización completa con la nube.")
            st.cache_data.clear()

except Exception as e:
    st.error(f"⚠️ Error en el sistema: {e}")
