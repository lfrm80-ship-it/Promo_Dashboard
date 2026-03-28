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

# =============================
# PASSWORD ADMIN (SECRETS)
# =============================
ADMIN_PASSWORD = st.secrets.get("admin_password", "admin")

# =============================
# SESSION STATE
# =============================
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# =============================
# ARCHIVOS
# =============================
PROMOS_QA = "promociones_data.csv"
PROMOS_PROD = "promociones_produccion.csv"

# =============================
# CONSTANTES
# =============================
PROPERTIES = [
    "DREPM - Dreams Playa Mujeres",
    "SECPM - Secrets Playa Mujeres"
]

MARKETS = ["USA", "CAN", "MEX", "LATAM", "EUR", "Worldwide"]

# =============================
# CSS
# =============================
st.markdown("""
<style>
.header-container {
    text-align: center;
    border-bottom: 1px solid #e6e9ef;
    padding-bottom: 6px;
    margin-bottom: 10px;
}
.main-title {
    font-size: 22px;
    font-weight: 700;
}
.sub-title {
    font-size: 13px;
    color: #6b6b6b;
}
.readonly-badge {
    position: fixed;
    top: 90px;
    right: 22px;
    background-color: #f1f5f9;
    color: #334155;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 600;
    border: 1px solid #cbd5e1;
    z-index: 1000;
}
.env-badge {
    position: fixed;
    top: 58px;
    right: 22px;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 700;
    z-index: 1000;
}
.env-qa {
    background-color: #e0f2fe;
    color: #075985;
    border: 1px solid #7dd3fc;
}
.env-prod {
    background-color: #fee2e2;
    color: #7f1d1d;
    border: 1px solid #fca5a5;
}
</style>
""", unsafe_allow_html=True)

# =============================
# HELPERS
# =============================
def cargar_promos(path):
    if os.path.exists(path):
        df = pd.read_csv(path)
        for c in ["BW_Inicio", "BW_Fin", "TW_Inicio", "TW_Fin"]:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c]).dt.date
        return df
    return pd.DataFrame()

def generar_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# =============================
# SIDEBAR
# =============================
with st.sidebar:
    st.image("HIC.png", use_container_width=True)
    st.divider()

    # =============================
    # CONTEXTO (NO MENÚ)
    # =============================
    env = st.radio(
        "Entorno de trabajo",
        ["QA", "Producción"],
        horizontal=True,
        help="QA = pruebas | Producción = datos oficiales"
    )

    PROMOS_FILE = PROMOS_PROD if env == "Producción" else PROMOS_QA

    st.divider()

    # =============================
    # NAVEGACIÓN
    # =============================
    menu_items = ["🔍 Vista rápida"]
    if st.session_state.is_admin:
        menu_items += ["📝 Editar promociones", "➕ Nueva promoción"]

    menu = st.radio("Navegación", menu_items)

    st.divider()

    # =============================
    # ADMIN (AL FINAL)
    # =============================
    st.caption("Acceso administrativo")

    if st.session_state.is_admin:
        st.success("🟢 Modo ADMIN activo")
        if st.button("Salir de modo Admin"):
            st.session_state.is_admin = False
            st.rerun()
    else:
        with st.expander("🔒 Cambiar a Admin"):
            pwd = st.text_input("Contraseña Admin", type="password")
            if st.button("Entrar"):
                if pwd == ADMIN_PASSWORD:
                    st.session_state.is_admin = True
                    st.rerun()
                else:
                    st.error("Contraseña incorrecta")

# =============================
# HEADER
# =============================
st.markdown("""
<div class="header-container">
    <div class="main-title">📊 Master Record Playa Mujeres</div>
    <div class="sub-title">Herramienta oficial de control de promociones</div>
</div>
""", unsafe_allow_html=True)

# =============================
# ENVIRONMENT BADGE
# =============================
if env == "QA":
    st.markdown('<div class="env-badge env-qa">QA</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="env-badge env-prod">PRODUCCIÓN</div>', unsafe_allow_html=True)

# =============================
# READ ONLY BADGE
# =============================
if not st.session_state.is_admin:
    st.markdown('<div class="readonly-badge">READ ONLY</div>', unsafe_allow_html=True)

# =============================
# DATA
# =============================
df = cargar_promos(PROMOS_FILE)

# =============================
# VISTA RÁPIDA
# =============================
if menu == "🔍 Vista rápida":

    if df.empty:
        st.info("No hay promociones registradas.")
    else:
        # VIEWER VE SOLO ACTIVAS
        if not st.session_state.is_admin:
            today = date.today()
            df = df[
                (df["TW_Inicio"] <= today) &
                (df["TW_Fin"] >= today)
            ]

        c1, c2 = st.columns([4, 1])
        with c1:
            search = st.text_input("", placeholder="Buscar por promo, hotel, market o rate plan…")
        with c2:
            st.download_button(
                "📥 Exportar Excel",
                generar_excel(df),
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

    edited = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True
    )

    if st.button("💾 Guardar cambios", use_container_width=True):
        edited.to_csv(PROMOS_FILE, index=False)
        st.success("Cambios guardados correctamente ✅")
        st.rerun()

# =============================
# NUEVA PROMO (ADMIN)
# =============================
elif menu == "➕ Nueva promoción":

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

                st.success("🎉 Promoción registrada correctamente")
                st.rerun()
