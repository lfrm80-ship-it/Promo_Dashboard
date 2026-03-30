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
# MÓDULO: REGISTRO (UPLOADER RESTAURADO)
# =====================================================
elif menu == "➕ Registro de Promoción":
    st.title("➕ Nueva Promoción")
    if not st.session_state.is_admin:
        st.warning("Acceso restringido a Administradores.")
    else:
        with st.form("reg_form", clear_on_submit=True):
            c1, c2 = st.columns([2, 1])
            nombre = c1.text_input("Nombre de la Promoción")
            hoteles = c2.multiselect("Hoteles aplicables", ["DREPM", "SECPM", "ZOE VR"])
            
            m1, m2, m3 = st.columns(3)
            mercado = m1.selectbox("Mercado", ["USA", "CAN", "MEX", "LATAM", "EUR", "Worldwide"])
            rate_code = m2.text_input("Rate Plan Code")
            dscto = m3.number_input("Descuento %", 0, 100, 0)
            
            d1, d2, d3, d4 = st.columns(4)
            bw_i, bw_f = d1.date_input("BW Inicio"), d2.date_input("BW Fin")
            tw_i, tw_f = d3.date_input("TW Inicio"), d4.date_input("TW Fin")
            
            st.divider()
            archivo = st.file_uploader("Adjuntar JPEG, PDF o Excel", type=["pdf", "jpg", "png", "xlsx"])
            notas = st.text_area("Notas / Restricciones")
            
            if st.form_submit_button("🚀 Guardar en Master Record"):
                if nombre and hoteles:
                    nuevas = pd.DataFrame([{"Hotel": h, "Promo": nombre, "Market": mercado, "Rate_Plan": rate_code, "Descuento": dscto, "BW_Inicio": bw_i, "BW_Fin": bw_f, "TW_Inicio": tw_i, "TW_Fin": tw_f, "Notas": notas} for h in hoteles])
                    df = pd.concat([df, nuevas], ignore_index=True)
                    guardar_datos(df)
                    st.success("✅ Promoción registrada exitosamente.")
                    st.rerun()

# =====================================================
# MÓDULO: UPSELL (ORDEN OPERATIVO ACTUALIZADO)
# =====================================================
elif menu == "📈 Upsell":
    st.title("📈 Calculadora de Upsell")
    CAT_VALS = {"JS Garden View": 0, "JS Pool View": 45, "JS Ocean View": 90, "JS Swim Out": 150}
    
    with st.container(border=True):
        # Ajustamos el ancho de las columnas para el nuevo orden
        row_main = st.columns([1, 1.2, 1, 1, 1.1, 0.6, 0.6, 0.8, 1])
        
        # 1. Datos del Hotel y Estancia
        h_sel = row_main[0].selectbox("Hotel", ["DREPM", "SECPM"], index=0)
        f_sel = row_main[1].date_input("Llegada", date.today())
        
        # 2. Categorías (El "Upgrade")
        h_orig = row_main[2].selectbox("De:", list(CAT_VALS.keys()))
        h_dest = row_main[3].selectbox("A:", [k for k in CAT_VALS.keys() if CAT_VALS[k] > CAT_VALS[h_orig]])
        
        # 3. Tarifas (Movido antes de la ocupación)
        t_orig = row_main[4].number_input("Tarifa Orig.", min_value=1.0, value=500.0)
        
        # 4. Ocupación y Noches
        ads = row_main[5].number_input("Adt", 1, 4, 2)
        
        if h_sel == "DREPM":
            nns = row_main[6].number_input("Chd", 0, 4, 0)
            nits = row_main[7].number_input("Nts", 1, 30, 1)
            btn_calc = row_main[8].button("🚀 Calcular", use_container_width=True)
        else:
            nns = 0
            # Espacio reservado para mantener alineación en SECPM
            row_main[6].markdown("<p style='text-align:center; padding-top:35px; color:gray;'>N/A</p>", unsafe_allow_html=True)
            nits = row_main[7].number_input("Nts", 1, 30, 1)
            btn_calc = row_main[8].button("🚀 Calcular", use_container_width=True)

    if btn_calc:
        temp, p_kid = detectar_temporada(f_sel)
        dif_noche = (CAT_VALS.get(h_dest, 0) - CAT_VALS[h_orig]) * (1.25 if temp == "OK RM" else 1)
        total_up = dif_noche * nits
        gran_total = t_orig + total_up
        
        res1, res2 = st.columns([1, 1.5])
        with res1:
            st.markdown(f"""
                <div style="background-color:#f8f9fa; padding:15px; border-radius:10px; border-left: 5px solid #00338d; border: 1px solid #ddd;">
                    <p style="margin:0; font-size:0.9em; color:#666;">Upgrade Total</p>
                    <h2 style="margin:0; color:#00338d;">${total_up:,.2f} USD</h2>
                    <p style="margin:0; font-size:1.1em;">≈ {(total_up * TC_VAL):,.2f} MXN</p>
                    <hr style="margin:10px 0;">
                    <p style="margin:0; font-size:0.9em; color:#666;">Gran Total Estancia</p>
                    <h3 style="margin:0;">${gran_total:,.2f} USD</h3>
                </div>
            """, unsafe_allow_html=True)

        with res2:
            if h_sel == "DREPM":
                st.markdown("### 👶 Edades y Políticas")
                ed1, ed2, ed3 = st.columns(3)
                ed1.metric("Infantes", "0-2 años")
                ed2.metric("Niños", f"3-12 (${p_kid})")
                ed3.metric("Juniors", "13+ (Adulto)")
                if nns > 0 and "Swim Out" in h_dest:
                    st.error("⚠️ Categoría Swim Out: Solo adultos permitidos.")
            else:
                st.info("✨ Secrets: Propiedad Adults Only. Menores no permitidos.")
# =====================================================
# MÓDULO: WOH (CON CALCULADORA DE PUNTOS)
# =====================================================
elif menu == "🏨 WOH":
    st.title("🏨 World of Hyatt")
    tab1, tab2 = st.tabs(["🏅 Status y Niveles", "🧮 Calculadora de Puntos"])
    
    with tab1:
        st.table({"Nivel": ["Member", "Discoverist", "Explorist", "Globalist"], "Noches": ["0", "10", "30", "60"], "Bono": ["0%", "10%", "20%", "30%"]})
        st.write("🚩 **20 Noches:** 2 Club Access | **30 Noches:** 1 Free Night (Cat 1-4)")
        st.write("🚩 **40 Noches:** 1 Guest of Honor | **60 Noches:** My Hyatt Concierge")

    with tab2:
        st.subheader("🧮 Calculadora de Puntos por Estancia")
        with st.container(border=True):
            cw1, cw2 = st.columns(2)
            tarifa_noche = cw1.number_input("Tarifa por noche (USD)", min_value=0, value=250)
            total_noches = cw2.number_input("Número de noches ", min_value=1, value=1)
            
            monto_total = tarifa_noche * total_noches
            p_base = monto_total * 5
            
            st.divider()
            c_p1, c_p2, c_p3, c_p4 = st.columns(4)
            c_p1.metric("Member", f"{int(p_base):,}")
            c_p2.metric("Discoverist", f"{int(p_base * 1.1):,}")
            c_p3.metric("Explorist", f"{int(p_base * 1.2):,}")
            c_p4.metric("Globalist", f"{int(p_base * 1.3):,}")
