import streamlit as st
import pandas as pd
import os
import io
import time
from datetime import date, datetime

# =====================================================
# CONFIGURACIÓN GENERAL
# =====================================================
st.set_page_config(
    page_title="Administrador de Promociones",
    layout="wide"
)

CSV_FILE = "promociones_data.csv"
MEDIA_DIR = "media"
PASSWORD_MAESTRA = "PlayaMujeres2026"

MARKETS = ["US", "Canada", "Mexico", "LATAM", "Europe", "Asia / ROW"]
PROPERTIES = [
    "DREPM - Dreams Playa Mujeres",
    "SECPM - Secrets Playa Mujeres"
]

if not os.path.exists(MEDIA_DIR):
    os.makedirs(MEDIA_DIR)

# =====================================================
# CSS COMPACTO
# =====================================================
st.markdown("""
<style>
body { background-color: #f7f8fa; }
.block-container { padding-top: 0.9rem; }
div[data-baseweb="tab-list"] { justify-content: center; }
button[data-baseweb="tab"][aria-selected="true"] { font-weight: 600; }
div[data-testid="stVerticalBlock"] { gap: 0.4rem; }
</style>
""", unsafe_allow_html=True)

# =====================================================
# SPACER REAL (evita cortes del header)
# =====================================================
st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

# =====================================================
# SESSION STATE – INIT
# =====================================================
st.session_state.setdefault("promo", "")
st.session_state.setdefault("descuento", 0)
st.session_state.setdefault("bw", (date.today(), date.today()))
st.session_state.setdefault("tw", (date.today(), date.today()))
st.session_state.setdefault("rate_raw", "")
st.session_state.setdefault("hoteles", [])
st.session_state.setdefault("markets", [])
st.session_state.setdefault("notas", "")
st.session_state.setdefault("reset_form", False)

# =====================================================
# FUNCIÓN PARA CARGAR DATOS
# =====================================================
def cargar_datos():
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)

        for c in ["BW_Inicio", "BW_Fin", "TW_Inicio", "TW_Fin"]:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c]).dt.date

        for col in ["Market", "Archivo_Path"]:
            if col not in df.columns:
                df[col] = ""

        df["Market"] = df["Market"].apply(
            lambda x: x.split("|") if isinstance(x, str) and x else []
        )
        return df

    return pd.DataFrame(columns=[
        "Hotel","Market","Promo","Rate_Plan","Descuento",
        "BW_Inicio","BW_Fin","TW_Inicio","TW_Fin",
        "Notas","Archivo_Path"
    ])

# =====================================================
# FUNCIÓN EXCEL
# =====================================================
def exportar_excel(df):
    buffer = io.BytesIO()
    fecha = datetime.now().strftime("%Y-%m-%d")

    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        ws = writer.book.add_worksheet("Promociones")
        writer.sheets["Promociones"] = ws

        if os.path.exists("HIC.png"):
            ws.insert_image("A1", "HIC.png", {"x_scale": 0.4, "y_scale": 0.4})

        ws.write("E2", "Fecha de generación:")
        ws.write("F2", fecha)

        df_x = df.copy()
        df_x["Market"] = df_x["Market"].apply(lambda x: ", ".join(x))
        df_x["Archivo_Respaldo"] = df_x["Archivo_Path"].apply(
            lambda x: os.path.basename(x) if isinstance(x, str) and x else ""
        )
        df_x.drop(columns=["Archivo_Path"], inplace=True)

        df_x.to_excel(writer, index=False, startrow=4)
        for i in range(len(df_x.columns)):
            ws.set_column(i, i, 18)

    buffer.seek(0)
    return buffer

# =====================================================
# HEADER
# =====================================================
col_l, col_logo, col_title, col_r = st.columns([1,1,2,1])
with col_logo:
    st.image("HIC.png", width=80)
with col_title:
    st.markdown("## Administrador de Promociones")
    st.markdown(
        "<span style='color:#6b6b6b'>Playa Mujeres – DREPM & SECPM</span>",
        unsafe_allow_html=True
    )
