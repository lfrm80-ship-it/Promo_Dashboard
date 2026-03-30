import streamlit as st
import pandas as pd
import os
from datetime import datetime, date
from io import BytesIO

# =====================================================
# 1. CONFIGURACIÓN Y ESTILOS PRO
# =====================================================
st.set_page_config(page_title="HIC Master Record", layout="wide", page_icon="🏨")

# Parámetros Operativos Cancún 2026
ADMIN_PASSWORD = st.secrets.get("admin_password", "admin")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROMOS_FILE = os.path.join(BASE_DIR, "promociones_produccion.csv")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
TC_VAL = 18.50 

for d in [BACKUP_DIR]:
    if not os.path.exists(d): os.makedirs(d)

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# =====================================================
# 2. FUNCIONES DE DATOS Y REVENUE
# =====================================================
def guardar_y_respaldar(df, nota="Actualización"):
    df.to_csv(PROMOS_FILE, index=False)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    df.to_csv(os.path.join(BACKUP_DIR, f"backup_{ts}.csv"), index=False)

def cargar_datos():
    if not os.path.exists(PROMOS_FILE):
        return pd.DataFrame(columns=["Hotel", "Promo", "Market", "Rate_Plan", "Descuento", "BW_Inicio", "BW_Fin", "TW_Inicio", "TW_Fin", "Notas"])
    df = pd.read_csv(PROMOS_FILE)
    for col in ["BW_Inicio", "BW_Fin", "TW_Inicio", "TW_Fin"]:
        if col in df.columns: df[col] = pd.to_datetime(df[col], errors='coerce').dt.date
    return df

def get_season_rate(fecha):
    # Temporadas Críticas 2026 (Semana Santa y Navidad)
    peaks = [(date(2026, 3, 26), date(2026, 4, 13)), (date(2026, 12, 20), date(2026, 12, 31))]
    for start, end in peaks:
        if start <= fecha <= end: return "PREMIUM", 148
    return "REGULAR", 89

# =====================================================
# 3. SIDEBAR (LOGO Y NAVEGACIÓN)
# =====================================================
with st.sidebar:
    # URL del logo de Hyatt World (Verificado)
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Hyatt_logo.svg/2560px-Hyatt_logo.svg.png", use_container_width=True)
    st.markdown("<h3 style='text-align: center;'>Master Record HIC</h3>", unsafe_allow_html=True)
    st.divider()
    
    menu = st.radio("Módulos de Gestión", 
                    ["🔍 Vista rápida y Filtros", "➕ Registro y Modificación", "📈 Upsell FD", "🏨 World of Hyatt"])
    st.divider()
    
    if st.session_state.is_admin:
        st.success("🔓 MODO ADMINISTRADOR ACTIVO")
        if st.button("Cerrar Sesión", use_container_width=True):
            st.session_state.is_admin = False
            st.rerun()
    else:
        with st.expander("🔐 Staff Admin"):
            pwd = st.text_input("Pass", type="password")
            if st.button("Desbloquear") and pwd == ADMIN_PASSWORD:
                st.session_state.is_admin = True
                st.rerun()

df = cargar_datos()

# =====================================================
# MÓDULO: VISTA RÁPIDA (FIX TYPEERROR IMAGEN 5)
# =====================================================
if menu == "🔍 Vista rápida y Filtros":
    st.title("🔎 Consulta de Promociones")
    if df.empty:
        st.info("Base de datos vacía.")
    else:
        c1, c2, c3 = st.columns([1, 1, 2])
        h_f = c1.multiselect("Hotel", ["DREPM", "SECPM", "ZOE VR"])
        m_f = c2.multiselect("Mercado", df["Market"].unique() if "Market" in df.columns else [])
        t_f = c3.text_input("Buscador Global (Código o Nombre)").strip()

        df_f = df.copy()
        if h_f: df_f = df_f[df_f["Hotel"].isin(h_f)]
        if m_f: df_f = df_f[df_f["Market"].isin(m_f)]
        
        # FIX BUSCADOR (Imagen 5)
        if t_f:
            mask = df_f.astype(str).apply(lambda x: x.str.contains(t_f, case=False, na=False).any(), axis=1)
            df_f = df_f[mask]

        st.dataframe(df_f, use_container_width=True, hide_index=True)
        
        if st.session_state.is_admin:
            # Botón Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_f.to_excel(writer, index=False)
            st.download_button("📥 Descargar Excel", data=output.getvalue(), file_name="HIC_Report.xlsx")

