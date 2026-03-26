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

if not os.path.exists(MEDIA_DIR):
    os.makedirs(MEDIA_DIR)

# =====================================================
# CSS BÁSICO
# =====================================================
st.markdown("""
<style>
body { background-color: #f7f8fa; }
.block-container { padding-top: 1.5rem; }
div[data-baseweb="tab-list"] { justify-content: center; }
button[data-baseweb="tab"][aria-selected="true"] { font-weight: 600; }
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

        if "Market" not in df.columns:
            df["Market"] = ""
        df["Market"] = df["Market"].apply(
            lambda x: x.split("|") if isinstance(x, str) and x else []
        )

        if "Archivo_Path" not in df.columns:
            df["Archivo_Path"] = ""

        return df

    return pd.DataFrame(columns=[
        "Hotel","Market","Promo","Rate_Plan","Descuento",
        "BW_Inicio","BW_Fin","TW_Inicio","TW_Fin",
        "Notas","Archivo_Path"
    ])

def exportar_excel_con_logo(df):
    output = io.BytesIO()
    fecha = datetime.now().strftime("%Y-%m-%d")

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet("Promociones")
        writer.sheets["Promociones"] = worksheet

        if os.path.exists("HIC.png"):
            worksheet.insert_image("A1", "HIC.png", {"x_scale": 0.4, "y_scale": 0.4})

        worksheet.write("E2", "Fecha de generación:")
        worksheet.write("F2", fecha)

        df_x = df.copy()
        df_x["Market"] = df_x["Market"].apply(lambda x: ", ".join(x))
        df_x["Archivo_Respaldo"] = df_x["Archivo_Path"].apply(
            lambda x: os.path.basename(x) if isinstance(x, str) and x else ""
        )
        df_x = df_x.drop(columns=["Archivo_Path"])

        df_x.to_excel(writer, index=False, startrow=4)
        for i, col in enumerate(df_x.columns):
            worksheet.set_column(i, i, 18)

    output.seek(0)
    return output

# =====================================================
# BLOQUE DE BRANDING
# =====================================================
st.markdown("<div style='margin-top:20px'></div>", unsafe_allow_html=True)
col_l, col_logo, col_title, col_r = st.columns([1,1,2,1])

with col_logo:
    st.image("HIC.png", width=95)

with col_title:
    st.markdown("## Administrador de Promociones")
    st.markdown(
        "<span style='color:#6b6b6b'>Playa Mujeres – DREPM & SECPM</span>",
        unsafe_allow_html=True
    )

st.markdown("<hr style='margin-top:12px; margin-bottom:18px;'>", unsafe_allow_html=True)

# =====================================================
# TABS
# =====================================================
tab_promos, tab_registro, tab_admin = st.tabs(
    ["Promociones","Registrar / Modificar","Administración"]
)

# =====================================================
# TAB PROMOCIONES
# =====================================================
with tab_promos:
    l,c,r = st.columns([1,3,1])
    with c:
        df = cargar_datos()
        if df.empty:
            st.info("No hay promociones registradas.")
        else:
            df_view = df.copy()
            df_view["Market"] = df_view["Market"].apply(lambda x: ", ".join(x))
            st.dataframe(df_view, use_container_width=True)
            excel = exportar_excel_con_logo(df)
            st.download_button(
                "Descargar Excel",
                excel,
                file_name="Promociones_Playa_Mujeres.xlsx"
            )

# =====================================================
# TAB REGISTRAR / MODIFICAR (FORM PRO ✅)
# =====================================================
with tab_registro:
    l,c,r = st.columns([1,3,1])
    with c:
        df = cargar_datos()

        with st.form("form_registro"):

            # Nombre promo + Descuento
            col_promo, col_desc = st.columns([3,1])
            with col_promo:
                promo = st.text_input("Nombre de la promoción")
            with col_desc:
                descuento = st.number_input("Descuento (%)", 0, 100, 5)

            # Booking / Travel Window
            col_bw, col_tw = st.columns(2)
            with col_bw:
                bw = st.date_input("Booking Window", (date.today(), date.today()))
            with col_tw:
                tw = st.date_input("Travel Window", (date.today(), date.today()))

            # Rate Plan + Descuento MISMA LINEA
            col_rate, col_desc2 = st.columns([3,1])
            with col_rate:
                rate = st.text_input("Rate Plan")
            with col_desc2:
                descuento = st.number_input(
                    "Descuento (%)",
                    min_value=0,
                    max_value=100,
                    step=5
                )

            # Propiedad + Market
            col_prop, col_market = st.columns(2)
            with col_prop:
                hoteles = st.multiselect(
                    "Propiedad(es)",
                    ["DREPM - Dreams Playa Mujeres","SECPM - Secrets Playa Mujeres"]
                )
            with col_market:
                markets = st.multiselect("Market(s)", MARKETS)

            notas = st.text_area("Notas / Restricciones")

            archivo = st.file_uploader(
                "Archivo de respaldo (PDF / Imagen)",
                type=["pdf","png","jpg","jpeg"]
            )

            guardar = st.form_submit_button("Guardar")

            if guardar:
                if not rate or not hoteles or not markets:
                    st.error("Rate Plan, Market y Propiedad son obligatorios.")
                else:
                    archivo_path = ""
                    if archivo:
                        archivo_path = os.path.join(
                            MEDIA_DIR, f"{rate}_{archivo.name}"
                        )
                        with open(archivo_path,"wb") as f:
                            f.write(archivo.getbuffer())

                    rows = []
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
                    st.experimental_rerun()

# =====================================================
# ADMINISTRACIÓN
# =====================================================
with tab_admin:
    clave = st.text_input("Clave Admin", type="password")
    if clave == PASSWORD_MAESTRA:
        st.success("Acceso autorizado")
