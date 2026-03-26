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

if not os.path.exists(MEDIA_DIR):
    os.makedirs(MEDIA_DIR)

# =====================================================
# CSS GLOBAL (FONDO + TABS)
# =====================================================
st.markdown("""
<style>
body {
    background-color: #f7f8fa;
}

.block-container {
    padding-top: 1.5rem;
    background-color: #f7f8fa;
}

div[data-baseweb="tab-list"] {
    justify-content: center;
}

button[data-baseweb="tab"] {
    font-size: 0.85rem;
    padding: 6px 14px;
    font-weight: 400;
}

button[data-baseweb="tab"][aria-selected="true"] {
    font-weight: 500;
}

header {
    background-color: white;
    border-bottom: 1px solid #e6e6e6;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# FUNCIONES
# =====================================================
def cargar_datos():
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        for c in ["BW_Inicio", "BW_Fin", "TW_Inicio", "TW_Fin"]:
            df[c] = pd.to_datetime(df[c]).dt.date
        return df

    return pd.DataFrame(columns=[
        "Hotel",
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
col_l, col_logo, col_t, col_r = st.columns([1, 1, 2, 1])

with col_logo:
    if os.path.exists("HIC.png"):
        st.image("HIC.png", width=95)

with col_t:
    st.markdown("## Administrador de Promociones")
    st.markdown(
        "<span style='color:#6b6b6b;'>Playa Mujeres – DREPM & SECPM</span>",
        unsafe_allow_html=True
    )

# =====================================================
# TABS
# =====================================================
tab_promos, tab_registro, tab_admin = st.tabs(
    ["Promociones", "Registrar / Modificar", "Administración"]
)

# =====================================================
# TAB 1 — PROMOCIONES
# =====================================================
with tab_promos:
    cl, cc, cr = st.columns([1, 3, 1])

    with cc:
        st.markdown("### Promociones")

        df = cargar_datos()

        if df.empty:
            st.info("No hay promociones registradas.")
        else:
            filtro = st.text_input("Buscar promoción")

            if filtro:
                df = df[df.astype(str).apply(
                    lambda x: x.str.contains(filtro, case=False)
                ).any(axis=1)]

            st.dataframe(df, use_container_width=True)

            # Excel
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=False)

            st.download_button(
                "Descargar Excel",
                buffer.getvalue(),
                file_name="Promociones_Playa_Mujeres.xlsx"
            )

            # Archivos
            st.markdown("#### Archivos de respaldo")
            for _, r in df.iterrows():
                archivo_path = r["Archivo_Path"]

                if isinstance(archivo_path, str) and archivo_path and os.path.exists(archivo_path):
                    with open(archivo_path, "rb") as f:
                        st.download_button(
                            label=f"Descargar – {r['Rate_Plan']}",
                            data=f,
                            file_name=os.path.basename(archivo_path)
                        )

# =====================================================
# TAB 2 — REGISTRAR / MODIFICAR
# =====================================================
with tab_registro:
    cl, cc, cr = st.columns([1, 3, 1])

    with cc:
        df = cargar_datos()
        rate = st.text_input("Rate Plan")

        existente = df[df["Rate_Plan"] == rate]
        editando = not existente.empty

        if editando:
            st.info("Editando promoción existente")

        with st.form("form_registro"):
            hoteles = st.multiselect(
                "Propiedad(es)",
                [
                    "DREPM - Dreams Playa Mujeres",
                    "SECPM - Secrets Playa Mujeres"
                ],
                default=existente["Hotel"].tolist() if editando else []
            )

            promo = st.text_input(
                "Nombre de la promoción",
                value=existente["Promo"].iloc[0] if editando else ""
            )

            descuento = st.number_input(
                "Descuento (%)",
                min_value=0,
                max_value=100,
                step=5,
                value=int(existente["Descuento"].iloc[0]) if editando else 0
            )

            bw = st.date_input("Booking Window", (date.today(), date.today()))
            tw = st.date_input("Travel Window", (date.today(), date.today()))
            notas = st.text_area("Notas / Restricciones")

            archivo = st.file_uploader(
                "Archivo de respaldo (PDF o Imagen)",
                type=["pdf", "png", "jpg", "jpeg"]
            )

            g_col, d_col = st.columns(2)
            guardar = g_col.form_submit_button("Guardar")
            eliminar = d_col.form_submit_button("Eliminar") if editando else False

            if guardar:
                if not rate or not hoteles:
                    st.error("Rate Plan y al menos una propiedad son obligatorios.")
                else:
                    archivo_path = ""
                    if archivo:
                        archivo_path = os.path.join(
                            MEDIA_DIR,
                            f"{rate}_{archivo.name}"
                        )
                        with open(archivo_path, "wb") as f:
                            f.write(archivo.getbuffer())

                    df = df[df["Rate_Plan"] != rate]

                    registros = []
                    for h in hoteles:
                        registros.append({
                            "Hotel": h,
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

                    df = pd.concat([df, pd.DataFrame(registros)], ignore_index=True)
                    df.to_csv(CSV_FILE, index=False)

                    st.success("Promoción guardada correctamente.")
                    st.rerun()

            if eliminar:
                df = df[df["Rate_Plan"] != rate]
                df.to_csv(CSV_FILE, index=False)
                st.warning("Promoción eliminada.")
                st.rerun()

# =====================================================
# TAB 3 — ADMINISTRACIÓN
# =====================================================
with tab_admin:
    cl, cc, cr = st.columns([1, 2, 1])

    with cc:
        st.markdown("### Zona Administrativa")

        clave = st.text_input("Clave de administrador", type="password")

        if clave == PASSWORD_MAESTRA:
            st.success("Acceso autorizado")

            if st.button("Borrar toda la base de datos"):
                if os.path.exists(CSV_FILE):
                    os.remove(CSV_FILE)
                    st.warning("Base de datos eliminada.")
                    st.rerun()
        elif clave:
            st.error("Clave incorrecta")