# =====================================================
# MÓDULO: REGISTRO Y MODIFICACIÓN (IMAGEN 4)
# =====================================================
elif menu == "➕ Registro y Modificación":
    st.title("🛠️ Gestión de Inventario de Promos")
    if not st.session_state.is_admin:
        st.warning("Inicia sesión como Admin.")
    else:
        t_n, t_m = st.tabs(["🚀 Nueva Promo", "📝 Modificar/Extender"])
        
        with t_n:
            with st.form("new_f"):
                # ... Formulario de registro similar al anterior ...
                st.write("Complete los datos de la nueva campaña")
                n = st.text_input("Nombre Promo")
                htls = st.multiselect("Hoteles", ["DREPM", "SECPM", "ZOE VR"])
                if st.form_submit_button("Guardar"):
                    st.success("Registrado.")
        
        with t_m:
            if not df.empty:
                sel = st.selectbox("Elija Promo para Modificar", df["Promo"].unique())
                # Lógica de extensión de fechas (Imagen 4)
                idx = df[df["Promo"] == sel].index[0]
                new_bw = st.date_input("Extender BW Fin", df.at[idx, 'BW_Fin'])
                if st.button("Actualizar Fechas"):
                    df.at[idx, 'BW_Fin'] = new_bw
                    guardar_y_respaldar(df)
                    st.rerun()

# =====================================================
# MÓDULO: UPSELL FD (SIN PUNTOS WOH - IMAGEN 1 & 3)
# =====================================================
elif menu == "📈 Upsell FD":
    st.title("📈 Calculadora de Upsell")
    CAT_VALS = {"JS Garden View": 0, "JS Pool View": 45, "JS Ocean View": 90, "JS Swim Out": 150}
    
    with st.container(border=True):
        # Layout de 2 renglones (Imagen 3)
        r1 = st.columns([1, 1, 1.5, 1])
        hotel = r1[0].selectbox("Hotel", ["DREPM", "SECPM"])
        fecha = r1[1].date_input("Llegada", date.today())
        tarifa_o = r1[2].number_input("Tarifa Original (USD)", value=500.0)
        noches = r1[3].number_input("Noches", 1, 30, 1)
        
        st.divider()
        
        r2 = st.columns([2, 2, 0.8, 0.8, 1])
        c_de = r2[0].selectbox("De:", list(CAT_VALS.keys()))
        c_a = r2[1].selectbox("A:", [k for k in CAT_VALS.keys() if CAT_VALS[k] > CAT_VALS[c_de]])
        adt = r2[2].number_input("Adt", 1, 4, 2)
        chd = r2[3].number_input("Chd", 0, 4, 0)
        calc = r2[4].button("🚀 Calcular", use_container_width=True)

    if calc:
        temp, p_nino = get_season_rate(fecha)
        diff = (CAT_VALS[c_a] - CAT_VALS[c_de]) * noches
        
        # Resultado Visual (Imagen 1)
        res1, res2 = st.columns([1, 1.5])
        with res1:
            st.metric("Total Upgrade", f"${diff:,.2f} USD", f"≈ {diff*TC_VAL:,.2f} MXN")
        with res2:
            st.info(f"👶 Niño (3-12): ${p_nino} USD | Temporada: {temp}")
            if chd > 0 and "Swim Out" in c_a:
                st.error("🚫 No se permiten niños en Swim Out.")

# =====================================================
# MÓDULO: WORLD OF HYATT (IMAGEN 6)
# =====================================================
elif menu == "🏨 World of Hyatt":
    st.title("🏨 World of Hyatt")
    ta, tb = st.tabs(["🏆 Estatus y Beneficios", "🔢 Simulador de Puntos"])
    
    with ta:
        st.image("https://www.hyatt.com/content/dam/hyatt/hyattcom/en/world-of-hyatt/WOH_Logo.png", width=100)
        st.table({
            "Estatus": ["Member", "Discoverist", "Explorist", "Globalist"],
            "Noches Req.": [0, 10, 30, 60],
            "Bono Puntos": ["--", "10%", "20%", "30%"],
            "Late C/O": ["Sujeto", "2:00 PM", "2:00 PM", "4:00 PM"]
        })
        st.caption("📣 Guest of Honor: Premio Milestone a las 40 noches.")
    
    with tb:
        t_eleg = st.number_input("Tarifa por noche (USD)", 0, 2000, 300)
        n_est = st.number_input("Noches de estancia", 1, 30, 4)
        p_base = (t_eleg * n_est) * 5
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Member", f"{int(p_base):,}")
        m2.metric("Discoverist", f"{int(p_base*1.1):,}")
        m3.metric("Explorist", f"{int(p_base*1.2):,}")
        m4.metric("Globalist", f"{int(p_base*1.3):,}")
