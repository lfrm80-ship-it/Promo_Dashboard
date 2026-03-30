import streamlit as st
import pandas as pd
import os
from datetime import datetime, date

# =====================================================
# 1. CONFIGURACIÓN Y ESTILOS PRO
# =====================================================
st.set_page_config(page_title="HIC Master Record", layout="wide", page_icon="🏨")

st.markdown("""
    <style>
    .result-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #e0e0e0;
        border-left: 6px solid #00338d;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
    }
    .status-tag {
        font-weight: bold;
        padding: 4px 10px;
        border-radius: 5px;
        text-transform: uppercase;
        font-size: 0.8em;
    }
    </style>
""", unsafe_allow_html=True)

# Configuración de archivos y rutas
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
# 3. SIDEBAR (NAVEGACIÓN)
# =====================================================
with st.sidebar:
    st.image("https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR6A7GfGq-o9f2A-V0uYmCqYFzP6oP2B4S-RA&s", width=200) 
    st.divider()
    menu = st.radio("Menú Principal", ["🔍 Vista rápida", "➕ Registro de Promoción", "📈 Upsell", "🏨 WOH"])
    st.divider()
    
    if st.session_state.is_admin:
        st.success("🔓 MODO ADMINISTRADOR")
        if st.button("Cerrar Sesión", use_container_width=True):
            st.session_state.is_admin = False
            st.rerun()
    else:
        with st.expander("🔐 Acceso Personal"):
            pwd = st.text_input("Contraseña", type="password")
            if st.button("Ingresar", use_container_width=True) and pwd == ADMIN_PASSWORD:
                st.session_state.is_admin = True
                st.rerun()

df = cargar_datos()

# =====================================================
# MÓDULO: VISTA RÁPIDA (FILTROS + EDICIÓN ADMIN)
# =====================================================
if menu == "🔍 Vista rápida":
    st.title("🔎 Consulta de Promociones")
    if df.empty:
        st.info("No hay promociones en la base de datos.")
    else:
        f1, f2, f3 = st.columns(3)
        h_f = f1.multiselect("Filtrar Hotel", df["Hotel"].unique())
        m_f = f2.multiselect("Filtrar Mercado", df["Market"].unique())
        t_f = f3.text_input("Buscar por nombre/código")

        df_f = df.copy()
        if h_f: df_f = df_f[df_f["Hotel"].isin(h_f)]
        if m_f: df_f = df_f[df_f["Market"].isin(m_f)]
        if t_f: df_f = df_f[df_f.astype(str).apply(lambda x: t_f.lower() in x.str.lower().any(), axis=1)]

        st.dataframe(df_f, use_container_width=True, hide_index=True)

        if st.session_state.is_admin and not df_f.empty:
            with st.expander("📝 Editar / Extender Promoción"):
                target = st.selectbox("Selecciona para editar", df_f["Promo"].unique())
                idx = df[df["Promo"] == target].index[0]
                ce1, ce2 = st.columns(2)
                n_bw = ce1.date_input("Nuevo BW Fin", value=df.at[idx, "BW_Fin"])
                n_tw = ce2.date_input("Nuevo TW Fin", value=df.at[idx, "TW_Fin"])
                if st.button("Guardar Cambios"):
                    df.at[idx, "BW_Fin"], df.at[idx, "TW_Fin"] = n_bw, n_tw
                    guardar_datos(df)
                    st.success("Promoción actualizada.")
                    st.rerun()

# =====================================================
# MÓDULO: REGISTRO (CON CARGA DE ARCHIVOS)
# =====================================================
elif menu == "➕ Registro de Promoción":
    st.title("➕ Alta de Nueva Promo")
    if not st.session_state.is_admin:
        st.warning("⚠️ Función exclusiva para administradores.")
    else:
        with st.form("new_promo_form", clear_on_submit=True):
            col1, col2 = st.columns([2, 1])
            nombre = col1.text_input("Nombre de la Promoción")
            hoteles = col2.multiselect("Hoteles", ["DREPM", "SECPM", "ZOE VR"])
            
            c1, c2, c3 = st.columns(3)
            mercado = c1.selectbox("Mercado", ["USA", "CAN", "MEX", "LATAM", "EUR", "Worldwide"])
            rate_code = c2.text_input("Rate Code")
            dscto = c3.number_input("Descuento (%)", 0, 100, 0)
            
            d1, d2, d3, d4 = st.columns(4)
            bw_i, bw_f = d1.date_input("BW Inicio"), d2.date_input("BW Fin")
            tw_i, tw_f = d3.date_input("TW Inicio"), d4.date_input("TW Fin")
            
            st.divider()
            archivo = st.file_uploader("Adjuntar JPEG, PDF o Excel", type=["jpg", "jpeg", "png", "pdf", "xlsx"])
            notas = st.text_area("Notas / Restricciones adicionales")
            
            if st.form_submit_button("🚀 Registrar en Master Record"):
                if nombre and hoteles:
                    nuevas = pd.DataFrame([{"Hotel": h, "Promo": nombre, "Market": mercado, "Rate_Plan": rate_code, "Descuento": dscto, "BW_Inicio": bw_i, "BW_Fin": bw_f, "TW_Inicio": tw_i, "TW_Fin": tw_f, "Notas": notas} for h in hoteles])
                    df = pd.concat([df, nuevas], ignore_index=True)
                    guardar_datos(df)
                    st.success("✅ Promoción guardada correctamente.")
                    st.rerun()

