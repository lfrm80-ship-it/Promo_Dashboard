import streamlit as st
import pandas as pd
import os
import io
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
# CSS COMPACTO (AJUSTADO PARA NO CORTAR HEADER)
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
# FUNCIONES
# =====================================================
def cargar_datos():
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)

        for c in ["BW_Inicio","BW_Fin","TW_Inicio","TW_Fin"]:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c]).dt.date

        for col in ["Market","Archivo_Path"]:
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

def exportar_excel(df):
    buffer = io.BytesIO()
    fecha = datetime.now().strftime("%Y-%m-%d")

    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        workbook = writer.book
        ws = workbook.add_worksheet("Promociones")
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
        df_x = df_x.drop(columns=["Archivo_Path"])

        df_x.to_excel(writer, index=False, startrow=4)
        for i, col in enumerate(df_x.columns):
            ws.set_column(i, i, 18)

    buffer.seek(0)
    return buffer

# =====================================================
# HEADER (CORREGIDO, SIN CORTES)
# =====================================================
col_l, col_logo, col_title, col_r = st.columns([1,1,2,1])

with col_logo:
    st.markdown("<div style='padding-top:4px'></div>", unsafe_allow_html=True)
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
    ["Promociones", "Registrar / Modificar", "Administración"]
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

        excel = exportar_excel(df)
        st.download_button(
            "Descargar Excel",
            excel,
            file_name="Promociones_Playa_Mujeres.xlsx"
        )

# =====================================================
# REGISTRAR / MODIFICAR (FORM COMPACTO, SIN SCROLL)
# =====================================================
with tab_registro:
    df = cargar_datos()

    with st.form("form_registro"):

        col_promo, col_desc = st.columns([3,1])
        promo = col_promo.text_input("Nombre de la promoción")
        descuento = col_desc.number_input("Descuento (%)", 0, 100, 5)

        col_bw, col_tw = st.columns(2)
        bw = col_bw.date_input("Booking Window", (date.today(), date.today()))
        tw = col_tw.date_input("Travel Window", (date.today(), date.today()))

        rate_raw = st.text_area(
            "Rate Plan(s) – uno por línea",
            placeholder="BAR\nPROMO2026\nCORP_PM",
            height=90
        )

        col_prop, col_market = st.columns(2)
        hoteles = col_prop.multiselect("Propiedad(es)", PROPERTIES)
        markets = col_market.multiselect("Market(s)", MARKETS)

        notas = st.text_area(
            "Notas / Restricciones",
            height=80,
            placeholder="Blackouts, restricciones, combinabilidad…"
        )

        archivo = st.file_uploader(
            "Archivo de respaldo (PDF / Imagen)",
            type=["pdf","png","jpg","jpeg"]
        )

        col_g, col_l, col_m = st.columns(3)
        guardar = col_g.form_submit_button("💾 Guardar")
        limpiar = col_l.form_submit_button("🧹 Limpiar")
        modificar = col_m.form_submit_button("✏️ Modificar")

        if limpiar:
            st.rerun()

        if guardar or modificar:
            rate_plans = [
                r.strip()
                for r in rate_raw.replace(",", "\n").split("\n")
                if r.strip()
            ]

            if not rate_plans or not hoteles or not markets:
                st.error("Rate Plan, Market y Propiedad son obligatorios.")
            else:
                archivo_path = ""
                if archivo:
                    archivo_path = os.path.join(MEDIA_DIR, archivo.name)
                    with open(archivo_path, "wb") as f:
                        f.write(archivo.getbuffer())

                if modificar:
                    df = df[~df["Rate_Plan"].isin(rate_plans)]

                rows = []
                for rate in rate_plans:
                    for h in hoteles:
                        rows.append({
                            "Hotel": h,
                            "Market": "|".join(markets),
                            "Promo": promo,
                            "Rate_Plan": rate,
                            "Descuento": descuento,
                            "BW_Inicio": bw[0],
                            "BW_Fin": bw[1],
                            "TW_Inicio": tw[0],
                            "TW_Fin": tw[1],
                            "Notas": notas,
                            "Archivo_Path": archivo_path
                        })

                df = pd.concat([df, pd.DataFrame(rows)], ignore_index=True)
                df.to_csv(CSV_FILE, index=False)

                st.success("✅ Promoción guardada correctamente")
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
            st.warning("Base eliminada")
            st.rerun()
``
