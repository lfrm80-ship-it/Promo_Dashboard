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
        ["🔍 Vista rápida", "📈 Upsell"] +
        (["➕ Nueva promoción"] if st.session_state.is_admin else [])
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
st.markdown("""
### 📊 Master Record Playa Mujeres
""", unsafe_allow_html=True)

if not st.session_state.is_admin:
    st.markdown("⚠️ **READ ONLY**", unsafe_allow_html=True)

# =============================
# CARGA DE PROMOCIONES (CRÍTICO)
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

        estados_ui = {
            "🟢 Activa": "Activa",
            "🟠 Futura": "Futura",
            "🔴 Expirada": "Expirada"
        }

        default_ui = (
            ["🟢 Activa"]
            if not st.session_state.is_admin
            else list(estados_ui.keys())
        )

        filtro_ui = st.multiselect(
            "Estado",
            list(estados_ui.keys()),
            default=default_ui
        )

        filtro = [estados_ui[e] for e in filtro_ui]
        df_view = df_view[df_view["Estado"].isin(filtro)]

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

        # -------- Vista previa --------
        if not df_view.empty:
            st.divider()
            st.subheader("📎 Vista previa")

            selected_idx = st.selectbox(
                "Selecciona una promoción",
                df_view.index,
                format_func=lambda i: df_view.loc[i, "Promo"]
            )

            archivo = df_view.loc[selected_idx].get("Archivo_Path")
            if isinstance(archivo, str) and os.path.exists(archivo):
                if st.button("👁 Ver archivo"):
                    st.image(archivo, use_container_width=True)
            else:
                st.info("Esta promoción no tiene archivo adjunto.")

        # -------- Eliminar promoción (ADMIN) --------
        if st.session_state.is_admin and not df_view.empty:
            st.divider()
            st.subheader("🛠 Acciones administrativas")
            st.warning("⚠️ Esta acción no se puede deshacer")

            if st.checkbox("Confirmar eliminación"):
                if st.button("🗑 Eliminar promoción"):
                    df = df.drop(selected_idx)

                    # 🔒 PROTECCIÓN CSV
                    if len(df) == 0:
                        st.error("⚠️ ERROR: Eliminar dejaría el CSV vacío. Operación cancelada.")
                        st.stop()

                    df.to_csv(PROMOS_FILE, index=False)
                    st.success("Promoción eliminada correctamente ✅")
                    st.rerun()

# =============================
# NUEVA PROMOCIÓN (ADMIN)
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
            "Adjuntar imagen (PNG / JPG)",
            ["png", "jpg", "jpeg"]
        )

        notas = st.text_area("Notas / Restricciones")

        submit = st.form_submit_button("✅ Registrar promoción")

        if submit:
            if not promo or not hotels or not rate:
                st.error("Completa los campos obligatorios.")
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

            df = pd.concat([df, pd.DataFrame(rows)], ignore_index=True)

            # 🔒 PROTECCIÓN CSV
            if len(df) == 0:
                st.error("⚠️ ERROR: Intento de guardar CSV vacío. Operación cancelada.")
                st.stop()

            df.to_csv(PROMOS_FILE, index=False)
            st.success("🎉 Promoción registrada correctamente")
            st.rerun()

# =============================
# UPSELL (PLACEHOLDER)
# =============================
elif menu == "📈 Upsell":
    st.subheader("📈 Upsell")
    st.info(
        "Esta pestaña es solo un contenedor por ahora.\n\n"
        "Aquí implementaremos más adelante la calculadora de Upsell "
        "para Front Desk y Reservas, sin afectar promociones existentes."
    )
