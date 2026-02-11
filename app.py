import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import os
from datetime import datetime, timedelta
from fpdf import FPDF

# 1. Configuración de página CON LOGO PERSONALIZADO
# Asegúrate de que 'banfield.ico' esté en la misma carpeta.
try:
    st.set_page_config(page_title="Servicios de PB por Vencer", layout="wide", page_icon="banfield.ico")
except:
    # Si no encuentra la imagen, usa un emoji por defecto para que no falle
    st.set_page_config(page_title="Loop Gestión Banfield", layout="wide", page_icon="🐾")

# --- CONEXIÓN A GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- CARGA TURBO CON CALAMINE ---
@st.cache_data(ttl=10)
def load_data():
    file = 'servicios por vencer 2026-1.xlsx'
    # Motor Calamine para lectura ultra rápida
    df_s = pd.read_excel(file, sheet_name='Servicios Loop', engine='calamine')
    
    # Estandarización de nombres
    df_s = df_s.rename(columns={'Fecha Fin': 'Fecha de Vencimiento', 'Nivel': 'Nivel de PB'})
    
    # Crear base única de clientes
    cols_base = ['No de PB', 'Mascota', 'Propietario', 'Fecha de Vencimiento', 'Nivel de PB']
    df_base = df_s[cols_base].drop_duplicates(subset=['No de PB'])
    
    df_base['Fecha de Vencimiento'] = pd.to_datetime(df_base['Fecha de Vencimiento']).dt.date
    df_base['No de PB'] = df_base['No de PB'].astype(str)
    df_s['No de PB'] = df_s['No de PB'].astype(str)
    
    return df_base, df_s

# --- GENERADOR DE PDF ---
def generar_pdf(df_print):
    pdf = FPDF()
    pdf.add_page()
    # Título del PDF
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, "Servicios por Vencer - Banfield", ln=True, align="C")
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
    
    return pdf.output()

# --- EJECUCIÓN ---
try:
    # Intentar mostrar el logo también dentro de la app (opcional, si te gusta)
    if os.path.exists("banfield.ico"):
        st.image("banfield.ico", width=15)
        
    st.title("Sistema de Gestión Loop (Turbo)")

    df_base, df_servicios = load_data()
    # Lectura de memoria (Google Sheets)
    df_memoria = conn.read(ttl=0)
    
    df_maestro = pd.merge(df_base, df_memoria, on="No de PB", how="left")
    df_maestro[['Contactado', 'Agendado']] = df_maestro[['Contactado', 'Agendado']].fillna(False)
    df_maestro['Notas'] = df_maestro['Notas'].fillna("")


    with st.sidebar:
        st.header("🔍 Filtros")
        hoy = datetime.now().date()
        rango = st.date_input("Intervalo de Fechas:", value=(hoy, hoy + timedelta(days=30)))
        servs_sel = st.multiselect("Servicios:", sorted(df_servicios['Descripción'].unique().tolist()))
        if st.button("🔄 Sincronizar"):
            st.cache_data.clear()
            st.rerun()

    res = df_maestro.copy()
    if isinstance(rango, tuple) and len(rango) == 2:
        res = res[(res['Fecha de Vencimiento'] >= rango[0]) & (res['Fecha de Vencimiento'] <= rango[1])]
    
    if servs_sel:
        ids_v = df_servicios[df_servicios['Descripción'].isin(servs_sel)]['No de PB'].unique()
        res = res[res['No de PB'].isin(ids_v)]

    col_t, col_p = st.columns([3, 1])
    with col_t:
        st.subheader(f"📋 Lista para Gestión ({len(res)})")
    with col_p:
        if not res.empty:
            pdf_bytes = generar_pdf(res)
            st.download_button("📥 Descargar PDF", data=pdf_bytes, file_name="lista_loop_banfield.pdf")

    df_editado = st.data_editor(
        res[['Fecha de Vencimiento', 'Mascota', 'Propietario', 'Nivel de PB', 'Contactado', 'Agendado', 'Notas', 'No de PB']],
        column_config={
            "Contactado": st.column_config.CheckboxColumn("📞 Contacto"),
            "Agendado": st.column_config.CheckboxColumn("📅 Cita"),
            "Notas": st.column_config.TextColumn("📝 Comentarios", width="large"),
            "No de PB": st.column_config.TextColumn("ID", disabled=True),
        },
        disabled=['Fecha de Vencimiento', 'Mascota', 'Propietario', 'Nivel de PB'],
        hide_index=True, use_container_width=True, key="editor"
    )

    if st.button("💾 GUARDAR GESTIÓN", type="primary"):
        df_para_sh = df_editado[['No de PB', 'Contactado', 'Agendado', 'Notas']]
        conn.update(data=df_para_sh)
        st.success("✅ Guardado en Google Sheets.")
        st.cache_data.clear()

except Exception as e:
    st.error(f"⚠️ Error detectado: {e}")
    st.info("Revisa si el nombre del Excel es exacto o si el Google Sheet tiene las columnas correctas.")
    
