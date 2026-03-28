import streamlit as st
import pandas as pd
import os
import io
import shutil
from datetime import date

# =============================
# CONFIGURACIÓN GENERAL
# =============================
st.set_page_config(page_title="Master Record Playa Mujeres", layout="wide")

PROMOS_FILE = "promociones_data.csv"
# Directorio para guardar los archivos físicos (PDF/Imágenes)
MEDIA_DIR = "media_promos"
if not os.path.exists(MEDIA_DIR):
    os.makedirs(MEDIA_DIR)

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
st.title("📊 Master Record de Promociones")
st.caption("Gestión Operativa Playa Mujeres | DREPM & SECPM")

df = cargar_promos()

tab_view, tab_edit, tab_new = st.tabs(["🔍 Vista Rápida", "📝 Modificar/Extender", "➕ Nueva Promo"])

# -----------------------------
# TAB: VISTA RÁPIDA (Lectura + Descargas)
# -----------------------------
with tab_view:
    if df.empty:
        st.info("No hay promociones en la base de datos.")
    else:
        col_search, col_download = st.columns([3, 1])
        with col_search:
            search = st.text_input("Filtrar por promo, hotel o rate plan", placeholder="Ej: Early Bird...")
        
        filtered_df = df[
            df['Promo'].str.contains(search, case=False) | 
            df['Rate_Plan'].str.contains(search, case=False) |
            df['Hotel'].str.contains(search, case=False)
        ]

        with col_download:
            st.write(" ")
            st.download_button(
                label="📥 Descargar Excel",
                data=generar_excel(filtered_df),
                file_name=f"Promociones_{date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        # Configuración de columnas para mostrar el link al archivo
        st.dataframe(
            filtered_df, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Descuento": st.column_config.NumberColumn(format="%d%%"),
                "Archivo_Path": st.column_config.LinkColumn("Documento/Flyer")
            }
        )

# -----------------------------
# TAB: MODIFICAR / EXTENDER
# -----------------------------
with tab_edit:
    st.subheader("Edición Directa")
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

    if st.button("💾 Guardar Cambios"):
        edited_df.to_csv(PROMOS_FILE, index=False)
        st.success("¡Base de datos actualizada!")
        st.rerun()

# -----------------------------
# TAB: NUEVA PROMO (Con Carga de Archivos)
# -----------------------------
with tab_new:
    with st.form("nuevo_registro", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            n_promo = st.text_input("Nombre de la Promoción")
            n_hotel = st.multiselect("Propiedades", PROPERTIES)
            n_market = st.selectbox("Mercado / Market", MARKETS)
        with c2:
            n_rate = st.text_input("Rate Plan (ej. 30PCTOFF)")
            n_desc = st.number_input("Descuento (%)", 0, 100, step=5)
        
        st.divider()
        c3, c4, c5, c6 = st.columns(4)
        bw_i = c3.date_input("BW Inicio")
        bw_f = c4.date_input("BW Fin")
        tw_i = c5.date_input("TW Inicio")
        tw_f = c6.date_input("TW Fin")
        
        # CAMPO DE ARCHIVO (Imagen o PDF)
        uploaded_file = st.file_uploader("Adjuntar Flyer o PDF de la promoción", type=["pdf", "png", "jpg", "jpeg"])
        
        n_notas = st.text_area("Notas / Restricciones")
        
        if st.form_submit_button("Registrar Promoción"):
            if not n_promo or not n_hotel or not n_rate:
                st.error("Campos obligatorios faltantes.")
            else:
                # Lógica para guardar el archivo físicamente
                file_path = ""
                if uploaded_file is not None:
                    file_path = os.path.join(MEDIA_DIR, f"{n_rate}_{uploaded_file.name}")
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                new_entries = []
                for h in n_hotel:
                    new_entries.append({
                        "Hotel": h, "Promo": n_promo, "Market": n_market, 
                        "Rate_Plan": n_rate, "Descuento": n_desc,
                        "BW_Inicio": bw_i, "BW_Fin": bw_f, 
                        "TW_Inicio": tw_i, "TW_Fin": tw_f, 
                        "Archivo_Path": file_path, # Guardamos la ruta
                        "Notas": n_notas
                    })
                df_updated = pd.concat([df, pd.DataFrame(new_entries)], ignore_index=True)
                df_updated.to_csv(PROMOS_FILE, index=False)
                st.success(f"Registrada: {n_promo} con archivo adjunto.")
                st.rerun()
