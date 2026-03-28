import streamlit as st
import pandas as pd
import os
from datetime import date

# =============================
# CONFIGURACIÓN GENERAL
# =============================
st.set_page_config(page_title="Administrador de Promociones", layout="wide")

PROMOS_FILE = "promociones_data.csv"
PRODUCCION_FILE = "promociones_produccion.csv"
MEDIA_DIR = "media"
os.makedirs(MEDIA_DIR, exist_ok=True)

PROPERTIES = [
    "DREPM - Dreams Playa Mujeres",
    "SECPM - Secrets Playa Mujeres"
]

# =============================
# SEGURIDAD (ST.SECRETS)
# =============================
# Nota: En local, crea un archivo .streamlit/secrets.toml con: admin_password = "tu_password"
# En la nube, agrégalo en la sección "Secrets" del dashboard.
try:
    ADMIN_PASSWORD = st.secrets["admin_password"]
except:
    ADMIN_PASSWORD = "admin123" # Fallback para desarrollo local inicial

# =============================
# HELPERS
# =============================
def safe_read_csv(path):
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame()

def cargar_promos():
    df = safe_read_csv(PROMOS_FILE)
    if df.empty:
        return df
    for c in ["BW_Inicio","BW_Fin","TW_Inicio","TW_Fin"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c]).dt.date
    return df

def cargar_produccion():
    df = safe_read_csv(PRODUCCION_FILE)
    if df.empty:
        return pd.DataFrame(columns=["Promo","Hotel","Rate_Plan","Room_Nights","Revenue","Comentario"])
    return df

def guardar_produccion(df):
    df.to_csv(PRODUCCION_FILE, index=False)

# =============================
# HEADER
# =============================
st.markdown("<h1 style='text-align:center;'>Administrador de Promociones</h1>", unsafe_allow_html=True)
st.markdown("<div style='text-align:center;color:#6b6b6b;font-size:14px;'>Playa Mujeres – DREPM & SECPM</div>", unsafe_allow_html=True)
st.divider()

# =============================
# TABS
# =============================
tab_promos, tab_registro = st.tabs(["Promociones", "Registrar / Modificar"])

# =============================
# TAB PROMOCIONES
# =============================
with tab_promos:
    df = cargar_promos()
    df_prod = cargar_produccion()
    hoy = date.today()

    if df.empty:
        st.info("No hay promociones registradas.")
    else:
        search = st.text_input("🔍 Buscar promoción")
        df_f = df.copy()

        if search:
            mask = (df_f["Promo"].str.contains(search, case=False, na=False) | 
                    df_f["Hotel"].str.contains(search, case=False, na=False))
            df_f = df_f[mask]

        filtro = st.radio("Mostrar:", ["Todas", "🟢 Activas", "🟡 Por iniciar", "🔴 Expiradas"], horizontal=True)

        for idx, row in df_f.iterrows():
            tw_ini, tw_fin = row["TW_Inicio"], row["TW_Fin"]
            estado = "🟢 Activa" if tw_ini <= hoy <= tw_fin else ("🟡 Por iniciar" if hoy < tw_ini else "🔴 Expirada")
            
            if filtro != "Todas" and estado != filtro:
                continue

            with st.expander(f"{estado} | {row['Promo']} | {row['Hotel']}"):
                st.write(f"**Rate Plan:** {row['Rate_Plan']} | **Descuento:** {row['Descuento']}%")
                st.caption(f"BW: {row['BW_Inicio']} a {row['BW_Fin']} | TW: {row['TW_Inicio']} a {row['TW_Fin']}")

    # ZONA ADMINISTRATIVA SEGURA
    st.divider()
    with st.expander("⚙️ Configuración Avanzada"):
        if not st.session_state.get("is_admin", False):
            pass_input = st.text_input("Contraseña de acceso", type="password")
            if st.button("Validar Acceso"):
                if pass_input == ADMIN_PASSWORD:
                    st.session_state.is_admin = True
                    st.rerun()
                else:
                    st.error("Acceso denegado")
        else:
            st.success("Modo Administrador Activo")
            if st.button("Cerrar Sesión"):
                st.session_state.is_admin = False
                st.rerun()
            
            if st.button("🗑️ Purgar Base de Datos"):
                if os.path.exists(PROMOS_FILE): os.remove(PROMOS_FILE)
                st.warning("Datos eliminados.")
                st.rerun()

# =============================
# TAB REGISTRAR / MODIFICAR
# =============================
with tab_registro:
    st.subheader("Nueva Promoción")
    with st.form("form_registro", clear_on_submit=True):
        promo = st.text_input("Nombre de la Promoción")
        hoteles = st.multiselect("Propiedades", PROPERTIES)
        
        c1, c2 = st.columns(2)
        bw_ini = c1.date_input("Booking Start")
        bw_fin = c2.date_input("Booking End")
        
        c3, c4 = st.columns(2)
        tw_ini = c3.date_input("Travel Start")
        tw_fin = c4.date_input("Travel End")

        submit = st.form_submit_button("Guardar")

        if submit:
            # VALIDACIÓN DE LÓGICA DE FECHAS
            if bw_fin < bw_ini or tw_fin < tw_ini:
                st.error("Error: La fecha de fin no puede ser anterior a la de inicio.")
            elif not promo or not hoteles:
                st.error("Por favor llena los campos obligatorios.")
            else:
                # Lógica de guardado...
                df_existente = cargar_promos()
                new_rows = [{"Hotel": h, "Promo": promo, "BW_Inicio": bw_ini, "BW_Fin": bw_fin, 
                             "TW_Inicio": tw_ini, "TW_Fin": tw_fin, "Rate_Plan": "Estandar", "Descuento": 0} for h in hoteles]
                df_final = pd.concat([df_existente, pd.DataFrame(new_rows)], ignore_index=True)
                df_final.to_csv(PROMOS_FILE, index=False)
                st.success("Promoción registrada con éxito.")
