import streamlit as st
import pandas as pd
import os
import sqlite3
from datetime import datetime, date
from io import BytesIO

# =====================================================
# 1. CONFIGURACIÓN GENERAL DE LA PÁGINA
# =====================================================
st.set_page_config(
    page_title="HIC Master Record",
    layout="wide",
    page_icon="🏨"
)

st.markdown(
    """
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button {
        width: 100%;
        border-radius: 6px;
        height: 3em;
        background-color: #00338d;
        color: white;
        font-weight: 600;
    }
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e0e0e0;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# =====================================================
# 2. PARÁMETROS GENERALES
# =====================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "hic_master.db")
SOPORTES_DIR = os.path.join(BASE_DIR, "soportes_promos")

ADMIN_PASSWORD = st.secrets.get("admin_password", "admin")

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# =====================================================
# 3. CONEXIÓN SQLITE (PERSISTENTE)
# =====================================================
@st.cache_resource
def get_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

conn = get_connection()

# =====================================================
# 4. FUNCIONES DE BASE DE DATOS
# =====================================================
def inicializar_tabla():
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

def cargar_datos():
    inicializar_tabla()
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
# 5. SIDEBAR / LOGIN
# =====================================================
with st.sidebar:
    st.image("HIC.png", use_container_width=True)

    st.markdown(
        "<h2 style='text-align:center; color:#00338d;'>Master Record</h2>",
        unsafe_allow_html=True
    )

    st.divider()

    menu = st.radio(
        "Navegación",
        [
            "🔍 Vista rápida y Filtros",
            "➕ Registro y Modificación",
            "📈 Upsell FD",
            "🏨 World of Hyatt"
        ]
    )

    st.divider()

    if st.session_state.is_admin:
        st.success("🔓 MODO ADMINISTRADOR")
        if st.button("Cerrar Sesión"):
            st.session_state.is_admin = False
            st.rerun()
    else:
        pwd = st.text_input("Password", type="password")
        if st.button("Login") and pwd == ADMIN_PASSWORD:
            st.session_state.is_admin = True
            st.rerun()

# =====================================================
# 6. MÓDULO 1 – VISTA RÁPIDA Y FILTROS
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
            return "Expirada"

        df_view = df.copy()
        df_view["Estatus"] = df_view.apply(estatus, axis=1)

        f1, f2, f3, f4 = st.columns([1, 1, 1, 2])

        h_sel = f1.multiselect("Hotel", ["DREPM", "SECPM"])
        m_sel = f2.multiselect("Mercado", sorted(df_view["Market"].dropna().unique()))
        e_sel = f3.multiselect(
            "Estatus",
            ["Vigente", "Iniciada", "Expirada"],
            default=["Vigente"]
        )
        t_busq = f4.text_input("Buscador Global")

        df_f = df_view.copy()

        if h_sel:
            df_f = df_f[df_f["Hotel"].isin(h_sel)]
        if m_sel:
            df_f = df_f[df_f["Market"].isin(m_sel)]
        if e_sel:
            df_f = df_f[df_f["Estatus"].isin(e_sel)]
        if t_busq:
            df_f = df_f[df_f.astype(str).apply(
                lambda r: r.str.contains(t_busq, case=False, na=False).any(),
                axis=1
            )]

        st.dataframe(df_f, use_container_width=True, hide_index=True)

        if st.session_state.is_admin and not df_f.empty:
            st.download_button(
                "📥 Exportar Selección a Excel",
                generar_excel(df_f),
                file_name=f"HIC_Master_{date.today()}.xlsx"
            )

        # =========================
        # VISUALIZACIÓN DE TESTIGOS
        # =========================
        st.divider()
        st.subheader("📎 Testigos de Promociones")

        if os.path.exists(SOPORTES_DIR):
            archivos = os.listdir(SOPORTES_DIR)
            if not archivos:
                st.info("No hay testigos cargados.")
            else:
                for f in archivos:
                    ruta = os.path.join(SOPORTES_DIR, f)
                    ext = f.split(".")[-1].lower()
                    if ext in ["png", "jpg", "jpeg"]:
                        st.image(ruta, caption=f, use_container_width=True)
                    else:
                        with open(ruta, "rb") as file:
                            st.download_button(f"Descargar {f}", file, file_name=f)

# =====================================================
# 7. MÓDULO 2 – REGISTRO Y MODIFICACIÓN (PRO)
# =====================================================
elif menu == "➕ Registro y Modificación":
    st.title("🛠️ Centro de Control de Promociones")

    if not st.session_state.is_admin:
        st.error("Acceso restringido a administradores.")
    else:
        with st.form("registro_promo", clear_on_submit=True):

            # ---------- FILA 1 ----------
            st.subheader("Datos Generales de la Promoción")

            c1, c2, c3 = st.columns([3, 2, 2])
            p_nom = c1.text_input("Promo")
            p_htl = c2.multiselect("Hotel", ["DREPM", "SECPM"])
            p_mkt = c3.selectbox("Mercado", ["USA", "CAN", "MEX", "LATAM", "EUR", "Worldwide"])

            # ---------- FILA 2 ----------
            c4, c5, c6 = st.columns([2, 1.5, 1])
            p_cod = c4.text_input("Rate Plan")
            p_des = c5.number_input("Descuento %", 0, 100, 0)

            # ---------- BW ----------
            st.markdown("### Booking Window")
            bw1, bw2 = st.columns(2)
            bw_i = bw1.date_input("BW Inicio")
            bw_f = bw2.date_input("BW Fin")

            # ---------- TW ----------
            st.markdown("### Travel Window")
            tw1, tw2 = st.columns(2)
            tw_i = tw1.date_input("TW Inicio")
            tw_f = tw2.date_input("TW Fin")

            # ---------- SOPORTES ----------
            st.markdown("### 📎 Testigos / Soporte")
            archivo = st.file_uploader(
                "Subir imagen, PDF o Excel",
                type=["png", "jpg", "jpeg", "pdf", "xlsx"]
            )

            notas = st.text_area("Notas / Restricciones")

            if st.form_submit_button("✅ Guardar Promoción"):
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

                if archivo:
                    os.makedirs(SOPORTES_DIR, exist_ok=True)
                    nombre = f"{p_nom.replace(' ', '_')}_{archivo.name}"
                    with open(os.path.join(SOPORTES_DIR, nombre), "wb") as f:
                        f.write(archivo.getbuffer())

                st.success("✅ Promoción registrada correctamente.")
                st.rerun()

# =====================================================
# 8. MÓDULO 3 – UPSELL FD
# =====================================================
elif menu == "📈 Upsell FD":
    st.title("📈 Calculadora de Upsell Front Desk")

    CATS = {
        "JS Garden View": 0,
        "JS Pool View": 45,
        "JS Ocean View": 90,
        "JS Swim Out": 150
    }

    col1, col2, col3 = st.columns(3)
    f_arr = col1.date_input("Llegada")
    nts = col2.number_input("Noches", 1, 30, 1)
    c_de = col3.selectbox("De", list(CATS))

    c_a = st.selectbox("A", [k for k in CATS if CATS[k] > CATS[c_de]])

    if st.button("Calcular Upsell"):
        total = (CATS[c_a] - CATS[c_de]) * nts
        st.success(f"Upgrade total: ${total:,.2f} USD")

# =====================================================
# 9. MÓDULO 4 – WORLD OF HYATT (COMPLETO)
# =====================================================
elif menu == "🏨 World of Hyatt":
    st.title("🏨 World of Hyatt – Operational Guide")
    st.caption(
        "Apply benefits accurately and calculate points based on guest tier and eligible spend."
    )

    # -------------------------------------------------
    # Definición de estatus World of Hyatt (OPERATIVA)
    # -------------------------------------------------
    woh = {
        "Member": {
            "nights": 0,
            "bonus": 0,
            "late": "Subject to availability",
            "priority": "Standard recognition",
            "tooltip": "Members earn points on eligible spend and access member‑only rates."
        },
        "Discoverist": {
            "nights": 10,
            "bonus": 10,
            "late": "Up to 2:00 PM",
            "priority": "Enhanced recognition",
            "tooltip": "Discoverist members enjoy added recognition and a points bonus."
        },
        "Explorist": {
            "nights": 30,
            "bonus": 20,
            "late": "Up to 2:00 PM",
            "priority": "High priority service",
            "tooltip": "Explorist members receive elevated benefits suited for frequent stays."
        },
        "Globalist": {
            "nights": 60,
            "bonus": 30,
            "late": "Guaranteed 4:00 PM",
            "priority": "Premium priority",
            "tooltip": "Globalist members receive the highest level of recognition and benefits."
        }
    }

    # -------------------------------------------------
    # Selector de tier
    # -------------------------------------------------
    estatus = st.radio(
        "World of Hyatt Tier",
        list(woh.keys()),
        horizontal=True,
        help="Select the guest's World of Hyatt tier to apply benefits correctly."
    )

    b = woh[estatus]

    # -------------------------------------------------
    # Beneficios operativos (FRONT DESK VIEW)
    # -------------------------------------------------
    st.markdown("### 🛎️ Tier Benefits")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Tier Qualification",
        f"{b['nights']} nights",
        help="Eligible nights required in a calendar year."
    )

    c2.metric(
        "Points Bonus",
        f"{b['bonus']}%",
        help="Bonus applied to base points on eligible spend."
    )

    c3.metric(
        "Late Check‑Out",
        b["late"],
        help="Late check‑out benefit according to tier terms."
    )

    c4.metric(
        "Service Priority",
        b["priority"],
        help="Operational level of recognition for this tier."
    )

    st.info(b["tooltip"])

    # -------------------------------------------------
    # CALCULADORA DE PUNTOS (OPERATIVA)
    # -------------------------------------------------
    st.divider()
    st.markdown("### 🔢 Points Accrual Calculator")

    st.info(
        "Earn 5 points for every USD 1 spent on eligible rates. "
        "Tier bonuses apply automatically."
    )

    col1, col2 = st.columns(2)

    with col1:
        rate = st.number_input(
            "Eligible Nightly Rate (USD)",
            value=300,
            help="Base room rate eligible for points earning."
        )

    with col2:
        nights = st.number_input(
            "Number of Nights",
            value=3,
            min_value=1,
            help="Total eligible nights for the stay."
        )

    base_points = rate * nights * 5
    total_points = base_points * (1 + b["bonus"] / 100)

    r1, r2, r3 = st.columns(3)

    r1.metric(
        "Base Points",
        f"{int(base_points):,}",
        help="Standard earning: 5 points per USD."
    )

    r2.metric(
        "Tier Bonus",
        f"+{int(total_points - base_points):,}",
        help="Additional points from tier bonus."
    )

    r3.metric(
        f"Total Points ({estatus})",
        f"{int(total_points):,}",
        help="Total World of Hyatt points credited."
    )

    st.caption(
        "Operational note: Points are credited only on eligible spend "
        "in accordance with World of Hyatt terms and conditions."
    )

