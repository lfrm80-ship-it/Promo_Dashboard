import streamlit as st
import pandas as pd
import os
import io
from datetime import date

# ======================================
# CONFIGURACIÓN
# ======================================
st.set_page_config(
    page_title="Promociones DREPM & SECPM | Hyatt AI",
    layout="wide"
)

PASSWORD_MAESTRA = "PlayaMujeres2026"
CSV_FILE = "promociones_data.csv"
MEDIA_DIR = "media"

if not os.path.exists(MEDIA_DIR):
    os.makedirs(MEDIA_DIR)

# ======================================
# CSS SEGURO (SIN TRIPLE COMILLAS)
# ======================================
st.markdown(
    "<style>"
    ".block-container { padding-top: 2rem; }"
    ".sidebar-divider { margin: 1rem 0; border-bottom: 1px solid #e0e0e0; }"
    "</style>",
    unsafe_allow_html=True
)

# ======================================
# SIDEBAR
# ======================================
with st.sidebar:
    if os.path.exists("HIC.png"):
        st.image("HIC.png", width=140)
    else:
        st.markdown("### 🏨 Hyatt Inclusive Collection")
        st.caption("Playa Mujeres Complex")

    st.markdown("<div class='sidebar-divider'></div>", unsafe_allow_html=True)

    st.markdown("#### Guía rápida")
    st.markdown("- 🆕 Limpiar formulario")
    st.markdown("- 💾 Guardar promoción")
    st.markdown("- 🔄 Actualizar existente")
    st.markdown("- 📥 Descargar reporte")

    st.markdown("<div class='sidebar-divider'></div>", unsafe_allow_html=True)

    with st.expander("🔐 Zona Administrador"):
        pass_input = st.text_input("Clave maestra", type="password")
        if pass_input == PASSWORD_MAESTRA:
            st.success("Acceso autorizado")
            if st.button("⚠️ Borrar toda la base"):
                if os.path.exists(CSV_FILE):
                    os.remove(CSV_FILE)
                    st.warning("Base eliminada")
                    st.rerun()
        elif pass_input != "":
            st.error("Contraseña incorrecta")

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
        "Notas", "Archivo_Path"
    ])

# ======================================
# HEADER
# ======================================
st.title("🏨 Dashboard Maestro de Promociones")
st.caption("Administración centralizada de promociones – DREPM & SECPM")

tab_buscar, tab_registrar = st.tabs([
    "🔍 Buscador & Reportes",
    "➕ Registrar / Modificar"
])

# ======================================
# TAB REGISTRAR
# ======================================
with tab_registrar:
    df = cargar_datos()

    if st.button("🧹 Limpiar formulario"):
        st.rerun()

    rate = st.text_input("🔑 Rate Plan")

    existente = df[df["Rate_Plan"] == rate]
    editando = not existente.empty

    with st.form("form_registro"):
        hoteles = st.multiselect(
            "Propiedad",
            ["DREPM - Dreams Playa Mujeres", "SECPM - Secrets Playa Mujeres"],
            default=existente["Hotel"].tolist() if editando else []
        )

        promo = st.text_input(
            "Nombre de la promoción",
            value=existente["Promo"].iloc[0] if editando else ""
        )

        descuento = st.number_input(
            "% Descuento",
            0, 100, step=5,
            value=int(existente["Descuento"].iloc[0]) if editando else 0
        )

        bw = st.date_input("Booking Window", (date.today(), date.today()))
        tw = st.date_input("Travel Window", (date.today(), date.today()))

        notas = st.text_area(
            "Notas",
            value=existente["Notas"].iloc[0] if editando else ""
        )

        guardar = st.form_submit_button("💾 Guardar / Actualizar")
        eliminar = st.form_submit_button("🗑️ Eliminar") if editando else False

        if guardar:
            if not rate or not hoteles:
                st.error("Falta Rate Plan o Propiedad")
            else:
                df = df[df["Rate_Plan"] != rate]

                nuevos = []
                for h in hoteles:
                    nuevos.append({
                        "Hotel": h,
                        "Promo": promo,
                        "Rate_Plan": rate,
                        "Descuento": descuento,
                        "BW_Inicio": bw[0],
                        "BW_Fin": bw[1],
                        "TW_Inicio": tw[0],
                        "TW_Fin": tw[1],
                        "Notas": notas,
                        "Archivo_Path": ""
                    })

                df = pd.concat([df, pd.DataFrame(nuevos)])
                df.to_csv(CSV_FILE, index=False)
                st.success("✅ Guardado")
                st.rerun()

        if eliminar:
            df = df[df["Rate_Plan"] != rate]
            df.to_csv(CSV_FILE, index=False)
            st.warning("❌ Eliminado")
            st.rerun()

# ======================================
# TAB BUSCADOR
# ======================================
with tab_buscar:
    df = cargar_datos()

    if df.empty:
        st.info("No hay promociones registradas.")
    else:
        filtro = st.text_input("🔎 Buscar")
        if filtro:
            df = df[df.astype(str).apply(
                lambda x: x.str.contains(filtro, case=False)
            ).any(axis=1)]

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as w:
            df.to_excel(w, index=False)

        st.download_button(
            "📥 Descargar Excel",
            buffer.getvalue(),
            file_name="Promociones.xlsx"
        )

        for _, r in df.iterrows():
            with st.container(border=True):
                st.markdown(f"**{r['Hotel']} | {r['Promo']}**")
                st.markdown(f"Rate: `{r['Rate_Plan']}`")
                st.markdown(
                    f"Viaje: {r['TW_Inicio']} → {r['TW_Fin']} | "
                    f"{r['Descuento']}% OFF"
                )
``
import streamlit as st

st.set_page_config(page_title="Test App", layout="wide")

st.title("Aplicación de prueba")
st.write("Si ves esto, tu entorno Streamlit está bien.")

if st.button("Probar"):
    st.success("Todo OK")

