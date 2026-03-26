import streamlit as st
import pandas as pd
import os
import io
from datetime import date
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter

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
# CSS GLOBAL (CENTRADO + FONDO + TABS)
# =====================================================
st.markdown("""
<style>
body { background-color: #f7f8fa; }
.block-container { padding-top: 1.5rem; }
div[data-baseweb="tab-list"] { justify-content: center; }
button[data-baseweb="tab"] { font-size: 0.85rem; padding: 6px 14px; }
button[data-baseweb="tab"][aria-selected="true"] { font-weight: 500; }
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
        "Hotel",
        "Market",
        "Promo",
        "Rate_Plan",
        "Descuento",
        "BW_Inicio",
        "BW_Fin",
        "TW_Inicio",
        "TW_Fin",
        "Notas",
        "Archivo_Path"
    ])

def generar_pdf(df):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    data = [df.columns.tolist()] + df.values.tolist()
    table = Table(data, repeatRows=1)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("FONT", (0,0), (-1,0), "Helvetica-Bold")
    ]))

    doc.build([table])
    buffer.seek(0)
    return buffer

# =====================================================
# HEADER CENTRADO
# =====================================================
cl, c_logo, c_title, cr = st.columns([1,1,2,1])

with c_logo:
    if os.path.exists("HIC.png"):
        st.image("HIC.png", width=90)

with c_title:
    st.markdown("## Administrador de Promociones")
    st.markdown(
        "<span style='color:#6b6b6b'>Playa Mujeres – DREPM & SECPM</span>",
        unsafe_allow_html=True
    )

# =====================================================
# TABS
# =====================================================
tab_promos, tab_registro, tab_admin = st.tabs(
    ["Promociones", "Registrar / Modificar", "Administración"]
)

# =====================================================
# TAB PROMOCIONES
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

            # ---- Excel ----
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
                df_view.to_excel(writer, index=False)

            st.download_button(
                "Descargar Excel",
                excel_buffer.getvalue(),
                file_name="Promociones.xlsx"
            )

            # ---- PDF ----
            pdf_buffer = generar_pdf(df_view)
            st.download_button(
                "Descargar PDF",
                pdf_buffer,
                file_name="Promociones.pdf"
            )

# =====================================================
# TAB REGISTRAR / MODIFICAR
# =====================================================
with tab_registro:
    l, c, r = st.columns([1,3,1])

    with c:
        df = cargar_datos()
        rate = st.text_input("Rate Plan")

        existente = df[df["Rate_Plan"] == rate]
        editando = not existente.empty

        if editando:
            st.info("Editando promoción existente")

        with st.form("form_registro"):
            hoteles = st.multiselect(
                "Propiedad(es)",
                ["DREPM - Dreams Playa Mujeres", "SECPM - Secrets Playa Mujeres"],
                default=existente["Hotel"].tolist() if editando else []
            )

            markets = st.multiselect(
                "Market(s)",
                MARKETS,
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
                type=["pdf", "png", "jpg", "jpeg"]
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

                    st.success("Promoción guardada correctamente.")
                    st.rerun()

# =====================================================
# TAB ADMINISTRACIÓN
# =====================================================
with tab_admin:
    l, c, r = st.columns([1,2,1])

    with c:
        st.markdown("### Zona Administrativa")
        clave = st.text_input("Clave de administrador", type="password")

        if clave == PASSWORD_MAESTRA:
            st.success("Acceso autorizado")

            if st.button("Borrar toda la base"):
                if os.path.exists(CSV_FILE):
                    os.remove(CSV_FILE)
                    st.warning("Base de datos eliminada.")
                    st.rerun()
        elif clave:
            st.error("Clave incorrecta")
``
