import streamlit as st
import pandas as pd
import os
import io
import requests
from datetime import date

# =============================
# CONFIGURACIÓN
# =============================
st.set_page_config(
    page_title="Master Record Playa Mujeres",
    layout="wide"
)

ADMIN_PASSWORD = st.secrets.get("admin_password", "admin")

MEDIA_DIR = "media"
os.makedirs(MEDIA_DIR, exist_ok=True)

# =============================
# GOOGLE SHEETS (LECTURA CSV)
# =============================
SHEET_ID = "1dvYqQFpI7VqJFuOLeyqQdb2GijFrhoFrNrpWidakAq4"
WORKSHEET = "promociones"

CSV_URL = (
    f"https://docs.google.com/spreadsheets/d/"
    f"{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={WORKSHEET}"
)

# =============================
# GOOGLE SHEETS (ESCRITURA)
# =============================
WEB_APP_URL = st.secrets["apps_script_url"]  # URL del Apps Script

# =============================
# SESSION STATE
# =============================
st.session_state.setdefault("is_admin", False)
st.session_state.setdefault("tw_i", None)
st.session_state.setdefault("tw_f", None)

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
    "Jet2Holidays",
    "Apple Vacations",
    "Funjet",
    "Classic Vacations",
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
            "Hotel","OTA","WOH","Promo","Market","Rate_Plan",
            "Descuento","BW_Inicio","BW_Fin",
            "TW_Inicio","TW_Fin","Archivo_Path","Notas"
        ])

    for c in ["BW_Inicio","BW_Fin","TW_Inicio","TW_Fin"]:
        df[c] = pd.to_datetime(df[c], errors="coerce").dt.date

    return df

def calcular_estado(row):
    hoy = date.today()
    if pd.isna(row["TW_Inicio"]) or pd.isna(row["TW_Fin"]):
        return "Expirada"
    if row["TW_Inicio"] <= hoy <= row["TW_Fin"]:
        return "Activa"
    if hoy < row["TW_Inicio"]:
        return "Futura"
    return "Expirada"

def generar_excel(df):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False)
    return buffer.getvalue()

# =============================
# SIDEBAR
# =============================
with st.sidebar:
    st.image("HIC.png", use_container_width=True)
    menu = st.radio(
        "Navegación",
        ["🔍 Vista rápida"] + (["➕ Nueva promoción"] if st.session_state.is_admin else [])
    )

    if st.session_state.is_admin:
        st.success("🟢 Modo ADMIN")
        if st.button("Salir de Admin"):
            st.session_state.is_admin = False
            st.rerun()
    else:
        with st.expander("Entrar como Admin"):
            pwd = st.text_input("Contraseña", type="password")
            if st.button("Entrar") and pwd == ADMIN_PASSWORD:
                st.session_state.is_admin = True
                st.rerun()

# =============================
# HEADER
# =============================
st.markdown("## 📊 Master Record Playa Mujeres")

df = cargar_promos()

# =============================
# VISTA RÁPIDA
# =============================
if menu == "🔍 Vista rápida":

    if df.empty:
        st.info("No hay promociones registradas.")
    else:
        df["Estado"] = df.apply(calcular_estado, axis=1)

        st.dataframe(df, use_container_width=True, hide_index=True)

        st.download_button(
            "📥 Descargar Excel",
            data=generar_excel(df),
            file_name=f"MasterRecord_{date.today()}.xlsx"
        )

# =============================
# NUEVA PROMOCIÓN
# =============================
elif menu == "➕ Nueva promoción":

    with st.form("new_promo", clear_on_submit=True):

        col1, col2 = st.columns(2)
        with col1:
            promo = st.text_input("Promoción *")
            hotels = st.multiselect("Hotel *", PROPERTIES)
        with col2:
            rate = st.text_input("Rate Plan *")
            discount = st.number_input("Descuento (%)", 0, 100)

        # OTA + BW
        c1, c2 = st.columns([1.2,1])
        with c1:
            ota = st.selectbox("OTA *", OTAS)
        with c2:
            bw1, bw2 = st.columns(2)
            bw_i = bw1.date_input("BW Inicio", value=None)
            bw_f = bw2.date_input("BW Fin", value=None)

        # WOH + TW (NO DESAPARECE)
        c3, c4 = st.columns([1.2,1])
        with c3:
            woh = st.selectbox("World of Hyatt (WOH)", ["No","Yes"])
        with c4:
            if woh == "Yes":
                tw1, tw2 = st.columns(2)
                st.session_state.tw_i = tw1.date_input(
                    "TW Inicio", value=st.session_state.tw_i
                )
                st.session_state.tw_f = tw2.date_input(
                    "TW Fin", value=st.session_state.tw_f
                )
            else:
                st.session_state.tw_i = None
                st.session_state.tw_f = None
                st.caption("TW no aplica")

        market = st.selectbox("Market", MARKETS)

        archivo = st.file_uploader(
            "Adjuntar archivo (PNG, JPG, PDF, XLS, XLSX)",
            ["png","jpg","jpeg","pdf","xls","xlsx"]
        )
        notas = st.text_area("Notas")

        submit = st.form_submit_button("Registrar promoción")

        if submit:
            if not promo or not hotels or not rate:
                st.error("Faltan campos obligatorios")
                st.stop()

            archivo_path = ""
            if archivo:
                archivo_path = os.path.join(MEDIA_DIR, archivo.name)
                with open(archivo_path,"wb") as f:
                    f.write(archivo.getbuffer())

            for h in hotels:
                payload = {
                    "Hotel": h,
                    "OTA": ota,
                    "WOH": woh,
                    "Promo": promo,
                    "Market": market,
                    "Rate_Plan": rate,
                    "Descuento": discount,
                    "BW_Inicio": bw_i,
                    "BW_Fin": bw_f,
                    "TW_Inicio": st.session_state.tw_i,
                    "TW_Fin": st.session_state.tw_f,
                    "Archivo_Path": archivo_path,
                    "Notas": notas
                }
                requests.post(WEB_APP_URL, json=payload)

            st.success("✅ Promoción guardada y visible en Google Sheets")
            st.rerun()
