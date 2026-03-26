import streamlit as st
import pandas as pd
import os
import io
from datetime import date

# ======================================
# CONFIGURACIÓN GENERAL (UNA SOLA VEZ)
# ======================================
st.set_page_config(
    page_title="Administrador de Promociones | Playa Mujeres",
    layout="wide"
)

PASSWORD_MAESTRA = "PlayaMujeres2026"
CSV_FILE = "promociones_data.csv"

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
        "Hotel", "Promo", "Rate_Plan", "Descuento",
        "BW_Inicio", "BW_Fin",
        "TW_Inicio", "TW_Fin",
        "Notas"
    ])

# ======================================
# HEADER PRINCIPAL
# ======================================
st.title("Administrador de Promociones")
st.caption("Playa Mujeres Complex — Dreams & Secrets")

tabs = st.tabs([
    "Promociones",
    "Registrar / Modificar",
    "Administración"
])

# ======================================
# TAB 1 — PROMOCIONES
# ======================================
with tabs[0]:
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
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as w:
            df.to_excel(w, index=False)

        st.download_button(
            "Descargar Excel",
            buffer.getvalue(),
            file_name="Promociones_Playa_Mujeres.xlsx"
        )

# ======================================
# TAB 2 — REGISTRAR / MODIFICAR
# ======================================
with tabs[1]:
    df = cargar_datos()

    rate = st.text_input("Rate Plan")

    existente = df[df["Rate_Plan"] == rate]
    editando = not existente.empty

    if editando:
        st.info("Editando promoción existente")

    with st.form("form_registro"):
        hoteles = st.multiselect(
            "Propiedad",
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
            0, 100, step=5,
            value=int(existente["Descuento"].iloc[0]) if editando else 0
        )

        bw = st.date_input("Booking Window", (date.today(), date.today()))
        tw = st.date_input("Travel Window", (date.today(), date.today()))

        notas = st.text_area(
            "Notas / Restricciones",
            value=existente["Notas"].iloc[0] if editando else ""
        )

        col1, col2 = st.columns(2)
        guardar = col1.form_submit_button("Guardar cambios")
        eliminar = col2.form_submit_button("Eliminar promoción") if editando else False

        if guardar:
            if not rate or not hoteles:
                st.error("Rate Plan y Propiedad son obligatorios")
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

                df = pd.concat([df, pd.DataFrame(registros)])
                df.to_csv(CSV_FILE, index=False)
                st.success("Promoción guardada")
                st.rerun()

        if eliminar:
            df = df[df["Rate_Plan"] != rate]
            df.to_csv(CSV_FILE, index=False)
            st.warning("Promoción eliminada")
            st.rerun()

# ======================================
# TAB 3 — ADMINISTRACIÓN
# ======================================
with tabs[2]:
    st.subheader("Zona Administrativa")

    clave = st.text_input("Clave de administrador", type="password")

    if clave == PASSWORD_MAESTRA:
        st.success("Acceso autorizado")

        if st.button("Borrar toda la base de datos"):
            if os.path.exists(CSV_FILE):
                os.remove(CSV_FILE)
                st.warning("Base de datos eliminada")
                st.rerun()
    elif clave:
        st.error("Clave incorrecta")
``
