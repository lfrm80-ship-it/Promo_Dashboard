import streamlit as st
import pandas as pd
import io, json, time, base64, requests
from datetime import date

# =============================
# CONFIGURACIÓN
# =============================
st.set_page_config("Master Record Playa Mujeres", layout="wide")

ADMIN_PASSWORD = st.secrets["admin_password"]
WEB_APP_URL = st.secrets["apps_script_url"]

SHEET_ID = "1dvYqQFpI7VqJFuOLeyqQdb2GijFrhoFrNrpWidakAq4"
WORKSHEET = "promociones"

# =============================
# CSV SIN CACHE
# =============================
def csv_url():
    return (
        f"https://docs.google.com/spreadsheets/d/"
        f"{SHEET_ID}/gviz/tq?"
        f"tqx=out:csv&sheet={WORKSHEET}&nocache={int(time.time())}"
    )

def cargar_df():
    try:
        df = pd.read_csv(csv_url())
    except:
        df = pd.DataFrame()
    for c in ["BW_Inicio","BW_Fin","TW_Inicio","TW_Fin"]:
        if c in df:
            df[c] = pd.to_datetime(df[c], errors="coerce").dt.date
    return df

def estado(row):
    if pd.isna(row["TW_Inicio"]) or pd.isna(row["TW_Fin"]):
        return "Expirada"
    if row["TW_Inicio"] <= date.today() <= row["TW_Fin"]:
        return "Activa"
    return "Futura"

# =============================
# STATE
# =============================
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# =============================
# SIDEBAR
# =============================
with st.sidebar:
    menu = st.radio(
        "Navegación",
        ["Vista rápida"] + (["Nueva promoción"] if st.session_state.is_admin else [])
    )

    with st.expander("Admin"):
        pwd = st.text_input("Password", type="password")
        if st.button("Entrar") and pwd == ADMIN_PASSWORD:
            st.session_state.is_admin = True
            st.rerun()

# =============================
# DATA
# =============================
df = cargar_df()

# =============================
# VISTA RÁPIDA
# =============================
if menu == "Vista rápida":
    if df.empty:
        st.info("Sin promociones")
    else:
        df["Estado"] = df.apply(estado, axis=1)
        view = df if st.session_state.is_admin else df[df["Estado"]=="Activa"]

        st.dataframe(view, use_container_width=True, hide_index=True)

        st.markdown("### 📎 Testigos")
        for _, r in view.iterrows():
            if isinstance(r.get("Archivo_Path"), str) and r["Archivo_Path"]:
                st.link_button("📄 Ver / Descargar", r["Archivo_Path"])

# =============================
# NUEVA PROMOCIÓN
# =============================
if menu == "Nueva promoción":

    with st.form("new_promo", clear_on_submit=True):

        # ----- PROMO / HOTEL / RATE -----
        c1, c2 = st.columns(2)

        with c1:
            promo = st.text_input("Promoción *")
            hotels = st.multiselect("Hotel *", ["DREPM", "SECPM"])

        with c2:
            rate = st.text_input("Rate Plan *")
            discount = st.number_input("Descuento (%)", 0, 100, step=1)

        st.divider()

        # ----- OTA / MARKET + FECHAS (LAYOUT PRO) -----
        left, right = st.columns([1.1, 2.6])

        with left:
            ota = st.selectbox("OTA *", ["Direct","Booking","Expedia"])
            market = st.selectbox("Market", ["USA","CAN","MEX","LATAM","EUR","Worldwide"])

        with right:
            # Headers
            h1, h2, h3, h4 = st.columns(4)
            with h1: st.caption("BW IN")
            with h2: st.caption("BW FIN")
            with h3: st.caption("TW IN")
            with h4: st.caption("TW FIN")

            # Inputs alineados
            i1, i2, i3, i4 = st.columns(4)
            with i1: bw_i = st.date_input("", value=None, label_visibility="collapsed", key="bw_i")
            with i2: bw_f = st.date_input("", value=None, label_visibility="collapsed", key="bw_f")
            with i3: tw_i = st.date_input("", value=None, label_visibility="collapsed", key="tw_i")
            with i4: tw_f = st.date_input("", value=None, label_visibility="collapsed", key="tw_f")

        st.divider()

        archivo = st.file_uploader(
            "Archivo (PNG, JPG, PDF, XLS, XLSX)",
            ["png","jpg","jpeg","pdf","xls","xlsx"]
        )

        notas = st.text_area("Notas")

        submit = st.form_submit_button("✅ Registrar promoción")

        if submit:
            for h in hotels:
                payload = {
                    "Hotel": h,
                    "OTA": ota,
                    "Promo": promo,
                    "Market": market,
                    "Rate_Plan": rate,
                    "Descuento": discount,
                    "BW_Inicio": str(bw_i or ""),
                    "BW_Fin": str(bw_f or ""),
                    "TW_Inicio": str(tw_i or ""),
                    "TW_Fin": str(tw_f or ""),
                    "Notas": notas
                }

                if archivo:
                    payload["FileName"] = archivo.name
                    payload["FileType"] = archivo.type
                    payload["FileContent"] = base64.b64encode(archivo.getvalue()).decode()

                r = requests.post(WEB_APP_URL, data=json.dumps(payload))
                if r.status_code != 200:
                    st.error("Error al guardar")
                    st.stop()

            st.success("✅ Promoción guardada correctamente")
            st.rerun()
