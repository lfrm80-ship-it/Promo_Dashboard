import streamlit as st
import pandas as pd
import os
import shutil
from datetime import datetime, date

# =====================================================
# 1. CONFIGURACIÓN DE PÁGINA Y RUTAS
# =====================================================
st.set_page_config(page_title="HIC Master Record", layout="wide", page_icon="🏨")

# Secretos y Directorios
ADMIN_PASSWORD = st.secrets.get("admin_password", "admin")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROMOS_FILE = os.path.join(BASE_DIR, "promociones_produccion.csv")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
MEDIA_DIR = os.path.join(BASE_DIR, "media")
TC_VAL = 18.50  # Tipo de cambio proyectado para 2026

for d in [BACKUP_DIR, MEDIA_DIR]:
    if not os.path.exists(d): os.makedirs(d)

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# =====================================================
# 2. MOTOR DE DATOS (REVENUE & LOGÍSTICA)
# =====================================================
def guardar_datos(df):
    df.to_csv(PROMOS_FILE, index=False)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    df.to_csv(os.path.join(BACKUP_DIR, f"backup_{ts}.csv"), index=False)

def cargar_datos():
    if not os.path.exists(PROMOS_FILE):
        return pd.DataFrame(columns=[
            "Hotel", "Promo", "Market", "Rate_Plan", "Descuento", 
            "BW_Inicio", "BW_Fin", "TW_Inicio", "TW_Fin", "Notas"
        ])
    df = pd.read_csv(PROMOS_FILE)
    for col in ["BW_Inicio", "BW_Fin", "TW_Inicio", "TW_Fin"]:
        if col in df.columns: df[col] = pd.to_datetime(df[col]).dt.date
    return df

def detectar_temporada(fecha):
    """Lógica de Revenue Management para temporadas críticas 2026"""
    # Semana Santa y Navidad 2026
    estancias_premium = [
        (date(2026, 3, 26), date(2026, 4, 13)), 
        (date(2026, 12, 20), date(2026, 12, 31))
    ]
    for inicio, fin in estancias_premium:
        if inicio <= fecha <= fin: return "OK RM", 148 # Precio niño temporada alta
    return "REGULAR", 89 # Precio niño temporada regular

# =====================================================
# 3. SIDEBAR Y CONTROL DE ACCESO
# =====================================================
with st.sidebar:
    st.image("https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR6A7GfGq-o9f2A-V0uYmCqYFzP6oP2B4S-RA&s", width=200) 
    st.divider()
    menu = st.radio("Navegación", ["🔍 Vista rápida", "➕ Registro de Promoción", "📈 Upsell", "🏨 WOH"])
    st.divider()
    
    if st.session_state.is_admin:
        st.success("🔓 MODO ADMINISTRADOR")
        if st.button("Cerrar Sesión", use_container_width=True):
            st.session_state.is_admin = False
            st.rerun()
    else:
        with st.expander("🔐 Acceso Staff Senior"):
            pwd = st.text_input("Contraseña", type="password")
            if st.button("Desbloquear", use_container_width=True) and pwd == ADMIN_PASSWORD:
                st.session_state.is_admin = True
                st.rerun()

df = cargar_datos()

# =====================================================
# MÓDULO 1: VISTA RÁPIDA (BÚSQUEDA AVANZADA)
# =====================================================
if menu == "🔍 Vista rápida":
    st.title("🔎 Master Record de Promociones")
    if df.empty:
        st.info("Aún no hay promociones registradas. Contacta al Distribution Manager.")
    else:
        f_col1, f_col2, f_col3 = st.columns([1, 1, 1.5])
        h_filtro = f_col1.multiselect("Hotel", ["DREPM", "SECPM", "ZOE VR"])
        m_filtro = f_col2.multiselect("Mercado", df["Market"].unique())
        t_busqueda = f_col3.text_input("Palabra clave (Promo o Rate Code)")

        df_display = df.copy()
        if h_filtro: df_display = df_display[df_display["Hotel"].isin(h_filtro)]
        if m_filtro: df_display = df_display[df_display["Market"].isin(m_filtro)]
        if t_busqueda:
            df_display = df_display[df_display.astype(str).apply(lambda x: t_busqueda.lower() in x.str.lower().any(), axis=1)]

        st.dataframe(df_display, use_container_width=True, hide_index=True)

