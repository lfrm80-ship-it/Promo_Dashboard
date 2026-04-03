import streamlit as st
import pandas as pd
import os
import io
from datetime import date

# =============================
# CONFIGURACIÓN GENERAL
# =============================
st.set_page_config(
    page_title="Master Record Playa Mujeres",
    layout="wide"
)

ADMIN_PASSWORD = st.secrets.get("admin_password", "admin")

MEDIA_DIR = "media"
os.makedirs(MEDIA_DIR, exist_ok=True)

# =============================
# GOOGLE SHEETS (CSV PÚBLICO)
# =============================
SHEET_ID = "1dvYqQFpI7VqJFuOLeyqQdb2GijFrhoFrNrpWidakAq4"
WORKSHEET = "promociones"

CSV_URL = (
    f"https://docs.google.com/spreadsheets/d/"
    f"{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={WORKSHEET}"
)

# =============================
# SESSION STATE
# =============================
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "selected_idx" not in st.session_state:
    st.session_state.selected_idx = None

# =============================
# CONSTANTES
# =============================
PROPERTIES = [
    "DREPM - Dreams Playa Mujeres",
    "SECPM - Secrets Playa Mujeres"
]

MARKETS = ["USA", "CAN", "MEX", "LATAM", "EUR", "Worldwide"]

OTAS = [
    "Direct",
    "Booking.com",
    "Expedia",
    "Hotelbeds",
    "Other"
]

# =============================
# FUNCIONES
# =============================
def cargar_promos():
    try:
        df = pd.read_csv(CSV_URL)
    except Exception:
        df = pd.DataFrame(columns=[
            "Hotel", "OTA", "WOH", "Promo", "Market", "Rate_Plan",
            "Descuento", "BW_Inicio", "BW_Fin",
            "TW_Inicio", "TW_Fin", "Archivo_Path", "Notas"
        ])

    for col in ["BW_Inicio", "BW_Fin", "TW_Inicio", "TW_Fin"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.date

    return df

def generar_excel(df):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False)
    return buffer.getvalue()

def calcular_estado(row):
    hoy = date.today()
    if pd.isna(row["TW_Inicio"]) or pd.isna(row["TW_Fin"]):
        return "Expirada"
    if row["TW_Inicio"] <= hoy <= row["TW_Fin"]:
        return "Activa"
    elif hoy < row["TW_Inicio"]:
        return "Futura"
    else:
        return "Expirada"

# =============================
# SIDEBAR
# =============================
with st.sidebar:
    st.image("HIC.png", use_container_width=True)
    st.divider()

    menu = st.radio(
        "Navegación",
        ["🔍 Vista rápida"] + (["➕ Nueva promoción"] if st.session_state.is_admin else [])
    )

    st.divider()
    st.caption("Acceso administrativo")

    if st.session_state.is_admin:
        st.success("🟢 Modo ADMIN activo")
        if st.button("Salir de Admin"):
            st.session_state.is_admin = False
            st.session_state.selected_idx = None
            st.rerun()
    else:
        with st.expander("🔒 Entrar como Admin"):
            pwd = st.text_input("Contraseña", type="password")
            if st.button("Entrar"):
                if pwd == ADMIN_PASSWORD:
                    st.session_state.is_admin = True
                    st.rerun()
                else:
                    st.error("Contraseña incorrecta")

# =============================
# HEADER
# =============================
st.markdown("## 📊 Master Record Playa Mujeres")
if not st.session_state.is_admin:
    st.caption("Modo lectura")

df = cargar_promos()

# =============================
# VISTA RÁPIDA
# =============================
if menu == "🔍 Vista rápida":

    if df.empty:
        st.info("No hay promociones registradas.")
    else:
        df = df.copy()
        df["Estado"] = df.apply(calcular_estado, axis=1)

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filtro_woh = st.selectbox("WOH", ["All", "Yes", "No"])
        with col_f2:
            filtro_estado = st.multiselect(
                "Estado",
                ["Activa", "Futura", "Expirada"],
                default=["Activa"] if not st.session_state.is_admin else ["Activa", "Futura", "Expirada"]
            )

        df_view = df[df["Estado"].isin(filtro_estado)]
        if filtro_woh != "All":
            df_view = df_view[df_view["WOH"] == filtro_woh]

        search = st.text_input("Buscar promoción…")
        if search:
            df_view = df_view[
                df_view.astype(str)
                .apply(lambda x: x.str.contains(search, case=False, na=False))
                .any(axis=1)
            ]

        st.dataframe(df_view, use_container_width=True, hide_index=True)

        st.download_button(
            "📥 Descargar Excel",
            data=generar_excel(df_view),
            file_name=f"MasterRecord_{date.today()}.xlsx"
        )

# =============================
# NUEVA PROMOCIÓN
# =============================
elif menu == "➕ Nueva promoción":

    with st.form("new_promo", clear_on_submit=True):

        # =============================
        # DATOS GENERALES (PROMO)
        # =============================
        col1, col2 = st.columns(2)

        with col1:
            promo = st.text_input("Promoción *")
            hotels = st.multiselect("Hotel *", PROPERTIES)

        with col2:
            rate = st.text_input("Rate Plan *")
            discount = st.number_input("Descuento (%)", 0, 100, step=1)

        st.divider()

        # =============================
        # OTA + BW (MISMA FILA)
        # =============================
        c1, c2 = st.columns([1.2, 1])

        with c1:
            ota = st.selectbox("OTA *", OTAS)

        with c2:
            bw_c1, bw_c2 = st.columns(2)
            with bw_c1:
                bw_i = st.date_input("BW Inicio", value=None)
            with bw_c2:
                bw_f = st.date_input("BW Fin", value=None)

        # =============================
        # WOH + TW (MISMA FILA)
        # =============================
        c3, c4 = st.columns([1.2, 1])

        with c3:
            woh = st.selectbox("World of Hyatt (WOH)", ["Yes", "No"])

        with c4:
            tw_c1, tw_c2 = st.columns(2)
            with tw_c1:
                tw_i = st.date_input("TW Inicio", value=None)
            with tw_c2:
                tw_f = st.date_input("TW Fin", value=None)

        # =============================
        # MARKET
        # =============================
        market = st.selectbox("Market", MARKETS)

        st.divider()

        # =============================
        # ARCHIVO Y NOTAS
        # =============================
        archivo = st.file_uploader(
            "Adjuntar archivo (PNG, JPG, PDF, XLS, XLSX)",
            ["png", "jpg", "jpeg", "pdf", "xls", "xlsx"]
        )

        notas = st.text_area("Notas / Restricciones")

        submit = st.form_submit_button("✅ Registrar promoción")

