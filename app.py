import streamlit as st
import pandas as pd
import os
import io
from datetime import date

# =============================
# CONFIGURACIÓN GENERAL
# =============================
st.set_page_config(page_title="Master Record Playa Mujeres", layout="wide")

# CSS para maximizar espacio vertical, centrar y asegurar visibilidad
st.markdown("""
    <style>
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 1rem;
        max-width: 1100px;
    }
    div[data-baseweb="tab-list"] {
        justify-content: center !important;
    }
    .header-container {
        text-align: center;
        padding-bottom: 5px;
        border-bottom: 1px solid #e6e9ef;
        margin-bottom: 10px;
    }
    .main-title {
        font-size: 22px !important;
        font-weight: bold;
        color: #1f1f1f;
    }
    .sub-title {
        font-size: 13px !important;
        color: #6b6b6b;
    }
    </style>
    """, unsafe_allow_html=True)

PROMOS_FILE = "promociones_data.csv"
MEDIA_DIR = "media"
os.makedirs(MEDIA_DIR, exist_ok=True)

PROPERTIES = ["DREPM - Dreams Playa Mujeres", "SECPM - Secrets Playa Mujeres"]
MARKETS = ["USA", "CAN", "MEX", "LATAM", "EUR", "Worldwide"]

# =============================
# HELPERS Y DATOS
# =============================
def cargar_promos():
    if os.path.exists(PROMOS_FILE):
        df = pd.read_csv(PROMOS_FILE)
        for c in ["BW_Inicio", "BW_Fin", "TW_Inicio", "TW_Fin"]:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c]).dt.date
        return df
    return pd.DataFrame(columns=["Hotel", "Promo", "Market", "Rate_Plan", "Descuento", "BW_Inicio", "BW_Fin", "TW_Inicio", "TW_Fin", "Archivo_Path", "Notas"])

def generar_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Promos')
    return output.getvalue()

# =============================
# HEADER COMPACTO
# =============================
st.markdown(f"""
    <div class="header-container">
        <div class="main-title">📊 Master Record Playa Mujeres</div>
        <div class="sub-title">Hyatt Inclusive Collection | DREPM & SECPM</div>
    </div>
    """, unsafe_allow_html=True)

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
        st.info("No hay promociones registradas.")
    else:
        c1, c2 = st.columns([4, 1])
        with c1:
            search = st.text_input("Filtrar...", label_visibility="collapsed", placeholder="Buscar por promo, hotel, market o rate plan...")
        with c2:
            st.download_button("📥 Excel", data=generar_excel(df), file_name=f"MasterRecord_{date.today()}.xlsx", use_container_width=True)
        
        mask = df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
        st.dataframe(
            df[mask], 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Descuento": st.column_config.NumberColumn(format="%d%%"),
                "Archivo_Path": st.column_config.LinkColumn("Flyer/PDF")
            }
        )

# -----------------------------
# TAB: EDITAR
# -----------------------------
with tab_edit:
    if not df.empty:
        updated_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, hide_index=True, key="editor_key")
        if st.button("💾 Guardar Cambios", use_container_width=True):
            updated_df.to_csv(PROMOS_FILE, index=False)
            st.success("¡Base de datos actualizada!")
            st.rerun()

# -----------------------------
# TAB: NUEVA PROMO (CORREGIDO)
# -----------------------------
with tab_new:
    with st.form("form_registro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            n_promo = st.text_input("Nombre de la Promoción")
            n_hotel = st.multiselect("Propiedad(es)", PROPERTIES)
            n_market = st.selectbox("Mercado", MARKETS)
        with col2:
            n_rate = st.text_input("Rate Plan")
            n_desc = st.number_input("Descuento (%)", 0, 100, step=1)
        
        st.divider()
        # Se definen c3, c4, c5 y c6 para evitar el NameError
        c3, c4, c5, c6 = st.columns(4)
        with c3:
            bw_i = st.date_input("BW Inicio")
        with c4:
            bw_f = st.date_input("BW Fin")
        with c5:
            tw_i = st.date_input("TW Inicio")
        with c6:
            tw_f = st.date_input("TW Fin")
        
        uploaded_file = st.file_uploader("Adjuntar Flyer (PDF/Imagen)", type=["pdf", "png", "jpg", "jpeg"])
        n_notas = st.text_area("Notas / Restricciones")
        
        if st.form_submit_button("✅ Registrar Promoción", use_container_width=True):
            if not n_promo or not n_hotel or not n_rate:
                st.error("Completa los campos obligatorios.")
            else:
                path_archivo = ""
                if uploaded_file:
                    path_archivo = os.path.join(MEDIA_DIR, uploaded_file.name)
                    with open(path_archivo, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                new_entries = []
                for h in n_hotel:
                    new_entries.append({
                        "Hotel": h, "Promo": n_promo, "Market": n_market, 
                        "Rate_Plan": n_rate, "Descuento": n_desc,
                        "BW_Inicio": bw_i, "BW_Fin": bw_f, 
                        "TW_Inicio": tw_i, "TW_Fin": tw_f, 
                        "Archivo_Path": path_archivo, "Notas": n_notas
                    })
                df_final = pd.concat([df, pd.DataFrame(new_entries)], ignore_index=True)
                df_final.to_csv(PROMOS_FILE, index=False)
                st.success("✅ Promoción registrada.")
                st.rerun()
