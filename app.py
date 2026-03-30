import streamlit as st
import pandas as pd
import os
import io
from datetime import datetime, date

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
# FUNCIONES PROMOS
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
# REGLAS OK RM – NIÑOS
# =============================
OK_RM_RULES = {
    2026: {
        "ok_rm": [
            ("2026-03-26", "2026-04-13"),
            ("2026-12-21", "2026-12-31")
        ],
        "regular": {"net": 67, "pub": 89},
        "ok": {"net": 111, "pub": 148}
    },
    2027: {
        "ok_rm": [
            ("2027-03-20", "2027-04-11"),
            ("2027-12-21", "2028-01-04")
        ],
        "regular": {"net": 71, "pub": 95},
        "ok": {"net": 118, "pub": 157}
    }
}

TC_MXN = 18.50


def detectar_ok_rm(fecha_llegada: date):
    reglas = OK_RM_RULES.get(fecha_llegada.year)
    if not reglas:
        return None, None

    for inicio, fin in reglas["ok_rm"]:
        inicio_dt = datetime.strptime(inicio, "%Y-%m-%d").date()
        fin_dt = datetime.strptime(fin, "%Y-%m-%d").date()
        if inicio_dt <= fecha_llegada <= fin_dt:
            return "OK RM", reglas["ok"]

    return "REGULAR", reglas["regular"]

# =============================
# SIDEBAR
# =============================
with st.sidebar:
    st.image("HIC.png", use_container_width=True)
    st.divider()

    menu = st.radio(
        "Navegación",
        ["🔍 Vista rápida", "➕ Nueva promoción", "📈 Upsell"]
        if st.session_state.is_admin
        else ["🔍 Vista rápida", "📈 Upsell"]
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
# DATA
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

        c_bw_i, c_bw_f, c_tw_i, c_tw_f = st.columns(4)
        bw_i = c_bw_i.date_input("BW Inicio")
        bw_f = c_bw_f.date_input("BW Fin")
        tw_i = c_tw_i.date_input("TW Inicio")
        tw_f = c_tw_f.date_input("TW Fin")

        imagen_file = st.file_uploader("Adjuntar imagen", ["png", "jpg", "jpeg"])
        notas = st.text_area("Notas / Restricciones")

        st.divider()

        excel_file = st.file_uploader("📥 Carga masiva desde Excel", ["xlsx", "xls"])
        submit = st.form_submit_button("✅ Guardar")

        if submit:
            if excel_file is not None:
                df_excel = pd.read_excel(excel_file)
                df = pd.concat([df, df_excel], ignore_index=True)

            elif promo and hotels and rate:
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
                st.error("Completa los campos.")
                st.stop()

            df.to_csv(PROMOS_FILE, index=False)
            st.success("✅ Promoción guardada")
            st.rerun()
# =============================
# UPSELL ✅
# =============================
if menu == "📈 Upsell":
    st.subheader("📈 Upsell")

    HABITACIONES = [
        "JS Garden View",
        "JS Pool View",
        "JS Ocean View",
        "JS Swim Out"
    ]

    col1, col2 = st.columns([1, 1])

    # =============================
    # INPUTS (COLUMNA IZQUIERDA)
    # =============================
    with col1:

        # --- Contexto (una fila)
        col_hotel, col_fecha = st.columns(2)
        with col_hotel:
            hotel = st.selectbox("Hotel", ["DREPM", "SECPM"])
        with col_fecha:
            fecha = st.date_input("Fecha", value=date(2026, 4, 1))

        # --- Upsell de habitación (De → A en una sola línea)
        col_from, col_arrow, col_to = st.columns([4, 1, 4])

        with col_from:
            habitacion_actual = st.selectbox("De", HABITACIONES)

        with col_arrow:
            st.markdown("<br>➡️", unsafe_allow_html=True)

        idx = HABITACIONES.index(habitacion_actual)
        opciones_upsell = HABITACIONES[idx + 1:]

        with col_to:
            habitacion_destino = st.selectbox(
                "A",
                opciones_upsell if opciones_upsell else ["No hay opciones"]
            )

        # --- Ocupación (Adultos + Niños en la misma fila)
        col_ad, col_nin = st.columns(2)

        if hotel == "DREPM":
            with col_ad:
                adultos = st.number_input("Adultos", 1, 4, 2)
            with col_nin:
                ninos = st.number_input("Niños", 0, 4, 0)
        else:
            with col_ad:
                adultos = st.number_input("Adultos", 1, 3, 2)
            ninos = 0
            st.caption("ℹ️ Resort solo adultos (18+)")

        # --- Impacto económico (una fila)
        col_tarifa, col_noches = st.columns(2)
        with col_tarifa:
            tarifa = st.number_input("Tarifa USD", value=500, step=50)
        with col_noches:
            noches = st.number_input("Noches", value=1)

        calcular = st.button("Calcular Upsell", use_container_width=True)

    # =============================
    # RESULTADOS (COLUMNA DERECHA)
    # =============================
    with col2:
        if calcular:
            st.markdown("🔄 **Calculando Upsell…**")

            temporada, precios = detectar_ok_rm(fecha)

            if not precios:
                st.error(
                    "⚠️ No hay reglas de temporada configuradas para esta fecha."
                )
            else:
                st.success(f"✅ Temporada: **{temporada}**")

                st.markdown(f"""
### 🏨 Upsell de habitación
**De:** {habitacion_actual}  
**A:** {habitacion_destino}
""")

                if hotel == "DREPM" and ninos > 0:
                    net, pub = precios["net"], precios["pub"]

                    st.markdown(f"""
### 👶 Cargos por niño (3–12 años)

- **NET:** {net} USD / {round(net * TC_MXN):,} MXN  
- **PUBLIC:** {pub} USD / {round(pub * TC_MXN):,} MXN  
""")

                    st.markdown("""
### 👶 Edades de niños (referencia)

- **0–2 años:** Gratis  
- **3–12 años:** Aplica cargo  
- **13+ años:** Adulto  

🏊 **Swim Out:** No acepta niños
""")

                incremento = 75 * noches
                st.markdown(f"""
### 💰 Upsell estimado
💵 **Incremento total:** **${incremento} USD**
""")
        else:
            st.info("⬅️ Ingresa los datos y presiona **Calcular Upsell**")
