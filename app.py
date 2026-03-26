import streamlit as st
import pandas as pd
import os
import io
from datetime import date

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
# CSS GLOBAL
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

        # ✅ FECHAS
        for c in ["BW_Inicio", "BW_Fin", "TW_Inicio", "TW_Fin"]:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c]).dt.date

        # ✅ MARKET (backward compatible)
        if "Market" not in df.columns:
            df["Market"] = ""

        df["Market"] = df["Market"].apply(
            lambda x: x.split("|") if isinstance(x, str) and x else []
        )

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

# =====================================================
# HEADER
# =====================================================
col_l, col_logo, col_title, col_r = st.columns([1, 1, 2, 1])

with col_logo:
    if os.path.exists("HIC.png"):
        st.image("HIC.png", width=90)

with col_title:
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
# PROMOCIONES
# =====================================================
with tab_promos:
    col_l, col_c, col_r = st.columns([1, 3, 1])

    with col_c:
        st.markdown("### Promociones")
        ...
``
    else:
        df_view = df.copy()
        df_view["Market"] = df_view["Market"].apply(lambda x: ", ".join(x))
        st.dataframe(df_view, use_container_width=True)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df_view.to_excel(writer, index=False)

        st.download_button(
            "Descargar Excel",
            buffer.getvalue(),
            file_name="Promociones.xlsx"
        )

# =====================================================
# REGISTRAR / MODIFICAR
# =====================================================
with tab_registro:
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
        notas = st.text_area("Notas")

        archivo = st.file_uploader(
            "Archivo respaldo (PDF / Imagen)",
            type=["pdf", "png", "jpg", "jpeg"]
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
        if st.button("Borrar BD"):
            os.remove(CSV_FILE)
            st.warning("Base eliminada")
            st.rerun()