# =====================================================
# MÓDULO 2: REGISTRO (SOLO ADMIN)
# =====================================================
elif menu == "➕ Registro de Promoción":
    st.title("➕ Alta de Nueva Campaña")
    if not st.session_state.is_admin:
        st.error("No tienes permisos para modificar el Master Record.")
    else:
        with st.form("main_form", clear_on_submit=True):
            c1, c2 = st.columns([2, 1])
            nombre_promo = c1.text_input("Nombre Oficial de la Promo")
            hoteles_afectados = c2.multiselect("Hoteles", ["DREPM", "SECPM", "ZOE VR"])
            
            m1, m2, m3 = st.columns(3)
            mercado_target = m1.selectbox("Mercado Geográfico", ["USA", "CAN", "MEX", "LATAM", "EUR", "Worldwide"])
            plan_code = m2.text_input("Rate Plan (Ej: PKGUP)")
            pct_desc = m3.number_input("Descuento (%)", 0, 100, 0)
            
            d1, d2, d3, d4 = st.columns(4)
            bw_start = d1.date_input("Booking Start")
            bw_end = d2.date_input("Booking End")
            tw_start = d3.date_input("Travel Start")
            tw_end = d4.date_input("Travel End")
            
            st.divider()
            up_file = st.file_uploader("Subir PDF de la Promo", type=["pdf", "jpg", "png"])
            comentarios = st.text_area("Restricciones o Notas de Combinabilidad")
            
            if st.form_submit_button("🚀 Publicar en Master Record"):
                if nombre_promo and hoteles_afectados:
                    nuevos_registros = pd.DataFrame([{
                        "Hotel": h, "Promo": nombre_promo, "Market": mercado_target, 
                        "Rate_Plan": plan_code, "Descuento": pct_desc, 
                        "BW_Inicio": bw_start, "BW_Fin": bw_end, 
                        "TW_Inicio": tw_start, "TW_Fin": tw_end, "Notas": comentarios
                    } for h in hoteles_afectados])
                    
                    df = pd.concat([df, nuevos_registros], ignore_index=True)
                    guardar_datos(df)
                    st.success("¡Promoción guardada y respaldada en la nube!")
                    st.rerun()

