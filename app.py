import streamlit as st
import pandas as pd
import os
import io
import json
import time
import requests
from datetime import date

# =============================
# CONFIGURACIÓN GENERAL
# =============================
st.set_page_config(
    page_title="Master Record Playa Mujeres",
    layout="wide"
)

ADMIN_PASSWORD = st.secrets.get("admin_password", "admin")
WEB_APP_URL = st.secrets.get("apps_script_url", "").strip()

MEDIA_DIR = "media"
os.makedirs(MEDIA_DIR, exist_ok=True)

# =============================
# GOOGLE SHEETS (LECTURA CSV SIN CACHE)
# =============================
SHEET_ID = "1dvYqQFpI7VqJFuOLeyqQdb2GijFrhoFrNrpWidakAq4"
WORKSHEET = "promociones"

def get_csv_url():
    return (
        f"https://docs.google.com/spreadsheets/d/"
        f"{SHEET_ID}/gviz/tq?"
        f"tqx=out:csv&sheet={WORKSHEET}&nocache={int(time.time())}"
    )

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
def date_to_str(d):
    if d is None or pd.isna(d):
        return ""
    return d.isoformat()

def cargar_promos():
    try:
        df = pd.read_csv(get_csv_url())
    except Exception:
        df = pd.DataFrame(columns=[
            "Hotel","OTA","Promo","Market","Rate_Plan",
            "Descuento","BW_Inicio","BW_Fin",
            "TW_Inicio","TW_Fin","Archivo_Path","Notas"
        ])

    for c in ["BW_Inicio","BW_Fin","TW_Inicio","TW_Fin"]:
        if c in df.columns:
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
# SESSION STATE
# =============================
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# =============================
# SIDEBAR
# =============================
with st.sidebar:
    st.image("HIC.png", use_container_width=True)

    menu = st.radio(
        "Navegación",
        ["🔍 Vista rápida"] + (["➕ Nueva promoción"] if st.session_state.is_admin else [])
    )

    st.divider()

    if st.session_state.is_admin:
        st.success("🟢 Modo ADMIN")
        if st.button("Salir de Admin"):
            st.session_state.is_admin = False
            st.rerun()
    else:
        with st.expander("🔒 Entrar como Admin"):
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
        df = df.copy()
        df["Estado"] = df.apply(calcular_estado, axis=1)

        df_view = df if st.session_state.is_admin else df[df["Estado"] == "Activa"]

        if df_view.empty:
            st.info("No hay promociones con los filtros actuales.")
        else:
            st.dataframe(df_view, use_container_width=True, hide_index=True)

            st.download_button(
                "📥 Descargar Excel",
                data=generar_excel(df_view),
                file_name=f"MasterRecord_{date.today()}.xlsx"
            )

            # ----- ARCHIVOS ADJUNTOS -----
            st.divider()
            st.markdown("### 📎 Archivos adjuntos")

            for idx, row in df_view.iterrows():

                path = row.get("Archivo_Path", "")

                if path:
                    st.markdown(f"**{row['Promo']} – {row['Hotel']}**")

                    try:
                        with open(path, "rb") as f:
                            st.download_button(
                                label="⬇️ Descargar archivo",
                                data=f,
                                file_name=os.path.basename(path),
                                key=f"dl_{idx}"
                            )
                    except Exception:
                        st.warning("Archivo no disponible")

# =============================
# NUEVA PROMOCIÓN
# =============================
elif menu == "➕ Nueva promoción":

    with st.form("new_promo", clear_on_submit=True):

        # PROMO / HOTEL / RATE
        c1, c2 = st.columns(2)

        with c1:
            promo = st.text_input("Promoción *", key="promo_name")
            hotels = st.multiselect("Hotel *", PROPERTIES, key="hotels_sel")

        with c2:
            rate = st.text_input("Rate Plan *", key="rate_plan")
            discount = st.number_input("Descuento (%)", 0, 100, step=1, key="discount")

        st.divider()

        # OTA / MARKET + FECHAS (HEADER PRO)
        left, right = st.columns([1.1, 2.6])

        with left:
            ota = st.selectbox("OTA *", OTAS, key="ota_sel")
            market = st.selectbox("Market", MARKETS, key="market_sel")

        with right:
            h1, h2, h3, h4 = st.columns(4)
            with h1: st.caption("BW IN")
            with h2: st.caption("BW FIN")
            with h3: st.caption("TW IN")
            with h4: st.caption("TW FIN")

            i1, i2, i3, i4 = st.columns(4)
            with i1:
                bw_i = st.date_input("", value=None, label_visibility="collapsed", key="bw_start")
            with i2:
                bw_f = st.date_input("", value=None, label_visibility="collapsed", key="bw_end")
            with i3:
                tw_i = st.date_input("", value=None, label_visibility="collapsed", key="tw_start")
            with i4:
                tw_f = st.date_input("", value=None, label_visibility="collapsed", key="tw_end")

        st.divider()

        archivo = st.file_uploader(
            "Adjuntar archivo (PNG, JPG, PDF, XLS, XLSX)",
            ["png", "jpg", "jpeg", "pdf", "xls", "xlsx"],
            key="file_upload"
        )

        notas = st.text_area("Notas / Restricciones", key="notes")

        # SUBMIT SIEMPRE AL FINAL
        submit = st.form_submit_button("✅ Registrar promoción")

        if submit:

            if not promo or not hotels or not rate:
                st.error("Completa los campos obligatorios.")
                st.stop()

            if bw_i and bw_f and bw_f < bw_i:
                st.error("BW Fin no puede ser menor que BW Inicio.")
                st.stop()

            if tw_i and tw_f and tw_f < tw_i:
                st.error("TW Fin no puede ser menor que TW Inicio.")
                st.stop()

            if not WEB_APP_URL.startswith("https://"):
                st.error("La URL de Apps Script no está configurada correctamente.")
                st.stop()

            archivo_path = ""
            if archivo:
                archivo_path = os.path.join(MEDIA_DIR, archivo.name)
                with open(archivo_path, "wb") as f:
                    f.write(archivo.getbuffer())

            headers = {"Content-Type": "application/json"}

            for h in hotels:
                payload = {
                    "Hotel": h,
                    "OTA": ota,
                    "Promo": promo,
                    "Market": market,
                    "Rate_Plan": rate,
                    "Descuento": discount,
                    "BW_Inicio": date_to_str(bw_i),
                    "BW_Fin": date_to_str(bw_f),
                    "TW_Inicio": date_to_str(tw_i),
                    "TW_Fin": date_to_str(tw_f),
                    "Archivo_Path": archivo_path,
                    "Notas": notas
                }

                r = requests.post(
                    WEB_APP_URL,
                    data=json.dumps(payload),
                    headers=headers,
                    timeout=10
                )

                if r.status_code != 200:
                    st.error("Error escribiendo en Google Sheets.")
                    st.stop()

            st.success("🎉 Promoción guardada correctamente")
            st.rerun()
