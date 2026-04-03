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
SPREADSHEET_URL = st.secrets["gsheets_url"]
MEDIA_DIR = "media"
os.makedirs(MEDIA_DIR, exist_ok=True)

# =============================
# GOOGLE SHEETS (NATIVO)
# =============================
conn = st.connection(
    "gsheets",
    type="gsheets",
    url=SPREADSHEET_URL
)

# =============================
# SESSION STATE
# =============================
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

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
    df = conn.read(worksheet="promociones", ttl=0)
    for col in ["BW_Inicio", "BW_Fin", "TW_Inicio", "TW_Fin"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
    return df

def guardar_promo(rows):
    df = cargar_promos()
    df = pd.concat([df, pd.DataFrame(rows)], ignore_index=True)
    conn.update(worksheet="promociones", data=df)

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
        df["Estado"] = df.apply(calcular_estado, axis=1)

        # 🔹 FILTROS
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

        search = st.text_input("Buscar promoción")
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

        promo = st.text_input("Promoción *")
        hotels = st.multiselect("Hotel *", PROPERTIES)
        ota = st.selectbox("OTA *", OTAS)
        woh = st.selectbox("World of Hyatt (WOH)", ["Yes", "No"])
        market = st.selectbox("Market", MARKETS)
        rate = st.text_input("Rate Plan *")
        discount = st.number_input("Descuento (%)", 0, 100)

        bw_i = st.date_input("BW Inicio")
        bw_f = st.date_input("BW Fin")
        tw_i = st.date_input("TW Inicio")
        tw_f = st.date_input("TW Fin")

        archivo = st.file_uploader(
            "Adjuntar archivo (PNG, JPG, PDF, XLS, XLSX)",
            ["png", "jpg", "jpeg", "pdf", "xls", "xlsx"]
        )

        notas = st.text_area("Notas")
        submit = st.form_submit_button("Registrar promoción")

        if submit:
            archivo_path = ""
            if archivo:
                archivo_path = os.path.join(MEDIA_DIR, archivo.name)
                with open(archivo_path, "wb") as f:
                    f.write(archivo.getbuffer())

            rows = []
            for h in hotels:
                rows.append({
                    "Hotel": h,
                    "OTA": ota,
                    "WOH": woh,
                    "Promo": promo,
                    "Market": market,
                    "Rate_Plan": rate,
                    "Descuento": discount,
                    "BW_Inicio": bw_i,
                    "BW_Fin": bw_f,
                    "TW_Inicio": tw_i,
                    "TW_Fin": tw_f,
                    "Archivo_Path": archivo_path,
                    "Notas": notas
                })

            guardar_promo(rows)
            st.success("✅ Promoción registrada correctamente")
            st.rerun()
