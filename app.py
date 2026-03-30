import streamlit as st
import pandas as pd
import os
from datetime import datetime, date

# =====================================================
# CONFIGURACIÓN Y ESTILOS
# =====================================================
st.set_page_config(page_title="HIC Master Record", layout="wide", page_icon="🏨")

# Estilo personalizado para las tarjetas de resultados
st.markdown("""
    <style>
    .metric-card {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #00338d;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

# Variables de entorno y rutas
ADMIN_PASSWORD = st.secrets.get("admin_password", "admin")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROMOS_FILE = os.path.join(BASE_DIR, "promociones_produccion.csv")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
MEDIA_DIR = os.path.join(BASE_DIR, "media")
TC_VAL = 18.50 # Tipo de cambio fijo para cálculos rápidos

for d in [BACKUP_DIR, MEDIA_DIR]:
    if not os.path.exists(d): os.makedirs(d)

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# =====================================================
# FUNCIONES DE DATOS
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
    # Fechas críticas (Semana Santa, Navidad, etc.)
    estancias_ok = [(date(2026, 3, 26), date(2026, 4, 13)), (date(2026, 12, 20), date(2026, 12, 31))]
    for inicio, fin in estancias_ok:
        if inicio <= fecha <= fin: return "OK RM", 148
    return "REGULAR", 89

# =====================================================
# SIDEBAR
# =====================================================
with st.sidebar:
    st.image("https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR6A7GfGq-o9f2A-V0uYmCqYFzP6oP2B4S-RA&s", width=200) 
    st.divider()
    menu = st.radio("Navegación", ["🔍 Vista rápida", "➕ Registro de Promoción", "📈 Upsell", "🏨 WOH"])
    st.divider()
    
    if st.session_state.is_admin:
        st.success("🟢 MODO ADMIN ACTIVO")
        if st.button("Salir de Admin", use_container_width=True):
            st.session_state.is_admin = False
            st.rerun()
    else:
        with st.expander("🔐 Acceso Admin"):
            pwd = st.text_input("Contraseña", type="password")
            if st.button("Entrar", use_container_width=True) and pwd == ADMIN_PASSWORD:
                st.session_state.is_admin = True
                st.rerun()

df = cargar_datos()

# =====================================================
# MÓDULO: VISTA RÁPIDA
# =====================================================
if menu == "🔍 Vista rápida":
    st.title("🔎 Master Record de Promociones")
    if df.empty:
        st.info("No hay promociones registradas aún.")
    else:
        # Filtros en columnas
        c1, c2, c3 = st.columns(3)
        h_f = c1.multiselect("Hotel", df["Hotel"].unique())
        m_f = c2.multiselect("Mercado", df["Market"].unique())
        t_f = c3.text_input("Buscar por nombre o Rate Code")

        df_f = df.copy()
        if h_f: df_f = df_f[df_f["Hotel"].isin(h_f)]
        if m_f: df_f = df_f[df_f["Market"].isin(m_f)]
        if t_f: df_f = df_f[df_f.astype(str).apply(lambda x: t_f.lower() in x.str.lower().any(), axis=1)]

        st.dataframe(df_f, use_container_width=True, hide_index=True)

        if st.session_state.is_admin and not df_f.empty:
            with st.expander("📝 Panel de Edición Rápida"):
                target = st.selectbox("Selecciona promo a extender", df_f["Promo"].unique())
                idx = df[df["Promo"] == target].index[0]
                ce1, ce2 = st.columns(2)
                n_bw = ce1.date_input("Extender BW hasta", value=df.at[idx, "BW_Fin"])
                n_tw = ce2.date_input("Extender TW hasta", value=df.at[idx, "TW_Fin"])
                if st.button("Actualizar Fechas"):
                    df.at[idx, "BW_Fin"], df.at[idx, "TW_Fin"] = n_bw, n_tw
                    guardar_datos(df)
                    st.success("¡Promoción extendida!")
                    st.rerun()

# =====================================================
# MÓDULO: REGISTRO (CON UPLOADER RESTAURADO)
# =====================================================
elif menu == "➕ Registro de Promoción":
    st.title("➕ Nueva Promoción")
    if not st.session_state.is_admin:
        st.warning("⚠️ Debes ser Admin para registrar nuevas promociones.")
    else:
        with st.form("registro_form", clear_on_submit=True):
            col1, col2 = st.columns([2, 1])
            nombre = col1.text_input("Nombre de la Promoción")
            hoteles = col2.multiselect("Hoteles aplicables", ["DREPM", "SECPM", "ZOE VR"])
            
            c1, c2, c3 = st.columns(3)
            mercado = c1.selectbox("Mercado", ["USA", "CAN", "MEX", "LATAM", "EUR", "Worldwide"])
            rate_code = c2.text_input("Rate Plan Code")
            dscto = c3.number_input("Descuento %", 0, 100, 0)
            
            d1, d2, d3, d4 = st.columns(4)
            bw_i, bw_f = d1.date_input("BW Inicio"), d2.date_input("BW Fin")
            tw_i, tw_f = d3.date_input("TW Inicio"), d4.date_input("TW Fin")
            
            # --- SECCIÓN DE ARCHIVOS RESTAURADA ---
            st.divider()
            st.markdown("### 📄 Documentación de Respaldo")
            archivo = st.file_uploader("Subir JPEG, PDF o Excel de la promoción", type=["jpg", "jpeg", "png", "pdf", "xlsx"])
            notas = st.text_area("Notas u observaciones adicionales")
            
            if st.form_submit_button("🚀 Guardar en Master Record"):
                if nombre and hoteles:
                    # Guardar archivo si existe
                    if archivo:
                        path = os.path.join(MEDIA_DIR, f"{datetime.now().strftime('%Y%m%d')}_{archivo.name}")
                        with open(path, "wb") as f: f.write(archivo.getbuffer())
                    
                    nuevas = pd.DataFrame([{"Hotel": h, "Promo": nombre, "Market": mercado, "Rate_Plan": rate_code, "Descuento": dscto, "BW_Inicio": bw_i, "BW_Fin": bw_f, "TW_Inicio": tw_i, "TW_Fin": tw_f, "Notas": notas} for h in hoteles])
                    df = pd.concat([df, nuevas], ignore_index=True)
                    guardar_datos(df)
                    st.success("✅ Registro exitoso.")
                    st.rerun()

# =====================================================
# MÓDULO: UPSELL
# =====================================================
elif menu == "📈 Upsell":
    st.title("📈 Calculadora de Upsell")
    CAT_VALS = {"JS Garden View": 0, "JS Pool View": 45, "JS Ocean View": 90, "JS Swim Out": 150}
    
    col_u1, col_u2 = st.columns([1.2, 1])
    
    with col_u1:
        with st.container(border=True):
            st.subheader("📋 Datos")
            h_sel = st.selectbox("Hotel", ["DREPM", "SECPM"])
            f_sel = st.date_input("Fecha llegada")
            
            st.write("**Cambio de Categoría**")
            cl1, cl2, cl3 = st.columns([4, 1, 4])
            h_orig = cl1.selectbox("De:", list(CAT_VALS.keys()), label_visibility="collapsed")
            cl2.markdown("<h3 style='text-align:center; margin-top:0;'>➡️</h3>", unsafe_allow_html=True)
            posibles = [k for k in CAT_VALS.keys() if CAT_VALS[k] > CAT_VALS[h_orig]]
            h_dest = cl3.selectbox("A:", posibles if posibles else ["Máxima"], label_visibility="collapsed")
            
            cu1, cu2, cu3 = st.columns(3)
            adults = cu1.number_input("Adultos", 1, 4, 2)
            kids = cu2.number_input("Niños", 0, 4, 0) if h_sel == "DREPM" else 0
            nights = cu3.number_input("Noches", 1, 30, 1)
            tarifa = st.number_input("Tarifa Original (Total USD)", min_value=1.0, value=500.0)

    with col_u2:
        temp, p_kid = detectar_temporada(f_sel)
        dif_noche = (CAT_VALS.get(h_dest, 0) - CAT_VALS[h_orig]) * (1.25 if temp == "OK RM" else 1)
        total_up = dif_noche * nights
        
        st.markdown(f"""
            <div class="metric-card">
                <p style="margin:0; color:#666;">Temporada: <b>{temp}</b></p>
                <h2 style="margin:10px 0; color:#00338d;">${total_up:,.2f} USD</h2>
                <p style="font-size:1.2em; margin:0;">≈ {total_up * TC_VAL:,.2f} MXN</p>
                <hr>
                <p style="margin:0;">Total con Upgrade: <b>${(tarifa + total_up):,.2f} USD</b></p>
            </div>
        """, unsafe_allow_html=True)
        
        if kids > 0:
            if "Swim Out" in h_dest: st.error("🚫 No se permiten niños en Swim Out.")
            else: st.info(f"👶 Menor (3-12): ${p_kid} USD/Noche")

# =====================================================
# MÓDULO: WOH
# =====================================================
elif menu == "🏨 WOH":
    st.title("🏨 World of Hyatt")
    t1, t2, t3 = st.tabs(["🏅 Status & Niveles", "🎯 Milestones", "🧮 Calculadora"])
    
    with t1:
        st.table({"Nivel": ["Member", "Discoverist", "Explorist", "Globalist"], "Noches": ["0", "10", "30", "60"], "Bono": ["0%", "10%", "20%", "30%"]})
        st.markdown("**Beneficios Pro:** Discoverist (2pm LCO), Explorist (2pm LCO + Upgrade), Globalist (4pm LCO + Breakfast + Suite)")
        
    with t2:
        st.markdown("#### Premios por Noches Acumuladas")
        st.write("🚩 **20 Noches:** 2 Club Access Awards o 2k Puntos")
        st.write("🚩 **30 Noches:** 1 Free Night (Cat 1-4) + 2 Club Access")
        st.write("🚩 **40 Noches:** 1 Guest of Honor Award + Suite Upgrade")
        st.write("🚩 **60 Noches:** 2 GOH Awards + 2 Suite Upgrades + 1 Free Night (Cat 1-7)")

    with t3:
        monto = st.number_input("Gasto Elegible (USD)", 0, value=100)
        st.metric("Puntos Base (5x)", f"{monto * 5:,}")
        st.caption("Recuerda que los impuestos y propinas no generan puntos.")
