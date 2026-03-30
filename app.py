import streamlit as st
import pandas as pd
import os
from datetime import datetime, date

# =====================================================
# 1. CONFIGURACIÓN Y ESTILOS
# =====================================================
st.set_page_config(page_title="HIC Master Record", layout="wide", page_icon="🏨")

# Variables de entorno y rutas
ADMIN_PASSWORD = st.secrets.get("admin_password", "admin")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROMOS_FILE = os.path.join(BASE_DIR, "promociones_produccion.csv")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
MEDIA_DIR = os.path.join(BASE_DIR, "media")
TC_VAL = 18.50 

for d in [BACKUP_DIR, MEDIA_DIR]:
    if not os.path.exists(d): os.makedirs(d)

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# =====================================================
# 2. FUNCIONES DE LÓGICA
# =====================================================
def guardar_datos(df):
    df.to_csv(PROMOS_FILE, index=False)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    df.to_csv(os.path.join(BACKUP_DIR, f"backup_{ts}.csv"), index=False)

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
    st.divider()
    
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
# MÓDULO: VISTA RÁPIDA
# =====================================================
if menu == "🔍 Vista rápida":
    st.title("🔎 Master Record")
    if df.empty:
        st.info("No hay promociones registradas.")
    else:
        f1, f2 = st.columns(2)
        h_f = f1.multiselect("Hotel", df["Hotel"].unique())
        t_f = f2.text_input("Buscar promo...")

        df_f = df.copy()
        if h_f: df_f = df_f[df_f["Hotel"].isin(h_f)]
        if t_f: df_f = df_f[df_f.astype(str).apply(lambda x: t_f.lower() in x.str.lower().any(), axis=1)]

        st.dataframe(df_f, use_container_width=True, hide_index=True)

# =====================================================
# MÓDULO: REGISTRO (CON UPLOADER)
# =====================================================
elif menu == "➕ Registro de Promoción":
    st.title("➕ Nueva Promoción")
    if not st.session_state.is_admin:
        st.warning("Acceso restringido.")
    else:
        with st.form("reg_form", clear_on_submit=True):
            c1, c2 = st.columns([2, 1])
            nombre = c1.text_input("Nombre Promo")
            hoteles = c2.multiselect("Hoteles", ["DREPM", "SECPM", "ZOE VR"])
            
            d1, d2, d3, d4 = st.columns(4)
            bw_i, bw_f = d1.date_input("BW Ini"), d2.date_input("BW Fin")
            tw_i, tw_f = d3.date_input("TW Ini"), d4.date_input("TW Fin")
            
            st.divider()
            archivo = st.file_uploader("Adjuntar Evidencia (PDF/JPG/Excel)", type=["pdf", "jpg", "png", "xlsx"])
            notas = st.text_area("Notas")
            
            if st.form_submit_button("🚀 Guardar"):
                if nombre and hoteles:
                    nuevas = pd.DataFrame([{"Hotel": h, "Promo": nombre, "BW_Inicio": bw_i, "BW_Fin": bw_f, "TW_Inicio": tw_i, "TW_Fin": tw_f, "Notas": notas} for h in hoteles])
                    df = pd.concat([df, nuevas], ignore_index=True)
                    guardar_datos(df)
                    st.success("Guardado")
                    st.rerun()

# =====================================================
# MÓDULO: UPSELL (CON EDADES Y PUNTOS)
# =====================================================
elif menu == "📈 Upsell":
    st.title("📈 Calculadora de Upsell")
    CAT_VALS = {"JS Garden View": 0, "JS Pool View": 45, "JS Ocean View": 90, "JS Swim Out": 150}
    
    col1, col2 = st.columns([1.2, 1])
    with col1:
        with st.container(border=True):
            h_sel = st.selectbox("Hotel", ["DREPM", "SECPM"])
            f_sel = st.date_input("Fecha")
            cl1, cl2, cl3 = st.columns([4, 1, 4])
            h_orig = cl1.selectbox("De:", list(CAT_VALS.keys()), label_visibility="collapsed")
            cl2.markdown("<h3 style='text-align:center;'>➡️</h3>", unsafe_allow_html=True)
            h_dest = cl3.selectbox("A:", [k for k in CAT_VALS.keys() if CAT_VALS[k] > CAT_VALS[h_orig]], label_visibility="collapsed")
            
            cu1, cu2, cu3 = st.columns(3)
            ads = cu1.number_input("Adultos", 1, 4, 2)
            nns = cu2.number_input("Niños (0-12)", 0, 4, 0) if h_sel == "DREPM" else 0
            nits = cu3.number_input("Noches", 1, 30, 1)
            btn_calc = st.button("🚀 Calcular", use_container_width=True)

    with col2:
        if btn_calc:
            temp, p_kid = detectar_temporada(f_sel)
            dif = (CAT_VALS[h_dest] - CAT_VALS[h_orig]) * (1.25 if temp == "OK RM" else 1)
            total = dif * nits
            
            st.markdown(f"""<div style="background-color:#f8f9fa; padding:20px; border-radius:10px; border-left: 5px solid #00338d; border: 1px solid #ddd;">
                <h4>Total Upgrade: ${total:,.2f} USD</h4>
                <p>≈ {(total * TC_VAL):,.2f} MXN</p>
                </div>""", unsafe_allow_html=True)
            
            if h_sel == "DREPM":
                st.info(f"👶 Niño (3-12): ${p_kid} USD")
            
            st.divider()
            st.subheader("💎 Puntos WOH por este pago")
            pb = total * 5
            st.write(f"**Member:** {int(pb):,} | **Explorist:** {int(pb*1.2):,} | **Globalist:** {int(pb*1.3):,}")

# =====================================================
# MÓDULO: WOH (CON BARRA DE CÁLCULO POR NOCHES)
# =====================================================
elif menu == "🏨 WOH":
    st.title("🏨 World of Hyatt")
    tab1, tab2 = st.tabs(["🏅 Status", "🧮 Calculadora de Estancia"])
    
    with tab1:
        st.table({"Nivel": ["Member", "Discoverist", "Explorist", "Globalist"], "Noches": ["0", "10", "30", "60"], "Bono": ["0%", "10%", "20%", "30%"]})
        st.write("🚩 **20 Noches:** 2 Club Access | **30 Noches:** 1 Cat 1-4 Free Night")
        st.write("🚩 **40 Noches:** 1 Guest of Honor | **60 Noches:** My Hyatt Concierge")

    with tab2:
        st.subheader("🧮 ¿Cuántos puntos generará el huésped?")
        # LA BARRA DE CÁLCULO RESTAURADA
        with st.container(border=True):
            cw1, cw2 = st.columns(2)
            monto_noche = cw1.number_input("Tarifa por noche (USD)", min_value=0, value=250)
            num_noches = cw2.number_input("Número de noches", min_value=1, value=1)
            
            total_estancia = monto_noche * num_noches
            puntos_base = total_estancia * 5
            
            st.divider()
            st.write(f"**Proyección de puntos por una estancia de ${total_estancia:,.2f} USD:**")
            
            c_p1, c_p2, c_p3, c_p4 = st.columns(4)
            c_p1.metric("Member", f"{int(puntos_base):,}")
            c_p2.metric("Discoverist", f"{int(puntos_base * 1.1):,}")
            c_p3.metric("Explorist", f"{int(puntos_base * 1.2):,}")
            c_p4.metric("Globalist", f"{int(puntos_base * 1.3):,}")
            st.caption("Nota: El cálculo se basa en el gasto elegible antes de impuestos.")
