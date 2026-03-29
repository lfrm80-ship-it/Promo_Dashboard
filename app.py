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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROMOS_FILE = os.path.join(BASE_DIR, "promociones_produccion.csv")
MEDIA_DIR = os.path.join(BASE_DIR, "media")
os.makedirs(MEDIA_DIR, exist_ok=True)

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

# =============================
# FUNCIONES
# =============================
def cargar_promos():
    if os.path.exists(PROMOS_FILE):
        try:
            df = pd.read_csv(PROMOS_FILE, sep=None, engine="python")
        except Exception:
            df = pd.read_csv(PROMOS_FILE)

        for col in ["BW_Inicio", "BW_Fin", "TW_Inicio", "TW_Fin"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce").dt.date

        return df
    return pd.DataFrame()

def generar_excel(df):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False)
    return buffer.getvalue()


def calcular_estado(row):
    hoy = date.today()
    tw_i = row.get("TW_Inicio")
    tw_f = row.get("TW_Fin")

    if pd.isna(tw_i) or pd.isna(tw_f):
        return "Expirada"
    if tw_i <= hoy <= tw_f:
        return "Activa"
    elif hoy < tw_i:
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
        ["🔍 Vista rápida", "📈 Upsell"] +
        (["➕ Nueva promoción"] if st.session_state.is_admin else [])
    )

    st.divider()
    st.caption("Acceso administrativo")

    if st.session_state.is_admin:
        st.success("🟢 Modo ADMIN activo")
        if st.button("Salir de Admin"):
            st.session_state.is_admin = False
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
st.markdown("### 📊 Master Record Playa Mujeres")
if not st.session_state.is_admin:
    st.markdown("⚠️ **READ ONLY**")

# =============================
# CARGA PROMOS
# =============================
df = cargar_promos()

# =============================
# VISTA RÁPIDA
# =============================
if menu == "🔍 Vista rápida":

    if df.empty:
        st.info("No hay promociones registradas.")
    else:
        df_view = df.copy()
        df_view["Estado"] = df_view.apply(calcular_estado, axis=1)

        st.dataframe(df_view, use_container_width=True, hide_index=True)

        st.download_button(
            "📥 Descargar Excel",
            generar_excel(df_view),
            f"MasterRecord_{date.today()}.xlsx"
        )

# =============================
# NUEVA PROMOCIÓN (ADMIN)
# =============================
elif menu == "➕ Nueva promoción":

    with st.form("new_promo", clear_on_submit=True):

    st.subheader("📥 Carga masiva desde Excel (opcional)")
    excel_file = st.file_uploader(
        "Subir archivo Excel (.xlsx / .xls)",
        ["xlsx", "xls"]
    )

    st.divider()
    st.subheader("📝 Carga manual")

    col1, col2 = st.columns(2)
    with col1:
        promo = st.text_input("Promoción")
        hotels = st.multiselect("Hotel", PROPERTIES)
        market = st.selectbox("Market", MARKETS)

    with col2:
        rate = st.text_input("Rate Plan")
        discount = st.number_input("Descuento (%)", 0, 100)

    st.divider()

    # ✅ ESTO ES LO IMPORTANTE
    col_bw_i, col_bw_f, col_tw_i, col_tw_f = st.columns(4)

    with col_bw_i:
        bw_i = st.date_input("BW Inicio")

    with col_bw_f:
        bw_f = st.date_input("BW Fin")

    with col_tw_i:
        tw_i = st.date_input("TW Inicio")

    with col_tw_f:
        tw_f = st.date_input("TW Fin")

    imagen_file = st.file_uploader(
        "Adjuntar imagen (PNG / JPG)",
        ["png", "jpg", "jpeg"]
    )

    notas = st.text_area("Notas / Restricciones")

    submit = st.form_submit_button("✅ Guardar")
            # ===== PROTECCIÓN CSV =====
            if len(df) == 0:
                st.error("⚠️ Error: el CSV quedaría vacío.")
                st.stop()

            df.to_csv(PROMOS_FILE, index=False)
            st.success("✅ Promociones guardadas correctamente")
            st.rerun()

# =============================
# UPSELL (PLACEHOLDER)
# =============================
elif menu == "📈 Upsell":
    st.subheader("📈 Upsell")
    st.info(
        "Esta pestaña ya está creada y aislada.\n\n"
        "Aquí se implementará la calculadora de Upsell "
        "para Front Desk y Reservas en el siguiente paso."
    )
