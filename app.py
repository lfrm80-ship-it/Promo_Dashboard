import streamlit as st
import pandas as pd
import os
import io
from datetime import date
import gspread
from google.oauth2.service_account import Credentials

# =============================
# CONFIGURACIÓN GENERAL
# =============================
st.set_page_config(
    page_title="Master Record Playa Mujeres",
    layout="wide"
)

ADMIN_PASSWORD = st.secrets.get("admin_password", "admin")
SPREADSHEET_NAME = "MasterRecordPromos"
SHEET_NAME = "promociones"
MEDIA_DIR = "media"
os.makedirs(MEDIA_DIR, exist_ok=True)

# =============================
# GOOGLE SHEETS
# =============================
def get_gsheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )
    client = gspread.authorize(creds)
    return client.open(SPREADSHEET_NAME).worksheet(SHEET_NAME)

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
        sheet = get_gsheet()
        df = pd.DataFrame(sheet.get_all_records())
        for col in ["BW_Inicio", "BW_Fin", "TW_Inicio", "TW_Fin"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
        return df
    except Exception as e:
        st.error(f"Error cargando promociones: {e}")
        return pd.DataFrame()

def guardar_promo(rows):
    sheet = get_gsheet()
    for r in rows:
        sheet.append_row([
            r["Hotel"],
            r["OTA"],
            r["WOH"],
            r["Promo"],
            r["Market"],
            r["Rate_Plan"],
            r["Descuento"],
            r["BW_Inicio"],
            r["BW_Fin"],
            r["TW_Inicio"],
            r["TW_Fin"],
            r["Archivo_Path"],
            r["Notas"]
        ])

def eliminar_promo(idx):
    sheet = get_gsheet()
    sheet.delete_rows(idx + 2)  # header + 1

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

        estados_ui = {
            "🟢 Activa": "Activa",
            "🟠 Futura": "Futura",
            "🔴 Expirada": "Expirada"
        }

        default_ui = ["🟢 Activa"] if not st.session_state.is_admin else list(estados_ui)
        filtro_estado_ui = st.multiselect(
            "Estado",
            list(estados_ui),
            default=default_ui
        )
        filtro_estado = [estados_ui[e] for e in filtro_estado_ui]

        df_view = df[df["Estado"].isin(filtro_estado)]

        col1, col2 = st.columns([4, 1])
        with col1:
            search = st.text_input("Buscar promoción…")
        with col2:
            st.download_button(
                "📥 Descargar Excel",
                data=generar_excel(df_view),
                file_name=f"MasterRecord_{date.today()}.xlsx",
                use_container_width=True
            )

        if search:
            df_view = df_view[
                df_view.astype(str)
                .apply(lambda x: x.str.contains(search, case=False, na=False))
                .any(axis=1)
            ]

        st.dataframe(df_view, use_container_width=True, hide_index=True)

        # ===== PREVIEW =====
        if not df_view.empty:
            st.divider()
            idx = st.selectbox(
                "Selecciona una promoción",
                df_view.index,
                format_func=lambda i: df_view.loc[i, "Promo"]
            )
            st.session_state.selected_idx = idx

            archivo = df_view.loc[idx, "Archivo_Path"]
            if archivo and os.path.exists(archivo):
                if st.button("👁 Ver archivo"):
                    ext = archivo.split(".")[-1].lower()
                    if ext in ["png", "jpg", "jpeg"]:
                        st.image(archivo, use_container_width=True)
                    else:
                        with open(archivo, "rb") as f:
                            st.download_button(
                                "📎 Descargar archivo",
                                f,
                                file_name=os.path.basename(archivo)
                            )
            else:
                st.info("Esta promoción no tiene archivo adjunto.")

        # ===== ELIMINAR (ADMIN) =====
        if st.session_state.is_admin and st.session_state.selected_idx is not None:
            st.divider()
            st.warning("⚠️ Esta acción no se puede deshacer")
            if st.checkbox("Confirmar eliminación"):
                if st.button("🗑 Eliminar promoción", type="primary"):
                    eliminar_promo(st.session_state.selected_idx)
                    st.success("Promoción eliminada correctamente ✅")
                    st.rerun()

# =============================
# NUEVA PROMOCIÓN
# =============================
elif menu == "➕ Nueva promoción":

    with st.form("new_promo", clear_on_submit=True):

        col1, col2 = st.columns(2)
        with col1:
            promo = st.text_input("Promoción *")
            hotels = st.multiselect("Hotel *", PROPERTIES)
            ota = st.selectbox("OTA *", OTAS)
            woh = st.selectbox("World of Hyatt (WOH)", ["Yes", "No"])
            market = st.selectbox("Market", MARKETS)

        with col2:
            rate = st.text_input("Rate Plan *")
            discount = st.number_input("Descuento (%)", 0, 100, step=1)

        st.divider()
        c3, c4, c5, c6 = st.columns(4)
        with c3:
            bw_i = st.date_input("BW Inicio")
        with c4:
            bw_f = st.date_input("BW Fin")
        with c5:
            tw_i = st.date_input("TW Inicio")
        with c6:
            tw_f = st.date_input("TW Fin")

        archivo = st.file_uploader(
            "Adjuntar archivo (PNG, JPG, PDF, XLS, XLSX)",
            ["png", "jpg", "jpeg", "pdf", "xls", "xlsx"]
        )

        notas = st.text_area("Notas / Restricciones")
        submit = st.form_submit_button("✅ Registrar promoción")

        if submit:
            if not promo or not hotels or not rate:
                st.error("Completa los campos obligatorios.")
                st.stop()

            if bw_f < bw_i or tw_f < tw_i:
                st.error("Fechas inválidas.")
                st.stop()

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
            st.success("🎉 Promoción registrada correctamente")
            st.rerun()