# =====================================================
# MÓDULO 3: UPSELL (LAYOUT PRO DE 2 RENGLONES)
# =====================================================
elif menu == "📈 Upsell":
    st.title("📈 Calculadora de Upsell Front Desk")
    # Valores de referencia Hyatt Inclusive
    CAT_VALS = {"JS Garden View": 0, "JS Pool View": 45, "JS Ocean View": 90, "JS Swim Out": 150}
    
    with st.container(border=True):
        # RENGLÓN 1: LOGÍSTICA
        r1 = st.columns([1, 1.2, 1.2, 1])
        hotel = r1[0].selectbox("Propiedad", ["DREPM", "SECPM"])
        llegada = r1[1].date_input("Fecha de Arribo", date.today())
        p_original = r1[2].number_input("Tarifa Original (USD)", min_value=1.0, value=500.0)
        noches = r1[3].number_input("Estancia (Nts)", 1, 30, 1)

        st.markdown("<hr style='margin:10px 0; border:0.5px solid #eee;'>", unsafe_allow_html=True)

        # RENGLÓN 2: CATEGORÍAS Y PAX
        if hotel == "DREPM":
            r2 = st.columns([2, 2, 0.8, 0.8, 1.2])
            c_ori = r2[0].selectbox("De:", list(CAT_VALS.keys()))
            c_des = r2[1].selectbox("A:", [k for k in CAT_VALS.keys() if CAT_VALS[k] > CAT_VALS[c_ori]])
            adultos = r2[2].number_input("Adt", 1, 4, 2)
            ninos = r2[3].number_input("Chd", 0, 4, 0)
            btn_upsell = r2[4].button("🚀 Calcular", use_container_width=True)
        else:
            r2 = st.columns([2, 2, 0.8, 1.2]) # Secrets: Sin campo de niños
            c_ori = r2[0].selectbox("De:", list(CAT_VALS.keys()))
            c_des = r2[1].selectbox("A:", [k for k in CAT_VALS.keys() if CAT_VALS[k] > CAT_VALS[c_ori]])
            adultos = r2[2].number_input("Adt", 1, 4, 2)
            ninos = 0
            btn_upsell = r2[3].button("🚀 Calcular", use_container_width=True)

    if btn_upsell:
        status_rm, p_nino = detectar_temporada(llegada)
        markup = 1.25 if status_rm == "OK RM" else 1.0 # Incremento por temporada alta
        
        diff_base = (CAT_VALS[c_des] - CAT_VALS[c_ori]) * markup
        total_upsell = diff_base * noches
        
        c_res1, c_res2 = st.columns([1, 1.5])
        with c_res1:
            st.markdown(f"""
                <div style="background-color:#f0f2f6; padding:20px; border-radius:10px; border: 1px solid #00338d;">
                    <h5 style="color:#00338d; margin:0;">Monto de Upgrade</h5>
                    <h2 style="margin:0;">${total_upsell:,.2f} USD</h2>
                    <p style="color:gray;">≈ {(total_upsell * TC_VAL):,.2f} MXN</p>
                    <hr>
                    <h6 style="margin:0;">Total Estancia: ${p_original + total_upsell:,.2f} USD</h6>
                </div>
            """, unsafe_allow_html=True)
        
        with c_res2:
            if hotel == "DREPM":
                st.markdown(f"### 👶 Recordatorio de Edades ({status_rm})")
                col_e1, col_e2 = st.columns(2)
                col_e1.metric("Niño (3-12)", f"${p_nino} USD")
                col_e2.metric("Infante", "$0 USD")
                if ninos > 0 and "Swim Out" in c_des:
                    st.error("⚠️ POLÍTICA: No se permiten menores en habitaciones Swim Out.")
            else:
                st.info("✨ SECPM: Propiedad exclusiva para adultos. Confirmar ID de todos los huéspedes.")

# =====================================================
# MÓDULO 4: WORLD OF HYATT (BENEFICIOS 2026)
# =====================================================
elif menu == "🏨 WOH":
    st.title("🏨 Ecosistema World of Hyatt")
    t1, t2 = st.tabs(["🏆 Niveles y Milestones", "🔢 Simulador de Puntos"])
    
    with t1:
        st.subheader("Beneficios por Nivel")
        beneficios = {
            "Nivel": ["Member", "Discoverist", "Explorist", "Globalist"],
            "Noches": ["0", "10", "30", "60"],
            "Bono Pts": ["--", "10%", "20%", "30%"],
            "Late C/O": ["Sujeto", "2:00 PM", "2:00 PM", "4:00 PM"]
        }
        st.table(beneficios)
        st.warning("📣 Guest of Honor: Ahora es un premio Milestone al alcanzar las 40 noches.")

    with t2:
        st.subheader("Simulador de Acumulación")
        with st.container(border=True):
            w_col1, w_col2 = st.columns(2)
            tarifa_n = w_col1.number_input("Tarifa noche (USD)", 0, 1000, 300)
            noches_w = w_col2.number_input("Noches", 1, 30, 4)
            
            p_base = (tarifa_n * noches_w) * 5
            
            st.divider()
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Base (Member)", f"{int(p_base):,}")
            m2.metric("Discoverist", f"{int(p_base * 1.1):,}")
            m3.metric("Explorist", f"{int(p_base * 1.2):,}")
            m4.metric("Globalist", f"{int(p_base * 1.3):,}")
