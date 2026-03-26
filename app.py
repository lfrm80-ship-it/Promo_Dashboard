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

# =====================================================
# BRANDING
# =====================================================
st.markdown("<div style='margin-top:20px'></div>", unsafe_allow_html=True)

col_l, col_logo, col_title, col_r = st.columns([1, 1, 2, 1])
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
    ["Promociones", "Registrar / Modificar", "Administración"]
)

# =====================================================
# TAB REGISTRAR / MODIFICAR ✅ FORM BIEN DEFINIDO
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

        # ✅ TODO lo del formulario vive AQUÍ
        with st.form("form_registro"):

            # Propiedad + Market
            col_prop, col_market = st.columns(2)
            with col_prop:
                hoteles = st.multiselect(
                    "Propiedad(es)",
                    ["DREPM - Dreams Playa Mujeres", "SECPM - Secrets Playa Mujeres"],
                    default=existente["Hotel"].tolist() if editando else []
                )
            with col_market:
                markets = st.multiselect(
                    "Market(s)",
                    MARKETS,
                    default=existente["Market"].iloc[0] if editando else []
                )

            # Promo + Descuento
            col_promo, col_desc = st.columns([3,1])
            with col_promo:
                promo = st.text_input(
                    "Nombre de la promoción",
                    value=existente["Promo"].iloc[0] if editando else ""
                )
            with col_desc:
                descuento = st.number_input(
                    "Descuento (%)",
                    min_value=0,
                    max_value=100,
                    step=5,
                    value=int(existente["Descuento"].iloc[0]) if editando else 0
                )

            # BW - TW
            st.markdown("** **")
            col_bw, col_tw = st.columns(2)
            with col_bw:
                bw = st.date_input(
                    "Booking Window",
                    value=(date.today(), date.today())
                )
            with col_tw:
                tw = st.date_input(
                    "Travel Window",
                    value=(date.today(), date.today())
                )

            notas = st.text_area("Notas / Restricciones")

            archivo = st.file_uploader(
                "Archivo de respaldo (PDF / Imagen)",
                type=["pdf","png","jpg","jpeg"]
            )

            # ✅ SUBMIT DENTRO DEL FORM (CLAVE)
            guardar = st.form_submit_button("Guardar")

            # ✅ LÓGICA AL SUBMIT
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

                    st.success("✅ Promoción guardada correctamente")
                    st.experimental_rerun()
