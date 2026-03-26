import streamlit as st
import pandas as pd
import os
import io
from datetime import date

# ======================================
# CONFIGURACIÓN GENERAL
# ======================================
st.set_page_config(
    page_title="Administrador de Promociones",
    layout="wide"
)

CSV_FILE = "promociones_data.csv"
PASSWORD_MAESTRA = "PlayaMujeres2026"

# ======================================
# CSS MÍNIMO PARA CENTRAR TABS
# ======================================
st.markdown(
    """
    <style>
    /* Centrar el menú de tabs */
    div[data-baseweb="tab-list"] {
        justify-content: center;
    }

    /* Hacer las tabs más pequeñas y ligeras */
    button[data-baseweb="tab"] {
        font-size: 0.85rem;
        padding: 6px 14px;
        font-weight: 400;
    }

    /* Tab activa más sutil */
    button[data-baseweb="tab"][aria-selected="true"] {
        font-weight: 500;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# ======================================
# FUNCIONES
# ======================================
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
        "Notas"
    ])

# ======================================
# HEADER FINAL REFINADO
# (LOGO IZQUIERDA + TÍTULO CENTRADO, TODO MÁS A LA DERECHA)
# ======================================
col_left, col_logo, col_title, col_right = st.columns([1, 1, 2, 1])

with col_logo:
    if os.path.exists("HIC.png"):
        st.image("HIC.png", width=115)

with col_title:
    st.markdown("## Administrador de Promociones")
    st.markdown(
        "<span style='color: #6b6b6b;'>Playa Mujeres - DREPM & SECPM </span>",
        unsafe_allow_html=True
    )

# ======================================
# TABS PRINCIPALES
# ======================================
tab_promos, tab_registro, tab_admin = st.tabs(
    ["Promociones", "Registrar / Modificar", "Administración"]
)

# ===============================
# TAB 1 — PROMOCIONES
# ===============================
with tab_promos:
    col_left, col_center, col_right = st.columns([1, 3, 1])

    with col_center:
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

            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=False)

            st.download_button(
                label="Descargar Excel",
                data=buffer.getvalue(),
                file_name="Promociones_Playa_Mujeres.xlsx"
            )


# ======================================
# TAB 2 — REGISTRAR / MODIFICAR (CENTRADO)
# ======================================
with tab_registro:
    col_left, col_center, col_right = st.columns([1, 3, 1])

    with col_center:
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

            bw = st.date_input(
                "Booking Window",
                value=(date.today(), date.today())
            )

            tw = st.date_input(
                "Travel Window",
                value=(date.today(), date.today())
            )

            notas = st.text_area(
                "Notas / Restricciones",
                value=existente["Notas"].iloc[0] if editando else ""
            )

            col_a, col_b = st.columns(2)
            guardar = col_a.form_submit_button("Guardar")
            eliminar = col_b.form_submit_button("Eliminar") if editando else False

            if guardar:
                if not rate or not hoteles:
                    st.error("El Rate Plan y al menos una propiedad son obligatorios.")
                else:
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
                            "Notas": notas
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

# ======================================
# TAB 3 — ADMINISTRACIÓN
# ======================================
with tab_admin:
    col_left, col_center, col_right = st.columns([1, 2, 1])

    with col_center:
        st.subheader("Zona Administrativa")

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

