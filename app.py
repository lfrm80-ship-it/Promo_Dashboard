import streamlit as st
import pandas as pd
import os
import io
from datetime import date

# =============================
# CONFIGURACIÓN GENERAL
# =============================
st.set_page_config(page_title="Master Record", layout="wide")

# CSS para maximizar espacio vertical y centrar
st.markdown("""
    <style>
    .block-container {
        padding-top: 1rem;    /* Espacio mínimo arriba */
        padding-bottom: 1rem;
        max-width: 1100px;
    }
    .stTabs [data-baseweb="tab-list"] {
        display: flex;
        justify-content: center;
    }
    /* Estilo para el mini-header */
    .mini-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.5rem 0;
        border-bottom: 1px solid #f0f2f6;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

# =============================
# MINI-HEADER (Todo en una línea)
# =============================
st.markdown("""
    <div class='mini-header'>
        <span style='font-weight: bold; font-size: 20px;'>📊 Master Record Playa Mujeres</span>
        <span style='color: gray; font-size: 14px;'>Hyatt Inclusive Collection | DREPM & SECPM</span>
    </div>
    """, unsafe_allow_html=True)

# --- Funciones de datos permanecen igual ---
def cargar_promos():
    if os.path.exists("promociones_data.csv"):
        df = pd.read_csv("promociones_data.csv")
        for c in ["BW_Inicio", "BW_Fin", "TW_Inicio", "TW_Fin"]:
            if c in df.columns: df[c] = pd.to_datetime(df[c]).dt.date
        return df
    return pd.DataFrame(columns=["Hotel", "Promo", "Market", "Rate_Plan", "Descuento", "BW_Inicio", "BW_Fin", "TW_Inicio", "TW_Fin", "Archivo_Path", "Notas"])

def generar_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Promociones')
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
    if df.empty:
        st.info("Sin registros.")
    else:
        c1, c2 = st.columns([4, 1])
        with c1:
            search = st.text_input("Filtrar...", label_visibility="collapsed", placeholder="Buscar promo, hotel o market")
        with c2:
            st.download_button("Excel", data=generar_excel(df), file_name="Promos.xlsx", use_container_width=True)
        
        filtered_df = df[df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]
        
        st.dataframe(
            filtered_df, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Descuento": st.column_config.NumberColumn(format="%d%%"),
                "Archivo_Path": st.column_config.LinkColumn("Flyer")
            }
        )

# -----------------------------
# TAB: MODIFICAR / EXTENDER
# -----------------------------
with tab_edit:
    edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, hide_index=True, key="editor")
    if st.button("💾 Guardar Cambios", use_container_width=True):
        edited_df.to_csv("promociones_data.csv", index=False)
        st.success("Actualizado")
        st.rerun()

# -----------------------------
# TAB: NUEVA PROMO
# -----------------------------
with tab_new:
    with st.form("nuevo_registro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            n_promo = st.text_input("Nombre")
            n_hotel = st.multiselect("Hoteles", ["DREPM - Dreams Playa Mujeres", "SECPM - Secrets Playa Mujeres"])
        with col2:
            n_rate = st.text_input("Rate Plan")
            n_desc = st.number_input("%", 0, 100, step=5)
        
        st.divider()
        c3, c4, c5, c6 = st.columns(4)
        bw_i, bw_f = c3.date_input("BW In"), c4.date_input("BW Fin")
        tw_i, tw_f = c5.date_input("TW In"), c6.date_input("TW Fin")
        
        uploaded_file = st.file_uploader("Adjuntar Flyer", type=["pdf", "png", "jpg"])
        
        if st.form_submit_button("✅ Registrar", use_container_width=True):
            # Lógica de guardado simplificada
            new_rows = []
            for h in n_hotel:
                new_rows.append({"Hotel": h, "Promo": n_promo, "Rate_Plan": n_rate, "Descuento": n_desc, "BW_Inicio": bw_i, "BW_Fin": bw_f, "TW_Inicio": tw_i, "TW_Fin": tw_f})
            pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True).to_csv("promociones_data.csv", index=False)
            st.rerun()
