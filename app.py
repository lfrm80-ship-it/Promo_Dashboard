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
        df = pd.read_csv(PROMOS_FILE, sep=None, engine="python")
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
    if hoy < tw_i:
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

    # 🔽 BAJAMOS EL BLOQUE DE ADMIN
    st.markdown("<br><br>", unsafe_allow_html=True)
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
# NUEVA PROMOCIÓN
# =============================
elif menu == "➕ Nueva promoción":

    with st.form("new_promo", clear_on_submit=True):

        # =============================
        # CARGA MANUAL
        # =============================
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

        # =============================
        # FECHAS EN UNA SOLA LÍNEA
        # =============================
        c_bw_i, c_bw_f, c_tw_i, c_tw_f = st.columns(4)
        with c_bw_i:
            bw_i = st.date_input("BW Inicio")
        with c_bw_f:
            bw_f = st.date_input("BW Fin")
        with c_tw_i:
            tw_i = st.date_input("TW Inicio")
        with c_tw_f:
            tw_f = st.date_input("TW Fin")

        # =============================
        # IMAGEN
        # =============================
        imagen_file = st.file_uploader(
            "Adjuntar imagen (PNG / JPG)",
            ["png", "jpg", "jpeg"]
        )

        notas = st.text_area("Notas / Restricciones")

        st.divider()

        # =============================
        # EXCEL (HASTA ABAJO)
        # =============================
        st.subheader("📥 Carga masiva desde Excel (opcional)")
        excel_file = st.file_uploader(
            "Subir archivo Excel (.xlsx / .xls)",
            ["xlsx", "xls"]
        )

        submit = st.form_submit_button("✅ Guardar")

        # =============================
        # GUARDADO
        # =============================
        if submit:

            # ---- EXCEL ----
            if excel_file is not None:
                df_excel = pd.read_excel(excel_file)

                if df_excel.empty:
                    st.error("El Excel está vacío.")
                    st.stop()

                df = pd.concat([df, df_excel], ignore_index=True)

            # ---- MANUAL ----
            elif promo and hotels and rate:

                archivo_path = ""
                if imagen_file:
                    archivo_path = os.path.join(MEDIA_DIR, imagen_file.name)
                    with open(archivo_path, "wb") as f:
                        f.write(imagen_file.getbuffer())

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

            else:
                st.error("Sube un Excel o completa el formulario manual.")
                st.stop()

            # ---- PROTECCIÓN CSV ----
            if len(df) == 0:
                st.error("Error: el CSV quedaría vacío.")
                st.stop()

            df.to_csv(PROMOS_FILE, index=False)
            st.success("✅ Promociones guardadas correctamente")
            st.rerun()

# =============================
# UPSELL (PLACEHOLDER)
# =============================
elif menu == "📈 Upsell":
    st.subheader("📈 Upsell")

    col1, col2 = st.columns([1, 2])

    with col1:
        hotel = st.selectbox("Hotel", ["DREPM", "SECPM"])
        habitacion = st.selectbox("Habitación actual", [
            "JS Garden View",
            "JS Pool View",
            "JS Ocean View"
        ])
        tarifa = st.number_input("Tarifa actual por noche", min_value=0)
        noches = st.number_input("Noches", min_value=1)
        periodo = st.selectbox("Periodo", ["Regular", "Holiday"])

        calcular = st.button("Calcular Upsell")

    with col2:
        if calcular:
            st.info("Aquí mostraremos las categorías superiores y el precio adicional.")
