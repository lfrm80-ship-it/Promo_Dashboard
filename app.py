import streamlit as st
import pandas as pd
import os
import sqlite3
from datetime import datetime, date
from io import BytesIO

# =====================================================
# CONFIGURACIÓN GENERAL
# =====================================================
st.set_page_config(page_title="HIC Master Record", layout="wide", page_icon="🏨")

st.markdown("""
<style>
.main { background-color: #f5f7f9; }
.stButton>button {
    width: 100%;
    border-radius: 5px;
    height: 3em;
    background-color: #00338d;
    color: white;
}
[data-testid="stSidebar"] {
    background-color: #ffffff;
    border-right: 1px solid #e0e0e0;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# BASE DE DATOS SQLITE
# =====================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "hic_master.db")
ADMIN_PASSWORD = st.secrets.get("admin_password", "admin")

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

@st.cache_resource
def get_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

conn = get_connection()

# =====================================================
# FUNCIONES DE DATOS
# =====================================================
def cargar_datos():
    conn.execute("""
        CREATE TABLE IF NOT EXISTS promociones (
            Hotel TEXT,
            Promo TEXT,
            Market TEXT,
            Rate_Plan TEXT,
            Descuento INTEGER,
            BW_Inicio DATE,
            BW_Fin DATE,
            TW_Inicio DATE,
            TW_Fin DATE,
            Notas TEXT
        )
    """)
    df = pd.read_sql("SELECT * FROM promociones", conn)
    for col in ["BW_Inicio", "BW_Fin", "TW_Inicio", "TW_Fin"]:
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
    return df

def guardar_datos(df):
    conn.execute("DELETE FROM promociones")
    df.to_sql("promociones", conn, if_exists="append", index=False)

def generar_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Master HIC")
    return output.getvalue()

df = cargar_datos()

# =====================================================
# SIDEBAR
# =====================================================
with st.sidebar:
    st.image("HIC.png", use_container_width=True)
    st.markdown("<h2 style='text-align:center; color:#00338d;'>Master Record</h2>", unsafe_allow_html=True)
    st.divider()

    menu = st.radio(
        "Navegación",
        ["🔍 Vista rápida y Filtros", "➕ Registro y Modificación", "📈 Upsell FD", "🏨 World of Hyatt"]
    )

    if st.session_state.is_admin:
        st.success("🔓 MODO ADMIN")
        if st.button("Cerrar Sesión"):
            st.session_state.is_admin = False
            st.rerun()
    else:
        pwd = st.text_input("Password", type="password")
        if st.button("Login") and pwd == ADMIN_PASSWORD:
            st.session_state.is_admin = True
            st.rerun()

# =====================================================
# MÓDULO 1 – VISTA RÁPIDA
# =====================================================
if menu == "🔍 Vista rápida y Filtros":
    st.title("🔎 Consulta Integral de Promociones")

    if df.empty:
        st.info("No hay promociones.")
    else:
        today = date.today()

        def estatus(row):
            if row["BW_Inicio"] <= today <= row["TW_Fin"]:
                return "Vigente"
            elif today < row["BW_Inicio"]:
                return "Iniciada"
            return "Expirada"

        df_v = df.copy()
        df_v["Estatus"] = df_v.apply(estatus, axis=1)

        c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
        h = c1.multiselect("Hotel", ["DREPM", "SECPM"])
        m = c2.multiselect("Mercado", df_v["Market"].unique())
        e = c3.multiselect("Estatus", ["Vigente", "Iniciada", "Expirada"], ["Vigente"])
        t = c4.text_input("Buscar")

        if h:
            df_v = df_v[df_v["Hotel"].isin(h)]
        if m:
            df_v = df_v[df_v["Market"].isin(m)]
        if e:
            df_v = df_v[df_v["Estatus"].isin(e)]
        if t:
            df_v = df_v[df_v.astype(str).apply(lambda r: r.str.contains(t, case=False).any(), axis=1)]

        st.dataframe(df_v, use_container_width=True)

        if st.session_state.is_admin and not df_v.empty:
            st.download_button(
                "📥 Exportar a Excel",
                generar_excel(df_v),
                file_name=f"HIC_Master_{date.today()}.xlsx"
            )

# =====================================================
# MÓDULO 2 – REGISTRO (UI PRO RESTAURADA)
# =====================================================
elif menu == "➕ Registro y Modificación":
    st.title("🛠️ Centro de Control")

    if not st.session_state.is_admin:
        st.error("Acceso restringido.")
    else:
        with st.form("alta"):
            p_nom = st.text_input("Promo")
            p_htl = st.multiselect("Hotel", ["DREPM", "SECPM"])
            p_mkt = st.selectbox("Mercado", ["USA", "CAN", "MEX", "LATAM", "EUR", "Worldwide"])
            p_cod = st.text_input("Rate Plan")
            p_des = st.number_input("Descuento %", 0, 100, 0)

            st.markdown("**Booking Window**")
            bw1, bw2 = st.columns(2)
            bw_i = bw1.date_input("BW Inicio")
            bw_f = bw2.date_input("BW Fin")

            st.markdown("**Travel Window**")
            tw1, tw2 = st.columns(2)
            tw_i = tw1.date_input("TW Inicio")
            tw_f = tw2.date_input("TW Fin")

            notas = st.text_area("Notas")

            if st.form_submit_button("✅ Guardar"):
                nuevos = pd.DataFrame([{
                    "Hotel": h,
                    "Promo": p_nom,
                    "Market": p_mkt,
                    "Rate_Plan": p_cod,
                    "Descuento": p_des,
                    "BW_Inicio": bw_i,
                    "BW_Fin": bw_f,
                    "TW_Inicio": tw_i,
                    "TW_Fin": tw_f,
                    "Notas": notas
                } for h in p_htl])

                df = pd.concat([df, nuevos], ignore_index=True)
                guardar_datos(df)
                st.success("Promoción guardada.")
                st.rerun()

# =====================================================
# MÓDULO 3 – UPSELL FD (SIN CAMBIOS)
# =====================================================
elif menu == "📈 Upsell FD":
    st.title("📈 Upsell Front Desk")
    CATS = {
        "JS Garden View": 0,
        "JS Pool View": 45,
        "JS Ocean View": 90,
        "JS Swim Out": 150
    }
    f = st.date_input("Llegada")
    n = st.number_input("Noches", 1, 30, 1)
    d = st.selectbox("De", list(CATS))
    a = st.selectbox("A", [k for k in CATS if CATS[k] > CATS[d]])
    if st.button("Calcular"):
        st.success(f"Upgrade total: ${(CATS[a]-CATS[d])*n:,.2f} USD")

# =====================================================
# MÓDULO 4 – WORLD OF HYATT (COMPLETO RESTAURADO)
# =====================================================
elif menu == "🏨 World of Hyatt":
    st.title("🏨 World of Hyatt – Operational Guide")

    woh = {
        "Member": {"bonus": 0, "late": "Subject to availability"},
        "Discoverist": {"bonus": 10, "late": "Up to 2 PM"},
        "Explorist": {"bonus": 20, "late": "Up to 2 PM"},
        "Globalist": {"bonus": 30, "late": "Guaranteed 4 PM"}
    }

    tier = st.radio("WOH Tier", list(woh.keys()), horizontal=True)

    rate = st.number_input("Eligible Rate (USD)", 300)
    nights = st.number_input("Nights", 1, 30, 1)

    base = rate * nights * 5
    total = base * (1 + woh[tier]["bonus"] / 100)

    c1, c2, c3 = st.columns(3)
    c1.metric("Base Points", int(base))
    c2.metric("Bonus", f"+{woh[tier]['bonus']}%")
    c3.metric("Total Points", int(total))
