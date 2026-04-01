import streamlit as st
import pandas as pd
import os
import sqlite3
from datetime import datetime, date
from io import BytesIO

# =====================================================
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS
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
# 2. PARÁMETROS Y BASE DE DATOS SQLITE
# =====================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "hic_master.db")

ADMIN_PASSWORD = st.secrets.get("admin_password", "admin")
TC_VAL = 18.50

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# =====================================================
# 3. CONEXIÓN SQLITE (PERSISTENTE)
# =====================================================
@st.cache_resource
def get_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    return conn

conn = get_connection()

# =====================================================
# 4. FUNCIONES DE DATOS (SQLITE)
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
        if col in df.columns:
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

# =====================================================
# ✅ CARGA GLOBAL DE DATOS
# =====================================================
df = cargar_datos()

# =====================================================
# 5. SIDEBAR Y LOGIN
# =====================================================
with st.sidebar:
    st.image("HIC.png", use_container_width=True)
    st.markdown("<h2 style='text-align:center; color:#00338d;'>Master Record</h2>", unsafe_allow_html=True)
    st.divider()

    menu = st.radio(
        "Navegación",
        ["🔍 Vista rápida y Filtros", "➕ Registro y Modificación", "📈 Upsell FD", "🏨 World of Hyatt"]
    )

    st.divider()

    if st.session_state.is_admin:
        st.success("🔓 MODO ADMINISTRADOR")
        if st.button("Cerrar Sesión"):
            st.session_state.is_admin = False
            st.rerun()
    else:
        with st.expander("🔐 Acceso Distribución"):
            pwd = st.text_input("Password", type="password")
            if st.button("Login") and pwd == ADMIN_PASSWORD:
                st.session_state.is_admin = True
                st.rerun()

# =====================================================
# 6. MÓDULO 1 – VISTA RÁPIDA
# =====================================================
if menu == "🔍 Vista rápida y Filtros":
    st.title("🔎 Consulta Integral de Promociones")

    if df.empty:
        st.info("No hay promociones registradas.")
    else:
        today = date.today()

        def estatus(row):
            if pd.isna(row["BW_Inicio"]) or pd.isna(row["TW_Fin"]):
                return "Sin Fecha"
            if row["BW_Inicio"] <= today <= row["TW_Fin"]:
                return "Vigente"
            elif today < row["BW_Inicio"]:
                return "Iniciada"
            else:
                return "Expirada"

        df_view = df.copy()
        df_view["Estatus"] = df_view.apply(estatus, axis=1)

        c1, c2, c3, c4 = st.columns([1, 1, 1, 2])

        h = c1.multiselect("Hoteles", ["DREPM", "SECPM"])
        m = c2.multiselect("Mercado", sorted(df_view["Market"].dropna().unique()))
        e = c3.multiselect("Estatus", ["Vigente", "Iniciada", "Expirada"], ["Vigente"])
        t = c4.text_input("Buscador Global")

        df_f = df_view.copy()

        if h:
            df_f = df_f[df_f["Hotel"].isin(h)]
        if m:
            df_f = df_f[df_f["Market"].isin(m)]
        if e:
            df_f = df_f[df_f["Estatus"].isin(e)]
        if t:
            df_f = df_f[df_f.astype(str).apply(
                lambda r: r.str.contains(t, case=False, na=False).any(), axis=1
            )]

        st.dataframe(df_f, use_container_width=True, hide_index=True)

        if st.session_state.is_admin and not df_f.empty:
            st.download_button(
                "📥 Exportar a Excel",
                generar_excel(df_f),
                file_name=f"HIC_Master_{date.today()}.xlsx",
            )

# =====================================================
# 7. MÓDULO 2 – REGISTRO / MODIFICACIÓN
# =====================================================
elif menu == "➕ Registro y Modificación":
    st.title("🛠️ Centro de Control")

    if not st.session_state.is_admin:
        st.error("Acceso solo para administradores.")
    else:
        tab1, tab2 = st.tabs(["🚀 Nueva Campaña", "📝 Modificar Fechas"])

        with tab1:
            with st.form("alta"):
                p_nom = st.text_input("Nombre de Promo")
                p_htl = st.multiselect("Hoteles", ["DREPM", "SECPM"])
                p_mkt = st.selectbox("Mercado", ["USA", "CAN", "MEX", "LATAM", "EUR", "Worldwide"])
                p_cod = st.text_input("Rate Plan")
                p_des = st.number_input("Descuento %", 0, 100, 0)

                bw_i = st.date_input("BW Inicio")
                bw_f = st.date_input("BW Fin")
                tw_i = st.date_input("TW Inicio")
                tw_f = st.date_input("TW Fin")

                notas = st.text_area("Notas")

                if st.form_submit_button("✅ Guardar"):
                    if p_nom and p_htl:
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
                        st.success("Promoción guardada correctamente.")
                        st.rerun()

        with tab2:
            if df.empty:
                st.info("No hay promociones.")
            else:
                promo = st.selectbox("Promo", sorted(df["Promo"].unique()))
                idx = df[df["Promo"] == promo].index[0]

                df.at[idx, "BW_Inicio"] = st.date_input("BW Inicio", df.at[idx, "BW_Inicio"])
                df.at[idx, "BW_Fin"] = st.date_input("BW Fin", df.at[idx, "BW_Fin"])
                df.at[idx, "TW_Inicio"] = st.date_input("TW Inicio", df.at[idx, "TW_Inicio"])
                df.at[idx, "TW_Fin"] = st.date_input("TW Fin", df.at[idx, "TW_Fin"])
                df.at[idx, "Notas"] = st.text_area("Notas", df.at[idx, "Notas"])

                if st.button("💾 Guardar Cambios"):
                    guardar_datos(df)
                    st.success("Cambios guardados.")
                    st.rerun()

# =====================================================
# 8. MÓDULO 3 – UPSELL FD
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
        total = (CATS[a] - CATS[d]) * n
        st.success(f"Upgrade total: ${total:,.2f} USD")

# =====================================================
# 9. MÓDULO 4 – WORLD OF HYATT
# =====================================================
elif menu == "🏨 World of Hyatt":
    st.title("🏨 World of Hyatt – Guide")
    st.info("Módulo informativo operativo.")