st.markdown("<hr style='margin-top:6px; margin-bottom:8px;'>", unsafe_allow_html=True)

# =====================================================
# TABS
# =====================================================
tab_promos, tab_registro, tab_admin = st.tabs(
    ["Promociones","Registrar / Modificar","Administración"]
)

# =====================================================
# PROMOCIONES
# =====================================================
with tab_promos:
    df = cargar_datos()
    if df.empty:
        st.info("No hay promociones registradas.")
    else:
        view = df.copy()
        view["Market"] = view["Market"].apply(lambda x: ", ".join(x))
        st.dataframe(view, use_container_width=True)

        st.download_button(
            "Descargar Excel",
            exportar_excel(df),
            file_name="Promociones_Playa_Mujeres.xlsx"
        )

# =====================================================
# REGISTRAR / MODIFICAR
# =====================================================
with tab_registro:
    df = cargar_datos()

    # ✅ RESET SEGURO ANTES DE CREAR WIDGETS
    if st.session_state.reset_form:
        st.session_state.promo = ""
        st.session_state.descuento = 0
        st.session_state.bw = (date.today(), date.today())
        st.session_state.tw = (date.today(), date.today())
        st.session_state.rate_raw = ""
        st.session_state.hoteles = []
        st.session_state.markets = []
        st.session_state.notas = ""
        st.session_state.reset_form = False

    with st.form("form_registro"):
        col_promo, col_desc = st.columns([3,1])
        col_promo.text_input("Nombre de la promoción", key="promo")
        col_desc.number_input("Descuento (%)", 0, 100, 5, key="descuento")

        col_bw, col_tw = st.columns(2)
        col_bw.date_input("Booking Window", key="bw")
        col_tw.date_input("Travel Window", key="tw")

        st.text_area(
            "Rate Plan(s) – uno por línea",
            placeholder="BAR\nPROMO2026\nCORP_PM",
            height=90,
            key="rate_raw"
        )

        col_prop, col_market = st.columns(2)
        col_prop.multiselect("Propiedad(es)", PROPERTIES, key="hoteles")
        col_market.multiselect("Market(s)", MARKETS, key="markets")

        st.text_area(
            "Notas / Restricciones",
            height=80,
            key="notas"
        )

        guardar = st.form_submit_button("💾 Guardar")

        if guardar:
            rate_plans = [
                r.strip()
                for r in st.session_state.rate_raw.replace(",", "\n").split("\n")
                if r.strip()
            ]

            if not rate_plans or not st.session_state.hoteles or not st.session_state.markets:
                st.error("Rate Plan, Market y Propiedad son obligatorios.")
            else:
                rows = []
                for rp in rate_plans:
                    for h in st.session_state.hoteles:
                        rows.append({
                            "Hotel": h,
                            "Market": "|".join(st.session_state.markets),
                            "Promo": st.session_state.promo,
                            "Rate_Plan": rp,
                            "Descuento": st.session_state.descuento,
                            "BW_Inicio": st.session_state.bw[0],
                            "BW_Fin": st.session_state.bw[1],
                            "TW_Inicio": st.session_state.tw[0],
                            "TW_Fin": st.session_state.tw[1],
                            "Notas": st.session_state.notas,
                            "Archivo_Path": ""
                        })

                pd.concat([df, pd.DataFrame(rows)], ignore_index=True).to_csv(CSV_FILE, index=False)

                st.success("✅ Promoción guardada correctamente. Limpiando formulario…")
                st.session_state.reset_form = True
                time.sleep(1.2)
                st.rerun()

# =====================================================
# ADMINISTRACIÓN
# =====================================================
with tab_admin:
    clave = st.text_input("Clave Administrador", type="password")
    if clave == PASSWORD_MAESTRA:
        confirmar = st.checkbox("Confirmo borrar toda la base")
        if confirmar and st.button("🗑️ Borrar toda la base"):
            if os.path.exists(CSV_FILE):
                os.remove(CSV_FILE)
            st.warning("Base de datos eliminada")
            st.rerun()
