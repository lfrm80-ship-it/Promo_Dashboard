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

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

PROMOS_FILE = "promociones_produccion.csv"
MEDIA_DIR = "media"
os.makedirs(MEDIA_DIR, exist_ok=True)

PROPERTIES = [
    "DREPM - Dreams Playa Mujeres",
    "SECPM - Secrets Playa Mujeres"
]

MARKETS = ["USA", "CAN", "MEX", "LATAM", "EUR", "Worldwide"]

# =============================
# CSS
# =============================
st.markdown("""
<style>
.badge {
    padding: 4px 8px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 600;
    color: white;
}
.activa { background-color: #16a34a; }
.futura { background-color: #f59e0b; }
.expirada { background-color: #dc2626; }

.readonly {
    position: fixed;
    top: 90px;
    right: 22px;
    background: #f1f5f9;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 600;
    border: 1px solid #cbd5e1;
}
</style>
""", unsafe_allow_html=True)

# =============================
# HELPERS
# =============================
def cargar_promos():
    if os.path.exists(PROMOS_FILE):
        df = pd.read_csv(PROMOS_FILE)

        # Convertir fechas SOLO si existen
        for c in ["BW_Inicio", "BW_Fin", "TW_Inicio", "TW_Fin"]:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], errors="coerce").dt.date

        return df

    return pd.DataFrame()

def generar_excel(df):
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False)
    return out.getvalue()

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
        ["🔍 Vista rápida"] +
        (["📝 Editar promociones", "➕ Nueva promoción"] if st.session_state.is_admin else [])
    )

    st.divider()
    st.caption("Acceso administrativo")

    if st.session_state.is_admin:
        st.success("🟢 Modo ADMIN activo")
        if st.button("Salir de Admin"):
            st.session_state.is_admin = False
            st.rerun()
    else:
        with st.expander("🔒 Cambiar a Admin"):
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
st.markdown(
    "<h3 style='text-align:center;'>📊 Master Record Playa Mujeres</h3>",
    unsafe_allow_html=True
)

if not st.session_state.is_admin:
    st.markdown("<div class='readonly'>READ ONLY</div>", unsafe_allow_html=True)

df = cargar_promos()

# =============================
# VISTA RÁPIDA
# =============================
if menu == "🔍 Vista rápida":

    if df.empty:
        st.info("No hay promociones registradas.")
    else:
        df["Estado"] = df.apply(calcular_estado, axis=1)

        estados = ["Activa", "Futura", "Expirada"]
        default = ["Activa"] if not st.session_state.is_admin else estados

        filtro_estado = st.multiselect(
            "Estado de la promoción",
            estados,
            default=default
        )

        df = df[df["Estado"].isin(filtro_estado)]

        search = st.text_input("Buscar…")
        mask = df.astype(str).apply(
            lambda x: x.str.contains(search, case=False, na=False)
        ).any(axis=1)

        st.dataframe(
            df[mask],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Archivo_Path": st.column_config.LinkColumn("Flyer / PDF")
            }
        )

        # =============================
        # PREVISUALIZACIÓN
        # =============================
        if not df[mask].empty and "Archivo_Path" in df.columns:
            st.divider()
            st.subheader("📎 Vista previa")

            idx = st.selectbox(
                "Selecciona una promoción",
                df[mask].index,
                format_func=lambda i: df.loc[i, "Promo"]
            )

            archivo = df.loc[idx, "Archivo_Path"]

            if isinstance(archivo, str) and archivo and os.path.exists(archivo):
                if archivo.lower().endswith(".pdf"):
                    st.markdown(
                        f'<iframe src="{archivo}" width="100%" height="600"></iframe>',
                        unsafe_allow_html=True
                    )
                else:
                    st.image(archivo, use_container_width=True)
            else:
                st.info("Esta promoción no tiene archivo adjunto.")

# =============================
# NUEVA PROMO (ADMIN)
# =============================
elif menu == "➕ Nueva promoción":

    with st.form("new_promo", clear_on_submit=True):

        col1, col2 = st.columns(2)
        with col1:
            promo = st.text_input("Promoción *")
            hotels = st.multiselect("Hotel *", PROPERTIES)
            market = st.selectbox("Market", MARKETS)
        with col2:
            rate = st.text_input("Rate Plan *")
            discount = st.number_input("Descuento %", 0, 100)

        st.divider()

        c3, c4, c5, c6 = st.columns(4)
