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

# --- ESTILOS CSS PARA INTERFAZ COMPACTA Y LETRA PEQUEÑA ---
# --- CSS MEJORADO PARA LEGIBILIDAD DE SERVICIOS ---
st.markdown("""
    <style>
    /* 1. Títulos y métricas pequeños */
    h1 { font-size: 22px !important; font-weight: bold !important; color: #004a99 !important; }
    h3 { font-size: 18px !important; }
    [data-testid="stMetricValue"] { font-size: 18px !important; }
    [data-testid="stMetricLabel"] { font-size: 14px !important; }

    /* 2. MAGIA PARA EL MULTISELECT: Permitir que el texto se lea completo */
    .stMultiSelect span {
        white-space: normal !important; /* Permite saltos de línea en las etiquetas seleccionadas */
        height: auto !important;
    }
    .stMultiSelect div[role="listbox"] div {
        white-space: normal !important; /* Permite saltos de línea en el menú desplegable */
    }
    
    /* 3. Ajuste de tamaño de los menús */
    .stMultiSelect div div div div { padding: 2px !important; font-size: 13px !important; }
    div[data-testid="stDateInput"] > div { padding: 0px 5px !important; font-size: 14px !important; min-height: 30px !important; }
    
    /* 4. Caja de cliente compacta */
    .cliente-box { padding: 10px; border-radius: 8px; background-color: #f8f9fa; border-left: 5px solid #004a99; margin-bottom: 10px; font-size: 14px; }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=10)
def load_data():
    file = 'servicios por vencer 2026-1.xlsx'
    df_s = pd.read_excel(file, sheet_name='Servicios Loop', engine='calamine')
    df_s = df_s.rename(columns={'Fecha Fin': 'Fecha de Vencimiento', 'Nivel': 'Nivel de PB'})
    
    # Normalización del ID para 5501-V
    df_s['No de PB'] = df_s['No de PB'].astype(str).str.strip().str.upper()
    
    cols_base = ['No de PB', 'Mascota', 'Propietario', 'Fecha de Vencimiento', 'Nivel de PB']
    df_base = df_s[cols_base].drop_duplicates(subset=['No de PB'])
    
    # Mantenemos el objeto fecha para cálculos, pero lo formatearemos al mostrar
    df_base['Fecha de Vencimiento'] = pd.to_datetime(df_base['Fecha de Vencimiento']).dt.date
    return df_base, df_s

def generar_pdf(df_print):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, "Lista de Gestion de PB - Banfield México", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", "B", 9)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(25, 8, "Vencimiento", 1, 0, "C", True) # Un poco más ancho para el formato dd/mm/aaaa
    pdf.cell(30, 8, "No de PB", 1, 0, "C", True)
    pdf.cell(30, 8, "Mascota", 1, 0, "C", True)
    pdf.cell(50, 8, "Propietario", 1, 0, "C", True)
    pdf.cell(55, 8, "Estatus/Notas", 1, 1, "C", True)
    
    pdf.set_font("Arial", "", 8)
    for _, row in df_print.iterrows():
        # CAMBIO: Formato de fecha en el PDF (Día/Mes/Año)
        fecha_formateada = row['Fecha de Vencimiento'].strftime('%d/%m/%Y')
        pdf.cell(25, 7, fecha_formateada, 1)
        pdf.cell(30, 7, str(row['No de PB']), 1)
        pdf.cell(30, 7, str(row['Mascota'])[:15], 1)
        pdf.cell(50, 7, str(row['Propietario'])[:25], 1)
        pdf.cell(55, 7, "", 1, 1)
    return bytes(pdf.output())

try:
    if os.path.exists("banfield mexico logo.svg"):
        st.sidebar.image("banfield mexico logo.svg", width=120)

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
        st.markdown("<br>"*5, unsafe_allow_html=True)

    if pb_input:
        perfil = df_maestro[df_maestro['No de PB'] == pb_input]
        if not perfil.empty:
            row = perfil.iloc[0]
            st.title(f"🐶🐱 Mascota: {row['Mascota']}")
            
            c1, c2, c3 = st.columns(3)
            with c1: 
                # CAMBIO: Formato de fecha en métrica individual
                st.metric("Vencimiento", row['Fecha de Vencimiento'].strftime('%d/%m/%Y'))
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
                up_n = st.text_area("Notas:", value=row['Notas'], key="n_i", height=80)
            
            if st.button("💾 Guardar Gestión"):
                df_up = pd.DataFrame({'No de PB': [pb_input], 'Contactado': [up_c], 'Agendado': [up_a], 'Notas': [up_n]})
                conn.update(data=df_up)
                st.success("Guardado.")
                st.cache_data.clear()
        else:
            st.warning(f"No se encontró el PB: {pb_input}")
            
    else:
        st.title("🐶🐱 Servicios Disponibles de PB")
        
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

        columnas_ordenadas = ['Fecha de Vencimiento', 'Mascota', 'Propietario', 'Nivel de PB', 'No de PB', 'Contactado', 'Agendado', 'Notas']

        df_editado = st.data_editor(
            res[columnas_ordenadas],
            column_config={
                # CAMBIO: Configuración de la columna de fecha para ver Día/Mes/Año
                "Fecha de Vencimiento": st.column_config.DateColumn(
                    "Vencimiento",
                    format="DD/MM/YYYY",
                    disabled=True
                ),
                "No de PB": st.column_config.TextColumn("No de PB", disabled=True),
                "Contactado": st.column_config.CheckboxColumn("📞"),
                "Agendado": st.column_config.CheckboxColumn("📅"),
                "Notas": st.column_config.TextColumn("Notas", width="large"),
                "Mascota": st.column_config.TextColumn(disabled=True),
                "Propietario": st.column_config.TextColumn(disabled=True),
                "Nivel de PB": st.column_config.TextColumn(disabled=True),
            },
            hide_index=True, use_container_width=True, key="editor_final_banfield"
        )

        if st.button("💾 GUARDAR CAMBIOS", type="primary"):
            df_para_sh = df_editado[['No de PB', 'Contactado', 'Agendado', 'Notas']]
            conn.update(data=df_para_sh)
            st.success("✅ Sincronizado.")
            st.cache_data.clear()

except Exception as e:
    st.error(f"⚠️ Error: {e}")


