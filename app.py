import streamlit as st
import pandas as pd
import os
import io
from datetime import date

# ======================================================
# CONFIGURACIÓN GENERAL
# ======================================================
st.set_page_config(
    page_title="Promociones DREPM & SECPM | Hyatt AI",
    layout="wide"
)

PASSWORD_MAESTRA = "PlayaMujeres2026"
CSV_FILE = "promociones_data.csv"
MEDIA_DIR = "media"

if not os.path.exists(MEDIA_DIR):
    os.makedirs(MEDIA_DIR)

# ======================================================
# ✅ CSS – TODO DENTRO DEL STRING (FIX DEL ERROR)
# ======================================================
st.markdown(
    "<style>"
    ".block-container { padding-top: 2rem; }"
    ".sidebar-divider { margin: 1rem 0; border-bottom: 1px solid #e0e0e0; }"
    ".card-title { font-weight: 600; font-size: 1.1rem; }"
    ".small-muted { color: #6b6b6b; font-size: 0.9rem; }"
    "</style>",
    unsafe_allow_html=True
)
``

# ======================================================
# SIDEBAR
# ======================================================
with st.sidebar:
    try:
        st.image("HIC.png", width=140)
    except:
        st.markdown("### 🏨 Hyatt Inclusive Collection")
        st.caption("Playa Mujeres Complex")

    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

    st.markdown("#### Guía rápida")
    st.markdown("""
    - 🆕 Limpiar formulario  
    - 💾 Guardar promoción  
    - 🔄 Actualizar existente  
    - 📥 Descargar reporte  
    """)

    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

    with st.expander("🔐 Zona Administrador"):
        st.caption("Acceso restringido – acción irreversible")
        pass_input = st.text_input("Clave maestra", type="password")

        if pass_input == PASSWORD_MAESTRA:
            st.success("Acceso autorizado")
            if st.button("⚠️ Borrar toda la base"):
                if os.path.exists(CSV_FILE):
                    os.remove(CSV_FILE)
                    st.warning("Base eliminada")
                    st.rerun()
        elif pass_input:
            st.error("Contraseña incorrecta")

# ======================================================
# FUNCIONES
# ======================================================
def cargar_datos():
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        for col in ["BW_Inicio", "BW_Fin", "TW_Inicio", "TW_Fin"]:
            df[col] = pd.to_datetime(df[col]).dt.date
        return df

    return pd.DataFrame(columns=[
        "Hotel", "Promo", "Rate_Plan", "Descuento",
        "BW_Inicio", "BW_Fin",
        "TW_Inicio", "TW_Fin",
        "Notas", "Archivo_Path"
    ])

# ======================================================
# HEADER PRINCIPAL
# ======================================================
st.title("🏨 Dashboard Maestro de Promociones")
st.caption("Administración centralizada de promociones – DREPM & SECPM")

tab_buscar, tab_registrar = st.tabs([
    "🔍 Buscador & Reportes",
    "➕ Registrar / Modificar"
])

# ======================================================
# TAB REGISTRAR / MODIFICAR
# ======================================================
with tab_registrar:
    df_actual = cargar_datos()

    col_a, col_b = st.columns([3, 1])
    with col_b:
        if st.button("🧹 Limpiar formulario", use_container_width=True):
            st.rerun()

    rate_a_buscar = st.text_input(
        "🔑 Rate Plan",
        help="Escribe el código para crear o modificar una promoción"
    )

    promo_existente = df_actual[df_actual["Rate_Plan"] == rate_a_buscar]
    es_mod = not promo_existente.empty

    if es_mod:
        st.info(f"Editando promoción existente: `{rate_a_buscar}`")

    with st.form("registro_form"):
        col1, col2 = st.columns(2)

        hoteles_opciones = [
            "DREPM - Dreams Playa Mujeres",
            "SECPM - Secrets Playa Mujeres"
        ]

        hoteles = col1.multiselect(
            "Propiedad(es)",
            hoteles_opciones,
            default=promo_existente["Hotel"].unique().tolist() if es_mod else []
        )

        promo = col2.text_input(
            "Nombre de la promoción",
            value=promo_existente["Promo"].iloc[0] if es_mod else ""
        )

        col3, col4 = st.columns(2)
        descuento = col3.number_input(
            "% Descuento",
            0, 100,
            step=5,
            value=int(promo_existente["Descuento"].iloc[0]) if es_mod else 0
        )

        archivo = col4.file_uploader(
            "📎 Backup (PDF / Imagen)",
            type=["pdf", "png", "jpg"]
        )

        st.markdown("##### Ventanas")
        bw = st.date_input("Booking Window", (date.today(), date.today()))
        tw = st.date_input("Travel Window", (date.today(), date.today()))

        notas = st.text_area(
            "Notas / Restricciones",
            value=promo_existente["Notas"].iloc[0] if es_mod else ""
        )

        col_btn1, col_btn2 = st.columns(2)
        guardar = col_btn1.form_submit_button(
            "💾 Guardar" if not es_mod else "🔄 Actualizar",
            use_container_width=True
        )
        eliminar = (
            col_btn2.form_submit_button("🗑️ Eliminar", use_container_width=True)
            if es_mod else False
        )

        if guardar:
            if not rate_a_buscar or not hoteles:
                st.error("Falta Rate Plan o Propiedad")
            else:
                df_actual = df_actual[df_actual["Rate_Plan"] != rate_a_buscar]

                archivo_path = ""
                if archivo:
                    archivo_path = os.path.join(
                        MEDIA_DIR, f"{rate_a_buscar}_{archivo.name}"
                    )
                    with open(archivo_path, "wb") as f:
                        f.write(archivo.getbuffer())

                nuevos = []
                for h in hoteles:
                    nuevos.append({
                        "Hotel": h,
                        "Promo": promo,
                        "Rate_Plan": rate_a_buscar,
                        "Descuento": descuento,
                        "BW_Inicio": bw[0],
                        "BW_Fin": bw[1],
                        "TW_Inicio": tw[0],
                        "TW_Fin": tw[1],
                        "Notas": notas,
                        "Archivo_Path": archivo_path
                    })

                df_actual = pd.concat([df_actual, pd.DataFrame(nuevos)])
                df_actual.to_csv(CSV_FILE, index=False)

                st.success("✅ Promoción guardada correctamente")
                st.rerun()

        if eliminar:
            df_actual = df_actual[df_actual["Rate_Plan"] != rate_a_buscar]
            df_actual.to_csv(CSV_FILE, index=False)
            st.warning("🗑️ Promoción eliminada")
            st.rerun()

# ======================================================
# TAB BUSCADOR & REPORTES
# ======================================================
with tab_buscar:
    df = cargar_datos()

    if df.empty:
        st.info("La base de datos está vacía.")
    else:
        col_f, col_e = st.columns([4, 1])
        filtro = col_f.text_input("🔎 Buscar en promociones")

        if filtro:
            df = df[df.astype(str).apply(
                lambda x: x.str.contains(filtro, case=False)
            ).any(axis=1)]

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.drop(columns=["Archivo_Path"]).to_excel(
                writer, index=False, sheet_name="Promociones"
            )

        col_e.download_button(
            "📥 Excel",
            output.getvalue(),
            file_name=f"Promociones_{date.today()}.xlsx",
            use_container_width=True
        )

        st.markdown("### Resultados")
        for _, r in df.iterrows():
            with st.container(border=True):
                st.markdown(f"**{r['Hotel']} — {r['Promo']}**")
                st.markdown(