# =====================================================
# MÓDULO: UPSELL (SÚPER COMPACTO + EDADES + PUNTOS)
# =====================================================
elif menu == "📈 Upsell":
    st.title("📈 Calculadora de Upsell Front Desk")
    CAT_VALS = {"JS Garden View": 0, "JS Pool View": 45, "JS Ocean View": 90, "JS Swim Out": 150}
    
    col_u1, col_u2 = st.columns([1.2, 1])
    
    with col_u1:
        with st.container(border=True):
            st.subheader("📋 Datos")
            h_sel = st.selectbox("Hotel", ["DREPM", "SECPM"])
            f_sel = st.date_input("Fecha llegada")
            
            st.write("**Categorías**")
            cl1, cl2, cl3 = st.columns([4, 1, 4])
            h_orig = cl1.selectbox("De:", list(CAT_VALS.keys()), label_visibility="collapsed")
            cl2.markdown("<h3 style='text-align:center;'>➡️</h3>", unsafe_allow_html=True)
            posibles = [k for k in CAT_VALS.keys() if CAT_VALS[k] > CAT_VALS[h_orig]]
            h_dest = cl3.selectbox("A:", posibles if posibles else ["Máxima"], label_visibility="collapsed")
            
            cu1, cu2, cu3 = st.columns(3)
            adults = cu1.number_input("Adultos", 1, 4, 2)
            kids = cu2.number_input("Niños (0-12)", 0, 4, 0) if h_sel == "DREPM" else 0
            nights = cu3.number_input("Noches", 1, 30, 1)
            
            tarifa = st.number_input("Tarifa Original Total (USD)", min_value=1.0, value=500.0)
            btn_calc = st.button("🚀 Calcular Upgrade", use_container_width=True)

    with col_u2:
        if btn_calc:
            temp, p_kid = detectar_temporada(f_sel)
            dif_noche = (CAT_VALS.get(h_dest, 0) - CAT_VALS[h_orig]) * (1.25 if temp == "OK RM" else 1)
            total_up = dif_noche * nights
            
            st.markdown(f"""
                <div class="result-card">
                    <p style="margin:0; color:#666;">Temporada: <b>{temp}</b></p>
                    <h2 style="margin:10px 0; color:#00338d;">${total_up:,.2f} USD</h2>
                    <p style="font-size:1.2em; margin:0;">≈ {(total_up * TC_VAL):,.2f} MXN</p>
                    <hr>
                    <p style="margin:0;">Total con Upgrade: <b>${(tarifa + total_up):,.2f} USD</b></p>
                </div>
            """, unsafe_allow_html=True)
            
            # --- EDADES (VITAL PARA RESERVAS) ---
            if h_sel == "DREPM":
                st.divider()
                st.subheader("👶 Política de Menores")
                ed1, ed2, ed3 = st.columns(3)
                ed1.info("**Infantes**\n0-2 años: $0")
                ed2.success(f"**Menores**\n3-12 años: ${p_kid} USD")
                ed3.warning("**Juniors**\n13+ años: Adulto")

            # --- CALCULADORA WOH POR NIVEL ---
            st.divider()
            st.subheader("💎 Puntos WOH por este Upsell")
            p_base = total_up * 5
            pw1, pw2 = st.columns(2)
            pw1.metric("Member", f"{int(p_base):,}")
            pw1.metric("Discoverist", f"{int(p_base * 1.1):,}")
            pw2.metric("Explorist", f"{int(p_base * 1.2):,}")
            pw2.metric("Globalist", f"{int(p_base * 1.3):,}")
            
            if kids > 0 and "Swim Out" in h_dest:
                st.error("🚫 No menores en Swim Out.")
        else:
            st.info("Ingresa los datos para ver el cálculo y los puntos acumulados.")

# =====================================================
# MÓDULO: WOH (CON CALCULADORA POR NOCHE)
# =====================================================
elif menu == "🏨 WOH":
    st.title("🏨 World of Hyatt - Programa de Lealtad")
    tab1, tab2, tab3 = st.tabs(["🏅 Status", "🎯 Milestones", "🧮 Calculadora de Puntos"])
    
    with tab1:
        st.table({
            "Nivel": ["Member", "Discoverist", "Explorist", "Globalist"],
            "Noches": ["0", "10", "30", "60"],
            "Bono Extra": ["0%", "10%", "20%", "30%"],
            "Late C/O": ["-", "2:00 PM", "2:00 PM", "4:00 PM"]
        })
        
    with tab2:
        st.markdown("### Premios por Noches Acumuladas (Año Calendario)")
        c_m1, c_m2 = st.columns(2)
        c_m1.write("🚩 **20 Noches:** 2 Club Access o 2k Pts")
        c_m1.write("🚩 **30 Noches:** 1 Free Night (Cat 1-4)")
        c_m2.write("🚩 **40 Noches:** 1 Guest of Honor Award")
        c_m2.write("🚩 **60 Noches:** My Hyatt Concierge + 1 Free Night (Cat 1-7)")

    with tab3:
        st.subheader("🧮 Calculadora de Acumulación por Noche")
        with st.container(border=True):
            cw1, cw2 = st.columns(2)
            monto_noche = cw1.number_input("Monto por Noche (USD Elegible)", min_value=0, value=200)
            n_noches = cw2.number_input("Cantidad de Noches", min_value=1, value=1)
            
            p_base_noche = monto_noche * 5
            st.divider()
            st.write(f"**Puntos acumulados por {n_noches} noche(s):**")
            
            pc1, pc2, pc3, pc4 = st.columns(4)
            pc1.metric("Member", f"{int(p_base_noche * n_noches):,}")
            pc2.metric("Discoverist", f"{int(p_base_noche * 1.1 * n_noches):,}")
            pc3.metric("Explorist", f"{int(p_base_noche * 1.2 * n_noches):,}")
            pc4.metric("Globalist", f"{int(p_base_noche * 1.3 * n_noches):,}")
