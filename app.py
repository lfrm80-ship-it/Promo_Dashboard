import streamlit as st
import pandas as pd
import os
import io
from datetime import date

# =============================
# CONFIGURACIÓN GENERAL
# =============================
st.set_page_config(
    page_title="Master Record Playa Mujeres",
    layout="wide"
)

ADMIN_PASSWORD = st.secrets.get("admin_password", "admin")

# =============================
# SESSION STATE
# =============================
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

PROMOS_FILE = "promociones_produccion.csv"
MEDIA_DIR = "media"
os.makedirs(MEDIA_DIR, exist_ok=True)

# =============================
# CONSTANTES
# =============================
PROPERTIES = [
    "DREPM - Dreams Playa Mujeres",
    "SECPM - Secrets Playa Mujeres"
]

MARKETS = ["USA", "CAN", "MEX", "LATAM", "EUR", "Worldwide"]

# =============================
# ESTILOS
# =============================
st.markdown("""
<style>
.readonly {
    position: fixed;
    top: 90px;
    right: 22px;
    background: #f1f5f9;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 600;
    border: 1px solid #cbd5e1;
}
</style>
""", unsafe_allow_html=True)

# =============================
# HELPERS
# =============================
def cargar_promos():
    if os.path.exists(PROMOS_FILE):
        df = pd.read_csv(PROMOS_FILE)
        for col in ["BW_Inicio", "BW_Fin", "TW_Inicio", "TW_Fin"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
        return df
    return pd.DataFrame()

def generar_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

def estado_promo(row):
    hoy = date.today()
    tw_i = row.get("TW_Inicio")
    tw_f = row.get("TW_Fin")

    if pd.isna(tw_i) or pd.isna(tw_f):
        return "Expirada"
    if tw_i <= hoy <= tw_f:
        return "Activa"
    elif hoy < tw_i:
        return "Futura"
    else:
        return "Expirada"

# =============================
# SIDEBAR
# =============================
with st.sidebar:
    st.image("HIC.png", use_container_width=True)
    st.divider()

    menu_items = ["🔍 Vista rápida"]
    if st.session_state.is_admin:
        menu_items.append("➕ Nueva promoción")

    menu = st.radio("Navegación", menu_items)

    st.divider()
    st.caption("Acceso administrativo")

    if st.session_state.is_admin:
        st.success("🟢 Modo ADMIN")
        if st.button("Salir de Admin"):
            st.session_state.is_admin = False
            st.rerun()
    else:
        with st.expander("🔒 Entrar como Admin"):
            pwd = st.text_input("Contraseña", type="password")
            if st.button("Entrar"):
                if pwd == ADMIN_PASSWORD:
                    st.session_state.is_admin = True
                    st.rerun()
                else:
                    st.error("Contraseña incorrecta")

# =============================
# HEADER
# =============================
st.markdown(
    "<h3 style='text-align:center;'>📊 Master Record Playa Mujeres</h3>",
    unsafe_allow_html=True
)

if not st.session_state.is_admin:
    st.markdown("<div class='readonly'>READ ONLY</div>", unsafe_allow_html=True)

df = cargar_promos()

# =============================
# VISTA RÁPIDA
# =============================
if menu == "🔍 Vista rápida":

    if df.empty:
        st.info("No hay promociones registradas.")
    else:
        df["Estado"] = df.apply(estado_promo, axis=1)

        estados = ["Activa", "Futura", "Expirada"]
        default = ["Activa"] if not st.session_state.is_admin else estados

        filtro_estado = st.multiselect(
            "Estado",
            estados,
            default=default
        )

        df_view = df[df["Estado"].isin(filtro_estado)]

        col1, col2 = st.columns([4, 1])
        with col1:
            search = st.text_input("Buscar promoción…")
        with col2:
            st.download_button(
                "📥 Descargar Excel",
                data=generar_excel(df_view),
                file_name=f"MasterRecord_{date.today()}.xlsx",
                use_container_width=True
            )

        df_view = df_view[
            df_view.astype(str)
            .apply(lambda x: x.str.contains(search, case=False, na=False))
            .any(axis=1)
        ]

        st.dataframe(
            df_view,
            use_container_width=True,
            hide_index=True
        )

        # =============================
        # PREVIEW + ACCIONES ADMIN
        # =============================
        if not df_view.empty:
            st.divider()
            st.subheader("📎 Vista previa")

            idx = st.selectbox(
                "Selecciona una promoción",
                df_view.index,
                format_func=lambda i: df_view.loc[i, "Promo"]
            )

            archivo = df_view.loc[idx, "Archivo_Path"]

            if isinstance(archivo, str) and archivo and os.path.exists(archivo):
                if archivo.lower().endswith(".pdf"):
                    with open(archivo, "rb") as f:
                        st.download_button(
                            "📥 Descargar PDF",
                            f,
                            file_name=os.path.basename(archivo)
                        )
                else:
                    st.image(archivo, use_container_width=True)
            else:
                st.info("Esta promoción no tiene archivo adjunto.")

            # =============================
            # ACCIONES ADMIN
            # =============================
            if st.session_state.is_admin:
                st.divider()
                st.subheader("🛠 Acciones administrativas")

                action = st.radio(
                    "Acción",
                    ["Editar", "Extender vigencia", "Eliminar"],
                    horizontal=True
                )

                if action == "Eliminar":
                    st.warning("⚠️ Esta acción no se puede deshacer")
                    if st.checkbox("Confirmar eliminación"):
                        if st.button("Eliminar promoción"):
                            df = df.drop(idx)
                            df.to_csv(PROMOS_FILE, index=False)
                            st.success("Promoción eliminada")
                            st.rerun()

        # =============================
        # VISTA PREVIA DE ARCHIVOS
        # =============================
        st.divider()
        st.subheader("📎 Vista previa")

        if not df[mask].empty and "Archivo_Path" in df.columns:
            idx = st.selectbox(
                "Selecciona una promoción",
                df[mask].index,
                format_func=lambda i: df.loc[i, "Promo"]
            )

            archivo = df.loc[idx, "Archivo_Path"]

            if isinstance(archivo, str) and archivo and os.path.exists(archivo):
                if archivo.lower().endswith(".pdf"):
                    with open(archivo, "rb") as f:
                        st.download_button(
                            "📥 Descargar PDF",
                            f,
                            file_name=os.path.basename(archivo)
                        )
                else:
                    st.image(archivo, use_container_width=True)
            else:
                st.info("Esta promoción no tiene archivo adjunto.")
# =============================
# ACCIONES ADMIN (VISTA RÁPIDA)
# =============================
if st.session_state.is_admin and not df[mask].empty:

    st.divider()
    st.subheader("🛠 Acciones administrativas")

    action = st.radio(
        "Selecciona una acción",
        ["Editar", "Extender vigencia", "Eliminar"],
        horizontal=True
    )
# =============================
# NUEVA PROMO (ADMIN)
# =============================
elif menu == "➕ Nueva promoción":

    with st.form("new_promo", clear_on_submit=True):

        col1, col2 = st.columns(2)
        with col1:
            promo = st.text_input("Promoción *")
            hotels = st.multiselect("Hotel *", PROPERTIES)
            market = st.selectbox("Market", MARKETS)
        with col2:
            rate = st.text_input("Rate Plan *")
            discount = st.number_input("Descuento (%)", 0, 100)

        st.divider()

        c3, c4, c5, c6 = st.columns(4)
        with c3:
            bw_i = st.date_input("BW Inicio")
        with c4:
            bw_f = st.date_input("BW Fin")
        with c5:
            tw_i = st.date_input("TW Inicio")
        with c6:
            tw_f = st.date_input("TW Fin")

        uploaded_file = st.file_uploader(
            "Adjuntar flyer / PDF (opcional)",
            ["pdf", "png", "jpg", "jpeg"]
        )

        notas = st.text_area("Notas / Restricciones")

        submit = st.form_submit_button("✅ Registrar promoción")

        if submit:

            if not promo or not hotels or not rate:
                st.error("Completa los campos obligatorios.")
                st.stop()

            if bw_f < bw_i:
                st.error("BW Fin no puede ser menor que BW Inicio.")
                st.stop()

            if tw_f < tw_i:
                st.error("TW Fin no puede ser menor que TW Inicio.")
                st.stop()

            file_path = ""
            if uploaded_file:
                file_path = os.path.join(MEDIA_DIR, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

            rows = []
            for h in hotels:
                rows.append({
                    "Hotel": h,
                    "Promo": promo,
                    "Market": market,
                    "Rate_Plan": rate,
                    "Descuento": discount,
                    "BW_Inicio": bw_i,
                    "BW_Fin": bw_f,
                    "TW_Inicio": tw_i,
                    "TW_Fin": tw_f,
                    "Archivo_Path": file_path,
                    "Notas": notas
                })

            df_final = pd.concat([df, pd.DataFrame(rows)], ignore_index=True)
            df_final.to_csv(PROMOS_FILE, index=False)

            st.success("🎉 Promoción registrada correctamente")
            st.rerun()
