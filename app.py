import streamlit as st
import pandas as pd
import os
import io
from datetime import date

# =============================
# CONFIGURACIÓN GENERAL
# =============================
st.set_page_config(page_title="Master Record Playa Mujeres", layout="wide")

# CSS Personalizado para centrar contenido y mejorar estética
st.markdown("""
    <style>
    /* Centrar el contenedor principal */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1000px; /* Limita el ancho para que se vea centrado */
    }
    /* Estilo para los Tabs */
    .stTabs [data-baseweb="tab-list"] {
        display: flex;
        justify-content: center;
    }
    /* Títulos centrados */
    .stMarkdown h1, .stMarkdown h3, .stMarkdown p {
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

PROMOS_FILE = "promociones_data.csv"
MEDIA_DIR = "media_promos"
os.makedirs(MEDIA_DIR, exist_ok=True)

PROPERTIES = ["DREPM - Dreams Playa Mujeres", "SECPM - Secrets Playa Mujeres"]
MARKETS = ["USA", "CAN", "MEX", "LATAM", "EUR", "Worldwide"]

# =============================
# FUNCIONES DE DATOS
# =============================
def cargar_promos():
    if os.path.exists(PROMOS_FILE):
        df = pd.read_csv(PROMOS_FILE)
        for c in ["BW_Inicio", "BW_Fin", "TW_Inicio", "TW_Fin"]:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c]).dt.date
        return df
    return pd.DataFrame(columns=[
        "Hotel", "Promo", "Market", "Rate_Plan", "Descuento", 
        "BW_Inicio", "BW_Fin", "TW_Inicio", "TW_Fin", "Archivo_Path", "Notas"
    ])

def generar_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Promociones')
    return output.getvalue()

# =============================
# INTERFAZ PRINCIPAL
# =============================

# Encabezado Centrado
st.markdown("# 📊 Master Record de Promociones")
st.markdown("### Gestión Operativa Playa Mujeres")
st.markdown("<p style='color: gray;'>Hyatt Inclusive Collection | DREPM & SECPM</p>", unsafe_allow_html=True)
st.divider()

df = cargar_promos()

# Tabs centrados por CSS
tab_view, tab_edit, tab_new = st.tabs(["🔍 Vista Rápida", "📝 Modificar/Extender", "➕ Nueva Promo"])

# -----------------------------
# TAB: VISTA RÁPIDA
# -----------------------------
with tab_view:
    if df.empty:
        st.info("No hay promociones en la base de datos.")
    else:
        # Buscador y descarga alineados
        col_search, col_download = st.columns([3, 1])
        with col_search:
            search = st.text_input("Filtrar promoción...", placeholder="Ej: Early Bird")
        
        filtered_df = df[
            df['Promo'].str.contains(search, case=False) | 
            df['Rate_Plan'].str.contains(search, case=False) |
            df['Hotel'].str.contains(search, case=False)
        ]

        with col_download:
            st.write(" ") # Espaciador
            st.download_button(
                label="📥 Descargar Excel",
                data=generar_excel(filtered_df),
                file_name=f"Promociones_{date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

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
    st.markdown("#### Edición Directa de Registros")
    edited_df = st.data_editor(
        df, 
        num_rows="dynamic", 
        use_container_width=True,
        column_config={
            "Market": st.column_config.SelectboxColumn("Market", options=MARKETS),
            "Hotel": st.column_config.SelectboxColumn("Hotel", options=PROPERTIES),
            "Descuento": st.column_config.NumberColumn("%", format="%d%%"),
        },
        hide_index=True,
        key="editor_promos"
    )

    col_btn_save = st.columns([1,1,1])[1] # Botón en el centro
    if col_btn_save.button("💾 Guardar Cambios"):
        edited_df.to_csv(PROMOS_FILE, index=False)
        st.success("¡Base de datos actualizada!")
        st.rerun()

# -----------------------------
# TAB: NUEVA PROMO
# -----------------------------
with tab_new:
    st.markdown("#### Registro de Nueva Promoción")
    with st.form("nuevo_registro", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            n_promo = st.text_input("Nombre de la Promoción")
            n_hotel = st.multiselect("Propiedades", PROPERTIES)
            n_market = st.selectbox("Mercado", MARKETS)
        with c2:
            n_rate = st.text_input("Rate Plan")
            n_desc = st.number_input("Descuento (%)", 0, 100, step=5)
        
        st.divider()
        c3, c4, c5, c6 = st.columns(4)
        bw_i = c3.date_input("BW Inicio")
        bw_f = c4.date_input("BW End")
        tw_i = c5.date_input("TW Inicio")
        tw_f = c6.date_input("TW End")
        
        uploaded_file = st.file_uploader("Adjuntar Flyer/PDF", type=["pdf", "png", "jpg", "jpeg"])
        n_notas = st.text_area("Notas Adicionales")
        
        # Botón de envío centrado
        c_btn = st.columns([1,2,1])[1]
        if c_btn.form_submit_button("✅ Registrar Promoción", use_container_width=True):
            if not n_promo or not n_hotel:
                st.error("Faltan datos obligatorios.")
            else:
                file_path = ""
                if uploaded_file:
                    file_path = os.path.join(MEDIA_DIR, f"{n_rate}_{uploaded_file.name}")
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                new_rows = []
                for h in n_hotel:
                    new_rows.append({
                        "Hotel": h, "Promo": n_promo, "Market": n_market, 
                        "Rate_Plan": n_rate, "Descuento": n_desc,
                        "BW_Inicio": bw_i, "BW_Fin": bw_f, 
                        "TW_Inicio": tw_i, "TW_Fin": tw_f, 
                        "Archivo_Path": file_path, "Notas": n_notas
                    })
                df_updated = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
                df_updated.to_csv(PROMOS_FILE, index=False)
                st.success("¡Promoción guardada con éxito!")
                st.rerun()
