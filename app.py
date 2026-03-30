import streamlit as st
import pandas as pd
import os
import io
from datetime import datetime, date

# =====================================================
# CONFIGURACIÓN GENERAL
# =====================================================
st.set_page_config(
    page_title="Master Record Playa Mujeres",
    layout="wide"
)

ADMIN_PASSWORD = st.secrets.get("admin_password", "admin")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROMOS_FILE = os.path.join(BASE_DIR, "promociones_produccion.csv")

# =====================================================
# SESSION STATE
# =====================================================
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# =====================================================
# CONSTANTES
# =====================================================
PROPERTIES = [
    "DREPM - Dreams Playa Mujeres",
    "SECPM - Secrets Playa Mujeres"
]

MARKETS = ["USA", "CAN", "MEX", "LATAM", "EUR", "Worldwide"]

# =====================================================
# FUNCIONES DE PROMOCIONES (ÚNICA ESCRITURA)
# =====================================================
def cargar_promos():
    if not os.path.exists(PROMOS_FILE):
        return pd.DataFrame()
    df = pd.read_csv(PROMOS_FILE)
    for col in ["BW_Inicio", "BW_Fin", "TW_Inicio", "TW_Fin"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
    return df


def guardar_promos(df):
    if df is None or len(df) == 0:
        st.error("⛔ Seguridad activada: intento de guardar CSV vacío BLOQUEADO.")
        st.stop()
    df.to_csv(PROMOS_FILE, index=False)


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
    if hoy < row["TW_Inicio"]:
        return "Futura"
    return "Expirada"

# =====================================================
# VARIABLES DE UPSWLL (AISLADAS – READ ONLY)
# =====================================================
OK_RM_RULES = {
    2026: {
        "ok_rm": [("2026-03-26", "2026-04-13"), ("2026-12-21", "2026-12-31")],
        "regular": {"net": 67, "pub": 89},
        "ok": {"net": 111, "pub": 148},
    },
    2027: {
        "ok_rm": [("2027-03-20", "2027-04-11"), ("2027-12-21", "2028-01-04")],
        "regular": {"net": 71, "pub": 95},
        "ok": {"net": 118, "pub": 157},
    },
}

TC_MXN = 18.50


def detectar_ok_rm(fecha_llegada):
    reglas = OK_RM_RULES.get(fecha_llegada.year)
    if not reglas:
        return None, None
    for i, f in reglas["ok_rm"]:
        if datetime.strptime(i, "%Y-%m-%d").date() <= fecha_llegada <= datetime.strptime(f, "%Y-%m-%d").date():
            return "OK RM", reglas["ok"]
    return "REGULAR", reglas["regular"]

# =====================================================
# SIDEBAR
# =====================================================
with st.sidebar:
    st.image("HIC.png", use_container_width=True)
    menu = st.radio(
        "Navegación",
        ["🔍 Vista rápida", "➕ Nueva promoción", "📈 Upsell"]
        if st.session_state.is_admin
        else ["🔍 Vista rápida", "📈 Upsell"]
    )
    st.divider()

    if st.session_state.is_admin:
        st.success("🟢 Modo ADMIN activo")
        if st.button("Salir de Admin"):
            st.session_state.is_admin = False
            st.rerun()
    else:
        with st.expander("🔒 Entrar como Admin"):
            pwd = st.text_input("Contraseña", type="password")
            if st.button("Entrar") and pwd == ADMIN_PASSWORD:
                st.session_state.is_admin = True
                st.rerun()

# =====================================================
# DATA CARGADA UNA SOLA VEZ
# =====================================================
df = cargar_promos()

# =====================================================
# VISTA RÁPIDA (READ ONLY + FILTROS)
# =====================================================
if menu == "🔍 Vista rápida":
    if df.empty:
        st.info("No hay promociones registradas.")
    else:
        df_view = df.copy()
        df_view["Estado"] = df_view.apply(calcular_estado, axis=1)

        st.subheader("🔎 Filtros")

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            h = st.multiselect("Hotel", df_view["Hotel"].unique())
        with c2:
            e = st.multiselect("Estado", ["Activa", "Futura", "Expirada"])
        with c3:
            m = st.multiselect("Market", df_view["Market"].unique())
        with c4:
            t = st.text_input("Buscar")

        if h:
            df_view = df_view[df_view["Hotel"].isin(h)]
        if e:
            df_view = df_view[df_view["Estado"].isin(e)]
        if m:
            df_view = df_view[df_view["Market"].isin(m)]
        if t:
            df_view = df_view[df_view.apply(lambda r: t.lower() in " ".join(r.astype(str)).lower(), axis=1)]

        st.dataframe(df_view, use_container_width=True, hide_index=True)
        st.download_button("📥 Descargar Excel", generar_excel(df_view), "promos.xlsx")

# =====================================================
# NUEVA PROMOCIÓN (ÚNICO GUARDADO)
# =====================================================
elif menu == "➕ Nueva promoción":
    with st.form("new_promo"):
        promo = st.text_input("Promoción")
        hotels = st.multiselect("Hotel", PROPERTIES)
        market = st.selectbox("Market", MARKETS)
        rate = st.text_input("Rate Plan")
        discount = st.number_input("Descuento (%)", 0, 100)

        c1, c2, c3, c4 = st.columns(4)
        bw_i = c1.date_input("BW Inicio")
        bw_f = c2.date_input("BW Fin")
        tw_i = c3.date_input("TW Inicio")
        tw_f = c4.date_input("TW Fin")

        notas = st.text_area("Notas")
        excel = st.file_uploader("📥 Carga masiva Excel", ["xlsx"])

        submit = st.form_submit_button("Guardar")

        if submit:
            if excel:
                df_excel = pd.read_excel(excel)
                df = pd.concat([df, df_excel], ignore_index=True)
            elif promo and hotels:
                rows = []
                for h in hotels:
                    rows.append({
                        "Hotel": h,
                        "Promo": promo,
                        "Market": market,
                        "Rate_Plan": rate,
                        "Descuento": discount,
                        "BW_Inicio": bw_i,
                        "BW_Fin": bw_f,
                        "TW_Inicio": tw_i,
                        "TW_Fin": tw_f,
                        "Notas": notas
                    })
                df = pd.concat([df, pd.DataFrame(rows)], ignore_index=True)
            else:
                st.error("Completa la información.")
                st.stop()

            guardar_promos(df)
            st.success("✅ Promoción guardada")
            st.rerun()

# =====================================================
# UPSELL (TOTALMENTE AISLADO)
# =====================================================
elif menu == "📈 Upsell":
    st.subheader("📈 Upsell")
    st.info("Este módulo es informativo y NO modifica promociones ni precios.")
