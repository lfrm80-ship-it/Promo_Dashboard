import streamlit as st
import pandas as pd
import os
from datetime import date

# =============================
# CONFIGURACIÓN GENERAL
# =============================
st.set_page_config(page_title="Master Record Playa Mujeres", layout="wide")

PROMOS_FILE = "promociones_data.csv"
MEDIA_DIR = "media"
os.makedirs(MEDIA_DIR, exist_ok=True)

PROPERTIES = ["DREPM - Dreams Playa Mujeres", "SECPM - Secrets Playa Mujeres"]
MARKETS = ["USA", "CAN", "MEX", "LATAM", "EUR", "Worldwide"]

# Carga segura de secretos para producción
try:
    ADMIN_PASSWORD = st.secrets["admin_password"]
except:
    ADMIN_PASSWORD = "admin123"

# =============================
# FUNCIONES DE DATOS
# =============================
def cargar_promos():
    if os.path.exists(PROMOS_FILE):
        df = pd.read_csv(PROMOS_FILE)
        # Convertir fechas para que Streamlit las reconozca en el editor
        for c in ["BW_Inicio", "BW_Fin", "TW_Inicio", "TW_Fin"]:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c]).dt.date
        return df
    return pd.DataFrame(columns=[
        "Hotel", "Promo", "Market", "Rate_Plan", "Descuento", 
        "BW_Inicio", "BW_Fin", "TW_Inicio", "TW_Fin", "Notas"
    ])

# =============================
# INTERFAZ PRINCIPAL
# =============================
st.title("📊 Master Record de Promociones")
st.caption("Gestión Operativa Playa Mujeres | DREPM & SECPM")

tab_view, tab_edit, tab_new = st.tabs(["🔍 Vista Rápida", "📝 Modificar/Extender", "➕ Nueva Promo"])

df = cargar_promos()

# -----------------------------
# TAB: VISTA RÁPIDA (Lectura)
# -----------------------------
with tab_view:
    if df.empty:
        st.info("No hay promociones en la base de datos.")
    else:
        search = st.text_input("Buscar por Promo o Rate Plan")
        filtered_df = df[df['Promo'].str.contains(search, case=False) | df['Rate_Plan'].str.contains(search, case=False)]
        st.dataframe(filtered_df, use_container_width=True, hide_index=True)

# -----------------------------
# TAB: MODIFICAR / EXTENDER (La "Mejora")
# -----------------------------
with tab_edit:
    st.subheader("Edición Directa y Extensiones")
    st.info("Puedes editar las fechas o descuentos directamente en la tabla y presionar 'Guardar Cambios'.")
    
    # Usamos st.data_editor para permitir cambios rápidos
    edited_df = st.data_editor(
        df, 
        num_rows="dynamic", 
        use_container_width=True,
        column_config={
            "Market": st.column_config.SelectboxColumn("Market", options=MARKETS),
            "Hotel": st.column_config.SelectboxColumn("Hotel", options=PROPERTIES),
            "Descuento": st.column_config.NumberColumn("%", format="%d%%"),
            "BW_Inicio": st.column_config.DateColumn("BW Start"),
            "BW_Fin": st.column_config.DateColumn("BW End"),
            "TW_Inicio": st.column_config.DateColumn("TW Start"),
            "TW_Fin": st.column_config.DateColumn("TW End"),
        },
        hide_index=True,
        key="editor_promos"
    )

    if st.button("💾 Guardar Cambios en la Base"):
        edited_df.to_csv(PROMOS_FILE, index=False)
        st.success("¡Base de datos actualizada correctamente!")
        st.rerun()

# -----------------------------
# TAB: NUEVA PROMO
# -----------------------------
with tab_new:
    with st.form("nuevo_registro"):
        col1, col2 = st.columns(2)
        with col1:
            n_promo = st.text_input("Nombre de la Promoción")
            n_hotel = st.multiselect("Propiedades", PROPERTIES)
            n_market = st.selectbox("Mercado / Market", MARKETS)
        with col2:
            n_rate = st.text_input("Rate Plan (ej. PROMO24)")
            n_desc = st.number_input("Descuento (%)", 0, 100, step=5)
        
        st.divider()
        c3, c4, c5, c6 = st.columns(4)
        bw_i = c3.date_input("BW Inicio")
        bw_f = c4.date_input("BW Fin")
        tw_i = c5.date_input("TW Inicio")
        tw_f = c6.date_input("TW Fin")
        
        n_notas = st.text_area("Notas / Restricciones")
        
        if st.form_submit_button("Registrar Promoción"):
            if not n_promo or not n_hotel or not n_rate:
                st.error("Faltan campos obligatorios.")
            else:
                new_data = []
                for h in n_hotel:
                    new_data.append({
                        "Hotel": h, "Promo": n_promo, "Market": n_market, 
                        "Rate_Plan": n_rate, "Descuento": n_desc,
                        "BW_Inicio": bw_i, "BW_Fin": bw_f, 
                        "TW_Inicio": tw_i, "TW_Fin": tw_f, "Notas": n_notas
                    })
                df_updated = pd.concat([df, pd.DataFrame(new_data)], ignore_index=True)
                df_updated.to_csv(PROMOS_FILE, index=False)
                st.success(f"Registrada: {n_promo}")
                st.rerun()
