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

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .stMultiSelect div div div div { padding: 1px !important; font-size: 13px !important; }
    div[data-testid="stDateInput"] > div { padding: 0px 5px !important; font-size: 14px !important; min-height: 30px !important; }
    .cliente-box { padding: 12px; border-radius: 8px; background-color: #f8f9fa; border-left: 5px solid #004a99; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=10)
def load_data():
    file = 'servicios por vencer 2026-1.xlsx'
    df_s = pd.read_excel(file, sheet_name='Servicios Loop', engine='calamine')
    df_s = df_s.rename(columns={'Fecha Fin': 'Fecha de Vencimiento', 'Nivel': 'Nivel de PB'})
    
    # NORMALIZACIÓN DE ID (Para que encuentre 5501-V, 5501-v, o 5501 V)
    df_s['No de PB'] = df_s['No de PB'].astype(str).str.strip().str.upper()
    
    cols_base = ['No de PB', 'Mascota', 'Propietario', 'Fecha de Vencimiento', 'Nivel de PB']
    df_base = df_s[cols_base].drop_duplicates(subset=['No de PB'])
    
    df_base['Fecha de Vencimiento'] = pd.to_datetime(df_base['Fecha de Vencimiento']).dt.date
    return df_base, df_s

def generar_pdf(df_print):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(190, 10, "Lista de Gestion Loop - Banfield", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", "B", 9)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(20, 8, "Vence", 1, 0, "C", True)
    pdf.cell(30, 8, "No de PB", 1, 0, "C", True)
    pdf.cell(30, 8, "Mascota", 1, 0, "C", True)
    pdf.cell(50, 8, "Propietario", 1, 0, "C", True)
    pdf.cell(60, 8, "Estatus/Notas", 1, 1, "C", True)
    
    pdf.set_font("Arial", "", 8)
    for _, row in df_print.iterrows():
        pdf.cell(20, 7, str(row['Fecha de Vencimiento']), 1)
        pdf.cell(30, 7, str(row['No de PB']), 1)
        pdf.cell(30, 7, str(row['Mascota'])[:15], 1)
        pdf.cell(50, 7, str(row['Propietario'])[:25], 1)
        pdf.cell(60, 7, "", 1, 1)
    return bytes(pdf.output())

try:
    if os.path.exists("Banfield-Logo.png"):
        st.sidebar.image("Banfield-Logo.png", width=120)

    df_base, df_servicios = load_data()
    
    try:
        df_memoria = conn.read(ttl=0)
        if not df_memoria.empty:
            df_memoria['No de PB'] = df_memoria['No de PB'].astype(str).str.strip().str.upper()
    except:
        df_memoria = pd.DataFrame(columns=['No de PB', 'Contactado', 'Agendado', 'Notas'])

    df_maestro = pd.merge(df_base, df_memoria, on="No de PB", how="left")
    df_maestro[['Contactado', 'Agendado']] = df_maestro[['Contactado', 'Agendado']].fillna(False)
    df_maestro['Notas'] = df_maestro['Notas'].fillna("")

    with st.sidebar:
        st.header("🔍 Consulta Individual")
        # El input del usuario también se limpia automáticamente
        pb_input = st.text_input("Ingresa el Número de PB a consultar:").strip().upper()
        
        st.divider()
        st.header("📅 Filtros de Lista")
        hoy = datetime.now().date()
        rango = st.date_input("Vencimientos:", value=(hoy, hoy + timedelta(days=30)))
        lista_serv = sorted(df_servicios['Descripción'].unique().tolist())
        servs_sel = st.multiselect("Servicios:", lista_serv)
        
        if st.button("🔄 Actualizar"):
            st.cache_data.clear()
            st.rerun()
        st.markdown("<br>"*10, unsafe_allow_html=True)

    if pb_input:
        # --- VISTA: FICHA INDIVIDUAL (Con Perro y Gato) ---
        perfil = df_maestro[df_maestro['No de PB'] == pb_input]
        if not perfil.empty:
            row = perfil.iloc[0]
            st.title(f"🐶🐱 Mascota: {row['Mascota']}")
            
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("Vencimiento", str(row['Fecha de Vencimiento']))
            with c2: st.metric("Plan", row['Nivel de PB'])
            with c3: st.metric("No de PB", row['No de PB'])
            
            st.markdown(f'<div class="cliente-box"><b>Propietario:</b> {row["Propietario"]}</div>', unsafe_allow_html=True)
            
            st.subheader("📋 Servicios Disponibles")
            serv_ind = df_servicios[df_servicios['No de PB'] == pb_input][['Descripción', 'Cantidad']]
            st.dataframe(serv_ind, use_container_width=True, hide_index=True)
            
            st.subheader("📝 Registrar Gestión")
            ca, cb = st.columns(2)
            with ca:
                up_c = st.checkbox("Contactado", value=row['Contactado'], key="c_i")
                up_a = st.checkbox("Agendado", value=row['Agendado'], key="a_i")
            with cb:
                up_n = st.text_area("Notas:", value=row['Notas'], key="n_i", height=100)
            
            if st.button("💾 Guardar Gestión de " + row['Mascota']):
                df_up = pd.DataFrame({'No de PB': [pb_input], 'Contactado': [up_c], 'Agendado': [up_a], 'Notas': [up_n]})
                conn.update(data=df_up)
                st.success("Guardado correctamente.")
                st.cache_data.clear()
        else:
            st.warning(f"No se encontró el PB: {pb_input}")
            
    else:
        # --- VISTA: LISTA GENERAL (Con Perro y Gato) ---
        st.title("🐶🐱 Servicios Disponibles")
        
        res = df_maestro.copy()
        if isinstance(rango, tuple) and len(rango) == 2:
            res = res[(res['Fecha de Vencimiento'] >= rango[0]) & (res['Fecha de Vencimiento'] <= rango[1])]
        if servs_sel:
            ids_v = df_servicios[df_servicios['Descripción'].isin(servs_sel)]['No de PB'].unique()
            res = res[res['No de PB'].isin(ids_v)]

        col_t, col_p = st.columns([3, 1])
        with col_t:
            st.subheader(f"📋 Lista para Atención ({len(res)})")
        with col_p:
            if not res.empty:
                pdf_bytes = generar_pdf(res)
                st.download_button("📥 Generar PDF", data=pdf_bytes, file_name="lista_banfield.pdf", mime="application/pdf")

        # Columnas reordenadas: No de PB antes de los iconos
        columnas_ordenadas = ['Fecha de Vencimiento', 'Mascota', 'Propietario', 'Nivel de PB', 'No de PB', 'Contactado', 'Agendado', 'Notas']

        df_editado = st.data_editor(
            res[columnas_ordenadas],
            column_config={
                "No de PB": st.column_config.TextColumn("No de PB", disabled=True),
                "Contactado": st.column_config.CheckboxColumn("📞"),
                "Agendado": st.column_config.CheckboxColumn("📅"),
                "Notas": st.column_config.TextColumn("Notas", width="large"),
                "Fecha de Vencimiento": st.column_config.DateColumn(disabled=True),
                "Mascota": st.column_config.TextColumn(disabled=True),
                "Propietario": st.column_config.TextColumn(disabled=True),
                "Nivel de PB": st.column_config.TextColumn(disabled=True),
            },
            hide_index=True, use_container_width=True, key="editor_vFinal_Banfield"
        )

        if st.button("💾 GUARDAR CAMBIOS DE LA LISTA", type="primary"):
            df_para_sh = df_editado[['No de PB', 'Contactado', 'Agendado', 'Notas']]
            conn.update(data=df_para_sh)
            st.success("✅ Datos sincronizados con la nube.")
            st.cache_data.clear()

except Exception as e:
    st.error(f"⚠️ Error: {e}")

