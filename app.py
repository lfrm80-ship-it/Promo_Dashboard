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
# ARCHIVOS
# =============================
PROMOS_QA = "promociones_data.csv"
PROMOS_PROD = "promociones_produccion.csv"
AUDIT_FILE = "audit_log.csv"

# =============================
# ROLES / SEGURIDAD
# =============================
USER_ROLE = st.secrets.get("role", "viewer").lower()
USER_NAME = st.secrets.get("user", "unknown")
IS_ADMIN = USER_ROLE == "admin"

# =============================
# CONSTANTES
# =============================
PROPERTIES = [
    "DREPM - Dreams Playa Mujeres",
    "SECPM - Secrets Playa Mujeres",
]

MARKETS = ["USA", "CAN", "MEX", "LATAM", "EUR", "Worldwide"]

# =============================
# CSS GLOBAL
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
    right: 24px;
    background-color: #eef2ff;
    color: #3730a3;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 600;
    border: 1px solid #c7d2fe;
    z-index: 1000;
}
.tooltip {
    position: relative;
    display: inline-block;
    cursor: help;
}
.tooltip .tooltiptext {
    visibility: hidden;
    width: 260px;
    background-color: #1f2937;
    color: #fff;
    text-align: left;
    padding: 8px 10px;
    border-radius: 6px;
    font-size: 12px;
    position: absolute;
    z-index: 1000;
    bottom: 125%;
    left: 50%;
    transform: translateX(-50%);
    opacity: 0;
    transition: opacity 0.2s;
}
.tooltip:hover .tooltiptext {
    visibility: visible;
    opacity: 1;
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
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False)
    return out.getvalue()

# =============================
# SIDEBAR
# =============================
with st.sidebar:
    st.image("HIC.png", use_container_width=True)
    st.divider()

    env = st.selectbox("Entorno", ["Producción", "QA"])
    PROMOS_FILE = PROMOS_PROD if env == "Producción" else PROMOS_QA

    st.divider()

    menu_items = ["🔍 Vista rápida"]
    if IS_ADMIN:
        menu_items += ["📝 Editar promociones", "➕ Nueva promoción"]

    menu = st.radio("Navegación", menu_items)

    st.divider()
    st.caption(f"Usuario: {USER_NAME}")

    if not IS_ADMIN:
        st.markdown("""
        <div class="tooltip">
            🔒 Rol: <b>VIEWER</b> ⓘ
            <span class="tooltiptext">
                Modo solo lectura activo.<br><br>
                Para crear o editar promociones, solicita acceso <b>ADMIN</b>
                al equipo de Revenue.
            </span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.caption("🟢 Rol: ADMIN")

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
# BADGE READ ONLY (solo VIEWER)
# =============================
if not IS_ADMIN:
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
        # 🔥 FILTRO POR DEFECTO SOLO PARA VIEWER
        hoy = date.today()
        if not IS_ADMIN:
            df = df[
                (df["TW_Inicio"] <= hoy) &
                (df["TW_Fin"] >= hoy)
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
# EDITAR (ADMIN)
# =============================
elif menu == "📝 Editar promociones":

    if not IS_ADMIN:
        st.stop()

    edited = st.data_editor(df, use_container_width=True, hide_index=True)

    if st.button("💾 Guardar cambios", use_container_width=True):
        edited.to_csv(PROMOS_FILE, index=False)
        st.success("Cambios guardados correctamente ✅")
        st.rerun()

# =============================
# NUEVA PROMO (ADMIN)
# =============================
elif menu == "➕ Nueva promoción":

    if not IS_ADMIN:
        st.stop()

    with st.form("new_promo", clear_on_submit=True):

        col1, col2 = st.columns(2)
        with col1:
            promo = st.text_input("Promoción *")
            hotels = st.multiselect("Propiedad(es) *", PROPERTIES)
            market = st.selectbox("Market", MARKETS)
        with col2:
            rate = st.text_input("Rate Plan *")
            discount = st.number_input("Descuento %", 0, 100)

        bw_i = st.date_input("BW Inicio")
        bw_f = st.date_input("BW Fin")
        tw_i = st.date_input("TW Inicio")
        tw_f = st.date_input("TW Fin")

        notes = st.text_area("Notas")

        if st.form_submit_button("✅ Registrar promoción"):
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
