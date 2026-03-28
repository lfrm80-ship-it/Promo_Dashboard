import streamlit as st
import pandas as pd
import os
import io
from datetime import date

# =============================
# CONFIG
# =============================
st.set_page_config(page_title="Master Record Playa Mujeres", layout="wide")

ADMIN_PASSWORD = st.secrets.get("admin_password", "admin")

# =============================
# SESSION STATE
# =============================
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# =============================
# FILES
# =============================
PROMOS_QA = "promociones_data.csv"
PROMOS_PROD = "promociones_produccion.csv"

# =============================
# CONSTANTS
# =============================
PROPERTIES = [
    "DREPM - Dreams Playa Mujeres",
    "SECPM - Secrets Playa Mujeres",
]

MARKETS = ["USA", "CAN", "MEX", "LATAM", "EUR", "Worldwide"]

# =============================
# CSS
# =============================
st.markdown("""
<style>
.env-badge {
    position: fixed;
    top: 50px;
    right: 24px;
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
if env == "QA":
    st.markdown(
        '<div class="env-badge env-qa">QA</div>',
        unsafe_allow_html=True
    )
else:
    st.markdown(
        '<div class="env-badge env-prod">PRODUCCIÓN</div>',
        unsafe_allow_html=True
    )

# =============================
# HEADER
# =============================
st.markdown("""
<h3 style="text-align:center;">📊 Master Record Playa Mujeres</h3>
""", unsafe_allow_html=True)

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
# VISTA
# =============================
if menu == "🔍 Vista rápida":

    if df.empty:
        st.info("No hay promociones registradas.")
    else:
        if not st.session_state.is_admin:
            today = date.today()
            df = df[(df["TW_Inicio"] <= today) & (df["TW_Fin"] >= today)]

        c1, c2 = st.columns([4,1])
        with c1:
            search = st.text_input("", placeholder="Buscar promoción...")
        with c2:
            st.download_button("📥 Excel", generar_excel(df), file_name="MasterRecord.xlsx")

        mask = df.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)
        st.dataframe(df[mask], use_container_width=True, hide_index=True)

# =============================
# EDITAR
# =============================
elif menu == "📝 Editar promociones":
    edited = st.data_editor(df, use_container_width=True, hide_index=True)
    if st.button("Guardar cambios"):
        edited.to_csv(PROMOS_FILE, index=False)
        st.success("Cambios guardados")
        st.rerun()

# =============================
# NUEVA
# =============================
elif menu == "➕ Nueva promoción":
    with st.form("new"):
        promo = st.text_input("Promoción")
        hotels = st.multiselect("Hotel", PROPERTIES)
        rate = st.text_input("Rate Plan")
        discount = st.number_input("Descuento %", 0, 100)

        submit = st.form_submit_button("Registrar")

        if submit and promo and hotels:
            rows = [{
                "Hotel": h,
                "Promo": promo,
                "Rate_Plan": rate,
                "Descuento": discount
            } for h in hotels]

            df_final = pd.concat([df, pd.DataFrame(rows)], ignore_index=True)
            df_final.to_csv(PROMOS_FILE, index=False)
            st.success("Promoción creada")
            st.rerun()
