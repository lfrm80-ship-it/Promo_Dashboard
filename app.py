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
header { background-color: white; border-bottom: 1px solid #e6e6e6; }
</style>
""", unsafe_allow_html=True)

# =====================================================
# FUNCIONES
# =====================================================
def cargar_datos():
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)

        for c in ["BW_Inicio", "BW_Fin", "TW_Inicio", "TW_Fin"]:
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
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet("Promociones")
        writer.sheets["Promociones"] = worksheet

        # Logo
        if os.path.exists("HIC.png"):
            worksheet.insert_image("A1", "HIC.png", {"x_scale": 0.4, "y_scale": 0.4})

        # Fecha
        worksheet.write("E2", f"Fecha de generación:")
        worksheet.write("F2", fecha_hoy)

        # Preparar dataframe
        df_x = df.copy()
        df_x["Market"] = df_x["Market"].apply(lambda x: ", ".join(x))
        df_x["Archivo_Respaldo"] = df_x["Archivo_Path"].apply(
            lambda x: os.path.basename(x) if isinstance(x, str) and x else ""
        )
        df_x = df_x.drop(columns=["Archivo_Path"])

        start_row = 4
        df_x.to_excel(writer, index=False, startrow=start_row)

        # Ajustar ancho de columnas
        for i, col in enumerate(df_x.columns):
            worksheet.set_column(i, i, max(18, len(col) + 2))

    output.seek(0)
    return output

# =====================================================
# HEADER
# =====================================================
cl, c_logo, c_title, cr = st.columns([1,1,2,1])

with c_logo:
    if os.path.exists("HIC.png"):
        st.image("HIC.png", width=90)

with c_title:
    st.markdown("## Administrador de Promociones")
    st.caption("Playa Mujeres – DREPM & SECPM")

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
    l, c, r = st.columns([1,3,1])

    with c:
        st.markdown("### Promociones")
        df = cargar_datos()

        if df.empty:
            st.info("No hay promociones registradas.")
        else:
            filtro = st.text_input("Buscar")
            if filtro:
                df = df[df.astype(str).apply(
                    lambda x: x.str.contains(filtro, case=False)
                ).any(axis=1)]

            df_view = df.copy()
            df_view["Market"] = df_view["Market"].apply(lambda x: ", ".join(x))
            st.dataframe(df_view, use_container_width=True)

            excel_buffer = exportar_excel_con_logo(df)

            st.download_button(
                "Descargar Excel",
                excel_buffer,
                file_name="Promociones_Playa_Mujeres.xlsx"
            )

# =====================================================
# REGISTRAR / MODIFICAR
# =====================================================
with tab_registro:
    l, c, r = st.columns([1,3,1])

    with c:
        df = cargar_datos()
        rate = st.text_input("Rate Plan")

        existente = df[df["Rate_Plan"] == rate]
        editando = not existente.empty

        with st.form("form"):
            hoteles = st.multiselect(
                "Propiedad(es)",
                ["DREPM - Dreams Playa Mujeres", "SECPM - Secrets Playa Mujeres"],
                default=existente["Hotel"].tolist() if editando else []
            )

            markets = st.multiselect(
                "Market(s)", MARKETS,
                default=existente["Market"].iloc[0] if editando else []
            )

            promo = st.text_input(
                "Nombre de la promoción",
                value=existente["Promo"].iloc[0] if editando else ""
            )

            descuento = st.number_input("Descuento (%)", 0, 100, 5)
            bw = st.date_input("Booking Window", (date.today(), date.today()))
            tw = st.date_input("Travel Window", (date.today(), date.today()))
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
                        archivo_path = os.path.join(MEDIA_DIR, f"{rate}_{archivo.name}")
                        with open(archivo_path, "wb") as f:
                            f.write(archivo.getbuffer())

                    df = df[df["Rate_Plan"] != rate]

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

                    st.success("Promoción guardada.")
                    st.rerun()

# =====================================================
# ADMIN
# =====================================================
with tab_admin:
    clave = st.text_input("Clave Admin", type="password")
    if clave == PASSWORD_MAESTRA:
        st.success("Acceso autorizado")

