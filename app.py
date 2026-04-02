import streamlit as st
import pandas as pd
import os
import sqlite3
from datetime import datetime, date
from io import BytesIO

# =====================================================
# 1. CONFIGURACIÓN Y ESTILOS (SOLUCIÓN MODO OSCURO)
# =====================================================
st.set_page_config(
    page_title="HIC Master Record",
    layout="wide",
    page_icon="🏨"
)

# CSS para corregir visibilidad en modo oscuro y mejorar botones
st.markdown(
    """
    <style>
    .main { background-color: transparent; }
    .stButton>button {
        width: 100%;
        border-radius: 6px;
        height: 3em;
        background-color: #00338d;
        color: white;
        font-weight: 600;
    }
    /* Forzar que el texto de la sidebar sea visible en cualquier tema */
    [data-testid="stSidebar"] {
        border-right: 1px solid #e0e0e0;
    }
    [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] label {
        color: inherit !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# =====================================================
# 2. PARÁMETROS GENERALES Y DB (PERSISTENCIA GARANTIZADA)
# =====================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "hic_master.db")
SOPORTES_DIR = os.path.join(BASE_DIR, "soportes_promos")

# Secretos de Streamlit Cloud
ADMIN_PASSWORD = st.secrets.get("admin_password", "admin")

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

@st.cache_resource
def get_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

conn = get_connection()

def inicializar_tabla():
    conn.execute("""
        CREATE TABLE IF NOT EXISTS promociones (
            Hotel TEXT, Promo TEXT, Market TEXT, Rate_Plan TEXT,
            Descuento INTEGER, BW_Inicio DATE, BW_Fin DATE,
            TW_Inicio DATE, TW_Fin DATE, Notas TEXT
        )
    """)
    conn.commit()

def cargar_datos():
    inicializar_tabla()
    df = pd.read_sql("SELECT * FROM promociones", conn)
    for col in ["BW_Inicio", "BW_Fin", "TW_Inicio", "TW_Fin"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
    return df

def guardar_datos(df_nuevo):
    # En SQLite, 'append' añade los nuevos sin borrar lo anterior
    df_nuevo.to_sql("promociones", conn, if_exists="append", index=False)

def generar_excel(df_export):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df_export.to_excel(writer, index=False, sheet_name="Master HIC")
    return output.getvalue()

# Carga global
df = cargar_datos()

# =====================================================
# 3. SIDEBAR / LOGIN
# =====================================================
with st.sidebar:
    try:
        st.image("HIC.png", use_container_width=True)
    except:
        st.write("### Inclusive Collection")

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
        pwd = st.text_input("Password", type="password")
        if st.button("Login") and pwd == ADMIN_PASSWORD:
            st.session_state.is_admin = True
            st.rerun()

# =====================================================
        # MEJORA: VISUALIZACIÓN DE TESTIGOS BAJO DEMANDA
        # =====================================================
        st.divider()
        with st.expander("👁️ Ver Testigos / Soportes de Promociones"):
            if os.path.exists(SOPORTES_DIR):
                archivos = os.listdir(SOPORTES_DIR)
                if not archivos:
                    st.info("No hay archivos de soporte cargados.")
                else:
                    # Organizamos en 3 columnas para que se vea más ordenado
                    cols_img = st.columns(3) 
                    for i, f in enumerate(archivos):
                        ruta = os.path.join(SOPORTES_DIR, f)
                        ext = f.lower().split(".")[-1]
                        
                        with cols_img[i % 3]: 
                            if ext in ["png", "jpg", "jpeg"]:
                                st.image(ruta, caption=f"Evidencia: {f}", use_container_width=True)
                            else:
                                with open(ruta, "rb") as file:
                                    st.download_button(
                                        label=f"📄 Descargar {f}", 
                                        data=file, 
                                        file_name=f, 
                                        key=f"btn_dl_{i}"
                                    )
            else:
                st.info("La carpeta de soportes aún no ha sido creada.")
# =====================================================
# 5. MÓDULO 2 – REGISTRO Y MODIFICACIÓN (ADMIN)
# =====================================================
elif menu == "➕ Registro y Modificación":
    st.title("🛠️ Centro de Control de Promociones")

    if not st.session_state.is_admin:
        st.error("Acceso restringido a administradores.")
    else:
        with st.form("registro_promo", clear_on_submit=True):
            st.subheader("Datos Generales")
            c1, c2, c3 = st.columns([3, 2, 2])
            p_nom = c1.text_input("Promo")
            p_htl = c2.multiselect("Hotel", ["DREPM", "SECPM"])
            p_mkt = c3.selectbox("Mercado", ["USA", "CAN", "MEX", "LATAM", "EUR", "Worldwide"])

            c4, c5 = st.columns(2)
            p_cod = c4.text_input("Rate Plan")
            p_des = c5.number_input("Descuento %", 0, 100, 0)

            st.markdown("### Fechas")
            bw1, bw2, tw1, tw2 = st.columns(4)
            bw_i = bw1.date_input("BW Inicio")
            bw_f = bw2.date_input("BW Fin")
            tw_i = tw1.date_input("TW Inicio")
            tw_f = tw2.date_input("TW Fin")

            archivo = st.file_uploader("Soporte", type=["png", "jpg", "pdf", "xlsx"])
            notas = st.text_area("Notas")

            if st.form_submit_button("✅ Guardar Promoción"):
                nuevos = pd.DataFrame([{
                    "Hotel": h, "Promo": p_nom, "Market": p_mkt, "Rate_Plan": p_cod,
                    "Descuento": p_des, "BW_Inicio": bw_i, "BW_Fin": bw_f,
                    "TW_Inicio": tw_i, "TW_Fin": tw_f, "Notas": notas
                } for h in p_htl])
                
                guardar_datos(nuevos)
                if archivo:
                    os.makedirs(SOPORTES_DIR, exist_ok=True)
                    with open(os.path.join(SOPORTES_DIR, archivo.name), "wb") as f:
                        f.write(archivo.getbuffer())
                st.success("Guardado correctamente.")
                st.rerun()

# =====================================================
# 6. MÓDULO 3 – UPSELL FD (LÓGICA COMPLETA)
# =====================================================
elif menu == "📈 Upsell FD":
    st.title("📈 Calculadora de Upsell Front Desk")
    CATS = {"JS Garden View": 0, "JS Pool View": 45, "JS Ocean View": 90, "JS Swim Out": 150}
    
    col1, col2, col3 = st.columns(3)
    f_arr = col1.date_input("Llegada")
    nts = col2.number_input("Noches", 1, 30, 1)
    c_de = col3.selectbox("De", list(CATS))
    c_a = st.selectbox("A", [k for k in CATS if CATS[k] > CATS[c_de]])

    if st.button("Calcular Upsell"):
        total = (CATS[c_a] - CATS[c_de]) * nts
        st.success(f"Upgrade total: ${total:,.2f} USD")

# =====================================================
# 7. MÓDULO 4 – WORLD OF HYATT (LÓGICA COMPLETA)
# =====================================================
elif menu == "🏨 World of Hyatt":
    st.title("🏨 World of Hyatt – Operational Guide")
    woh = {
        "Member": {"nights": 0, "bonus": 0, "late": "Subject to availability", "priority": "Standard"},
        "Discoverist": {"nights": 10, "bonus": 10, "late": "2:00 PM", "priority": "Enhanced"},
        "Explorist": {"nights": 30, "bonus": 20, "late": "2:00 PM", "priority": "High"},
        "Globalist": {"nights": 60, "bonus": 30, "late": "4:00 PM", "priority": "Premium"}
    }
    estatus_woh = st.radio("Tier", list(woh.keys()), horizontal=True)
    b = woh[estatus_woh]
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Nights", f"{b['nights']}")
    c2.metric("Bonus", f"{b['bonus']}%")
    c3.metric("Late C/O", b['late'])
    c4.metric("Priority", b['priority'])

    st.divider()
    st.markdown("### 🔢 Points Calculator")
    rate = st.number_input("Rate (USD)", value=300)
    nights_woh = st.number_input("Noches ", value=3)
    base_p = rate * nights_woh * 5
    total_p = base_p * (1 + b["bonus"] / 100)
    
    r1, r2, r3 = st.columns(3)
    r1.metric("Base Points", f"{int(base_p):,}")
    r2.metric("Bonus Points", f"+{int(total_p - base_p):,}")
    r3.metric("Total", f"{int(total_p):,}")
