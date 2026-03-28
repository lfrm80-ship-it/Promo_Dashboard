import streamlit as st
import pandas as pd
import os
import io
from datetime import date

# =============================
# CONFIGURACIÓN GENERAL
# =============================
st.set_page_config(page_title="Master Record Playa Mujeres", layout="wide")

# CSS Corregido: Asegura visibilidad y minimiza espacios
st.markdown("""
    <style>
    /* Reduce el espacio superior total */
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 1rem;
        max-width: 1100px;
    }
    /* Centra los tabs */
    div[data-baseweb="tab-list"] {
        justify-content: center !important;
    }
    /* Estilo del Header Compacto */
    .header-container {
        text-align: center;
        padding-bottom: 10px;
        border-bottom: 1px solid #e6e9ef;
        margin-bottom: 15px;
    }
    .main-title {
        font-size: 24px !important;
        font-weight: bold;
        color: #1f1f1f;
        margin-bottom: 0px;
    }
    .sub-title {
        font-size: 14px !important;
        color: #6b6b6b;
    }
    </style>
    """, unsafe_allow_html=True)

# =============================
# HEADER COMPACTO (Restaurado)
# =============================
st.markdown("""
    <div class="header-container">
        <div class="main-title">📊 Master Record Playa Mujeres</div>
        <div class="sub-title">Hyatt Inclusive Collection | DREPM & SECPM</div>
    </div>
    """, unsafe_allow_html=True)

# =============================
# HELPERS Y DATOS
# =============================
def cargar_promos():
    if os.path.exists("promociones_data.csv"):
        df = pd.read_csv("promociones_data.csv")
        for c in ["BW_Inicio", "BW_Fin", "TW_Inicio", "TW_Fin"]:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c]).dt.date
        return df
    return pd.DataFrame()

def generar_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Promos')
    return output.getvalue()

df = cargar_promos()

# =============================
# TABS PRINCIPALES
# =============================
tab_view, tab_edit, tab_new = st.tabs(["🔍 Vista", "📝 Editar", "➕ Nueva"])

# -----------------------------
# TAB: VISTA RÁPIDA
# -----------------------------
with tab_view:
    if df is None or df.empty:
        st.info("No hay promociones registradas.")
    else:
        # Fila superior compacta
        c1, c2 = st.columns([4, 1])
        with c1:
            search = st.text_input("Filtrar...", label_visibility="collapsed", placeholder="Buscar por promo, hotel o market...")
        with c2:
            st.download_button("📥 Excel", data=generar_excel(df), file_name=f"MasterRecord_{date.today()}.xlsx", use_container_width=True)
        
        # Filtro inteligente
        mask = df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
        st.dataframe(
            df[mask], 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Descuento": st.column_config.NumberColumn(format="%d%%"),
                "Archivo_Path": st.column_config.LinkColumn("Documento")
            }
        )

# -----------------------------
# TAB: EDITAR (Data Editor)
# -----------------------------
with tab_edit:
    if not df.empty:
        updated_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, hide_index=True)
        if st.button("💾 Guardar Cambios", use_container
