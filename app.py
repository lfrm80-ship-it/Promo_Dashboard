import streamlit as st
import pandas as pd
import os
import io
from datetime import date, datetime

# =============================
# CONFIGURACIÓN GENERAL
# =============================
st.set_page_config(
    page_title="Master Record Playa Mujeres",
    layout="wide"
)

# =============================
# ARCHIVOS Y PATHS
# =============================
PROMOS_QA = "promociones_data.csv"
PROMOS_PROD = "promociones_produccion.csv"
AUDIT_FILE = "audit_log.csv"
MEDIA_DIR = "media"

os.makedirs(MEDIA_DIR, exist_ok=True)

# =============================
# SEGURIDAD / ROLES
# =============================
USER_ROLE = st.secrets.get("role", "viewer")   # admin | viewer
USER_NAME = st.secrets.get("user", "unknown")

IS_ADMIN = USER_ROLE.lower() == "admin"

# =============================
# CONSTANTES
# =============================
PROPERTIES = [
    "DREPM - Dreams Playa Mujeres",
    "SECPM - Secrets Playa Mujeres",
]

MARKETS = ["USA", "CAN", "MEX", "LATAM", "EUR", "Worldwide"]

# =============================
# ESTILOS
# =============================
st.markdown("""
<style>
.header-container {
    text-align: center;
    border-bottom: 1px solid #e6e9ef;
    margin-bottom: 15px;
}
.main-title {
    font-size: 22px;
    font-weight: 700;
}
.sub-title {
    font-size: 13px;
    color: #6b6b6b;
}
</style>
""", unsafe_allow_html=True)

# =============================
# HELPERS
# =============================
def cargar_promos(file):
    if os.path.exists(file):
        df = pd.read_csv(file)
        for c in ["BW_Inicio", "BW_Fin", "TW_Inicio", "TW_Fin"]:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c]).dt.date
        return df
    return pd.DataFrame()

def generar_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Promos")
    return output.getvalue()

def log_action(action, promo):
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user": USER_NAME,
        "role": USER_ROLE,
        "action": action,
        "promo": promo
    }
    df_log = pd.DataFrame([entry])
    if os.path.exists(AUDIT_FILE):
        df_log.to_csv(AUDIT_FILE, mode="a", index=False, header=False)
    else:
        df_log.to_csv(AUDIT_FILE, index=False)

# =============================
# SIDEBAR
# =============================
with st.sidebar:
    st.image("HIC.png", use_container_width=True)
    st.divider()

    env = st.selectbox("Entorno", ["Producción", "QA"])
    PROMOS_FILE = PROMOS_PROD if env == "Producción" else PROMOS_QA

    st.divider()

    menu_options = ["🔍 Vista rápida"]
    if IS_ADMIN:
        menu_options.extend(["📝 Editar promociones", "➕ Nueva promoción"])

    menu = st.radio("Navegación", menu_options)

    st.divider()
    st.caption(f"Usuario: {USER_NAME}")
    st.caption(f"Rol: {USER_ROLE.upper()}")

# =============================
# HEADER
# =============================
st.markdown("""
<div class="header-container">
    <div class="main-title">📊 Master Record Playa Mujeres</div>
    <div class="sub-title">Herramienta oficial de control de promociones</div>
</div>
""", unsafe_allow_html=True)

# ✅ MENSAJE UX PARA VIEWER (MEJORA CLAVE)
if not IS_ADMIN:
    st.info(
        "🔒 **Modo solo lectura activo** · "
        "Para crear o editar promociones, solicita acceso **ADMIN** al equipo de Revenue."
    )

df = cargar_promos(PROMOS_FILE)

# =============================
# VISTA RÁPIDA
# =============================
if menu == "🔍 Vista rápida":

    if df.empty:
        st.info("No hay promociones registradas.")
    else:
        c1, c2 = st.columns([4, 1])
        with c1:
            search = st.text_input("", placeholder="Buscar por promo, hotel, market o rate plan…")
        with c2:
            st.download_button(
                "📥 Exportar Excel",
                data=generar_excel(df),
                file_name=f"MasterRecord_{date.today()}.xlsx",
                use_container_width=True
            )

        mask = df.astype(str).apply(
            lambda x: x.str.contains(search, case=False, na=False)
        ).any(axis=1)

        st.dataframe(
            df[mask],
            use_container_width=True,
            hide_index=True
        )

# =============================
# EDITAR PROMOS (ADMIN)
# =============================
elif menu == "📝 Editar promociones":

    if not IS_ADMIN:
        st.error("⛔ Acceso restringido.")
        st.stop()

    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True
    )

    if st.button("💾 Guardar cambios", use_container_width=True):
        edited_df.to_csv(PROMOS_FILE, index=False)
        log_action("EDIT", "Multiple records")
        st.success("Cambios guardados correctamente ✅")
        st.rerun()

# =============================
# NUEVA PROMO (ADMIN)
# =============================
elif menu == "➕ Nueva promoción":

    if not IS_ADMIN:
        st.error("⛔ Acceso restringido.")
        st.stop()

    with st.form("form_nueva_promo", clear_on_submit=True):

        col1, col2 = st.columns(2)

        with col1:
            promo = st.text_input("Nombre de la promoción *")
            hotels = st.multiselect("Propiedad(es) *", PROPERTIES)
            market = st.selectbox("Market", MARKETS)

        with col2:
            rate = st.text_input("Rate Plan *")
            discount = st.number_input("Descuento (%)", 0, 100, step=1)

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

        notes = st.text_area("Notas / Restricciones")

        submit = st.form_submit_button("✅ Registrar promoción", use_container_width=True)

        if submit:
            if not promo or not hotels or not rate:
                st.error("Completa los campos obligatorios (*)")
            else:
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
                        "Notas": notes
                    })

                df_final = pd.concat([df, pd.DataFrame(rows)], ignore_index=True)
                df_final.to_csv(PROMOS_FILE, index=False)

                log_action("CREATE", promo)
                st.success("🎉 Promoción registrada correctamente")
                st.rerun()
