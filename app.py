import streamlit as st
import pandas as pd
import os
from datetime import datetime, date

# =====================================================
# 1. CONFIGURACIÓN Y ESTILOS
# =====================================================
st.set_page_config(page_title="HIC Master Record", layout="wide", page_icon="🏨")

ADMIN_PASSWORD = st.secrets.get("admin_password", "admin")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROMOS_FILE = os.path.join(BASE_DIR, "promociones_produccion.csv")
TC_VAL = 18.50 

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# =====================================================
# 2. FUNCIONES DE LÓGICA
# =====================================================
def cargar_datos():
    if not os.path.exists(PROMOS_FILE):
        return pd.DataFrame(columns=["Hotel", "Promo", "Market", "Rate_Plan", "Descuento", "BW_Inicio", "BW_Fin", "TW_Inicio", "TW_Fin", "Notas"])
    df = pd.read_csv(PROMOS_FILE)
    for col in ["BW_Inicio", "BW_Fin", "TW_Inicio", "TW_Fin"]:
        if col in df.columns: df[col] = pd.to_datetime(df[col]).dt.date
    return df

def detectar_temporada(fecha):
    estancias_ok = [(date(2026, 3, 26), date(2026, 4, 13)), (date(2026, 12, 20), date(2026, 12, 31))]
    for inicio, fin in estancias_ok:
        if inicio <= fecha <= fin: return "OK RM", 148
    return "REGULAR", 89

# =====================================================
# 3. SIDEBAR
# =====================================================
with st.sidebar:
    st.image("https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR6A7GfGq-o9f2A-V0uYmCqYFzP6oP2B4S-RA&s", width=200) 
    st.divider()
    menu = st.radio("Navegación", ["🔍 Vista rápida", "➕ Registro de Promoción", "📈 Upsell", "🏨 WOH"])
    
    if st.session_state.is_admin:
        st.success("🔓 MODO ADMIN")
        if st.button("Cerrar Sesión", use_container_width=True):
            st.session_state.is_admin = False
            st.rerun()
    else:
        with st.expander("🔐 Acceso Admin"):
            pwd = st.text_input("Pass", type="password")
            if st.button("Entrar", use_container_width=True) and pwd == ADMIN_PASSWORD:
                st.session_state.is_admin = True
                st.rerun()

df = cargar_datos()

# =====================================================
# MÓDULO: UPSELL (LIMPIO Y SIN PUNTOS WOH)
# =====================================================
if menu == "📈 Upsell":
    st.title("📈 Calculadora de Upsell")
    CAT_VALS = {"JS Garden View": 0, "JS Pool View": 45, "JS Ocean View": 90, "JS Swim Out": 150}
    
    with st.container(border=True):
        # Renglón 1: Logística
        r1_col1, r1_col2, r1_col3, r1_col4 = st.columns([1, 1.2, 1.2, 1])
        h_sel = r1_col1.selectbox("Hotel", ["DREPM", "SECPM"], index=0)
        f_sel = r1_col2.date_input("Fecha de llegada", date.today())
        t_orig = r1_col3.number_input("Tarifa Original (USD)", min_value=1.0, value=500.0)
        nits = r1_col4.number_input("Noches", 1, 30, 1)

        st.markdown("<hr style='margin:10px 0; border:0.5px solid #eee;'>", unsafe_allow_html=True)

        # Renglón 2: Categorías y Pax
        if h_sel == "DREPM":
            r2 = st.columns([2, 2, 0.8, 0.8, 1.2])
            h_orig = r2[0].selectbox("Categoría Original", list(CAT_VALS.keys()))
            h_dest = r2[1].selectbox("Upgrade a", [k for k in CAT_VALS.keys() if CAT_VALS[k] > CAT_VALS[h_orig]])
            ads = r2[2].number_input("Adultos", 1, 4, 2)
            nns = r2[3].number_input("Niños", 0, 4, 0)
            btn_calc = r2[4].button("🚀 Calcular", use_container_width=True)
        else:
            r2 = st.columns([2, 2, 0.8, 1.2])
            h_orig = r2[0].selectbox("Categoría Original", list(CAT_VALS.keys()))
            h_dest = r2[1].selectbox("Upgrade a", [k for k in CAT_VALS.keys() if CAT_VALS[k] > CAT_VALS[h_orig]])
            ads = r2[2].number_input("Adultos", 1, 4, 2)
            nns = 0
            btn_calc = r2[3].button("🚀 Calcular", use_container_width=True)

    if btn_calc:
        temp, p_kid = detectar_temporada(f_sel)
        dif_noche = (CAT_VALS.get(h_dest, 0) - CAT_VALS[h_orig]) * (1.25 if temp == "OK RM" else 1)
        total_up = dif_noche * nits
        gran_total = t_orig + total_up
        
        res1, res2 = st.columns([1, 1.5])
        with res1:
            st.markdown(f"""
                <div style="background-color:#f8f9fa; padding:15px; border-radius:10px; border-left: 5px solid #00338d; border: 1px solid #ddd;">
                    <p style="margin:0; font-size:0.9em; color:#666;">Total Upgrade</p>
                    <h2 style="margin:0; color:#00338d;">${total_up:,.2f} USD</h2>
                    <p style="margin:0; font-size:1.1em;">≈ {(total_up * TC_VAL):,.2f} MXN</p>
                    <hr style="margin:10px 0;">
                    <p style="margin:0; font-size:0.9em; color:#666;">Gran Total con Upgrade</p>
                    <h3 style="margin:0;">${gran_total:,.2f} USD</h3>
                </div>
            """, unsafe_allow_html=True)

        with res2:
            if h_sel == "DREPM":
                st.markdown("### 👶 Recordatorio de Edades") # Línea 172 corregida
                ed1, ed2, ed3 = st.columns(3)
                ed1.metric("Infantes (0-2)", "$0 USD")
                ed2.metric("Niños (3-12)", f"${p_kid} USD")
                ed3.metric("Juniors (13+)", "Adulto")
                if nns > 0 and "Swim Out" in h_dest:
                    st.error("🚫 Restricción: No se permiten menores en Swim Out.")
            else:
                st.info("✨ Secrets es Adults Only. Menores no permitidos en la propiedad.")

elif menu == "🏨 WOH":
    st.title("🏨 World of Hyatt")
    st.info("Para cálculos de puntos, utiliza la pestaña de WOH en el menú lateral.")
