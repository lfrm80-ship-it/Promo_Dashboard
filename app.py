import streamlit as st
import pandas as pd
import os
import io
from datetime import datetime, date

# =====================================================
# CONFIGURACIÓN GENERAL
# =====================================================
st.set_page_config(page_title="HIC Master Record", layout="wide")

ADMIN_PASSWORD = st.secrets.get("admin_password", "admin")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROMOS_FILE = os.path.join(BASE_DIR, "promociones_produccion.csv")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
TC_VAL = 18.50

# Asegurar directorios
for d in [BACKUP_DIR, os.path.join(BASE_DIR, "media")]:
    if not os.path.exists(d): os.makedirs(d)

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# =====================================================
# FUNCIONES NÚCLEO
# =====================================================
def guardar_con_backup(df):
    if df is None or len(df) == 0:
        st.error("⛔ Error: El archivo no puede estar vacío.")
        return
    df.to_csv(PROMOS_FILE, index=False)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    df.to_csv(os.path.join(BACKUP_DIR, f"backup_{ts}.csv"), index=False)

def cargar_datos():
    if not os.path.exists(PROMOS_FILE): return pd.DataFrame()
    df = pd.read_csv(PROMOS_FILE)
    for col in ["BW_Inicio", "BW_Fin", "TW_Inicio", "TW_Fin"]:
        if col in df.columns: df[col] = pd.to_datetime(df[col]).dt.date
    return df

def detectar_temporada(fecha):
    # Lógica simplificada de temporadas OK RM
    estancias_ok = [
        (date(2026, 3, 26), date(2026, 4, 13)),
        (date(2026, 12, 21), date(2026, 12, 31))
    ]
    for inicio, fin in estancias_ok:
        if inicio <= fecha <= fin: return "OK RM", 148
    return "REGULAR", 89

# =====================================================
# SIDEBAR COMPACTO
# =====================================================
with st.sidebar:
    c1, c2, c3 = st.columns([1, 3, 1])
    c2.image("HIC.png") # Asegúrate de que el archivo existe
    
    st.divider()
    menu = st.radio("Navegación", ["🔍 Vista rápida", "➕ Gestión", "📈 Upsell", "🏨 WOH"])
    
    st.divider()
    if st.session_state.is_admin:
        st.success("🟢 ADMIN ACTIVADO")
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
# VISTA RÁPIDA & EDICIÓN
# =====================================================
if menu == "🔍 Vista rápida":
    st.title("🔍 Master Record")
    if df.empty:
        st.info("No hay datos.")
    else:
        # Filtros compactos en una sola línea
        f1, f2, f3 = st.columns(3)
        h_filter = f1.multiselect("Hotel", df["Hotel"].unique())
        m_filter = f2.multiselect("Mercado", df["Market"].unique())
        t_filter = f3.text_input("Buscar texto...")

        filtered_df = df.copy()
        if h_filter: filtered_df = filtered_df[filtered_df["Hotel"].isin(h_filter)]
        if m_filter: filtered_df = filtered_df[filtered_df["Market"].isin(m_filter)]
        if t_filter: filtered_df = filtered_df[filtered_df.astype(str).apply(lambda x: t_filter.lower() in x.str.lower().any(), axis=1)]

        st.dataframe(filtered_df, use_container_width=True, hide_index=True)

        if st.session_state.is_admin:
            with st.expander("📝 Editar Promoción Existente"):
                target = st.selectbox("Elegir promo para extender", filtered_df["Promo"].unique())
                col_e1, col_e2 = st.columns(2)
                new_bw = col_e1.date_input("Nuevo BW Fin")
                new_tw = col_ed2 = col_e2.date_input("Nuevo TW Fin")
                if st.button("Actualizar Promo"):
                    df.loc[df["Promo"] == target, ["BW_Fin", "TW_Fin"]] = [new_bw, new_tw]
                    guardar_con_backup(df)
                    st.success("Actualizado")
                    st.rerun()

# =====================================================
# GESTIÓN (COMPACTO)
# =====================================================
elif menu == "➕ Gestión":
    st.title("➕ Registro de Promoción")
    if not st.session_state.is_admin:
        st.warning("Solo lectura. Accede como Admin para registrar.")
    else:
        with st.container(border=True):
            c_p1, c_p2 = st.columns([2, 1])
            nombre = c_p1.text_input("Nombre de la Promoción")
            hoteles = c_p2.multiselect("Hoteles", ["DREPM", "SECPM"])
            
            c_p3, c_p4, c_p5 = st.columns(3)
            mercado = c_p3.selectbox("Mercado", ["USA", "CAN", "MEX", "LATAM", "EUR", "Worldwide"])
            rate_code = c_p4.text_input("Rate Code")
            dscto = c_p5.number_input("Descuento %", 0, 100)
            
            c_d1, c_d2, c_d3, c_d4 = st.columns(4)
            bw_i = c_d1.date_input("BW Inicio")
            bw_f = c_d2.date_input("BW Fin")
            tw_i = c_d3.date_input("TW Inicio")
            tw_f = c_d4.date_input("TW Fin")
            
            if st.button("🚀 Guardar Promoción en Master Record", use_container_width=True):
                if nombre and hoteles:
                    nuevas = pd.DataFrame([{"Hotel": h, "Promo": nombre, "Market": mercado, "Rate_Plan": rate_code, "Descuento": dscto, "BW_Inicio": bw_i, "BW_Fin": bw_f, "TW_Inicio": tw_i, "TW_Fin": tw_f} for h in hoteles])
                    df = pd.concat([df, nuevas], ignore_index=True)
                    guardar_con_backup(df)
                    st.success("Guardado exitoso")
                    st.rerun()

# =====================================================
# UPSELL (REDISEÑO PRO)
# =====================================================
elif menu == "📈 Upsell":
    st.title("📈 Calculadora de Upsell")
    UPSELL_DATA = {"JS Garden View": 0, "JS Pool View": 45, "JS Ocean View": 90, "JS Swim Out": 150}
    
    with st.container(border=True):
        col_u1, col_u2 = st.columns([1, 1])
        
        with col_u1:
            st.markdown("### 🛠 Configuración")
            hotel = st.selectbox("Propiedad", ["DREPM", "SECPM"])
            fecha = st.date_input("Fecha Estancia")
            
            # Línea de categorías pro
            st.markdown("**Categorías**")
            cl1, cl2, cl3 = st.columns([4, 1, 4])
            orig = cl1.selectbox("De:", list(UPSELL_DATA.keys()), label_visibility="collapsed")
            cl2.markdown("<h3 style='text-align:center;'>➡️</h3>", unsafe_allow_html=True)
            dest = cl3.selectbox("A:", [k for k in UPSELL_DATA.keys() if UPSELL_DATA[k] > UPSELL_DATA[orig]], label_visibility="collapsed")
            
            c_o1, c_o2, c_o3 = st.columns(3)
            ads = c_o1.number_input("Adultos", 1, 4, 2)
            nns = c_o2.number_input("Niños", 0, 4, 0) if hotel == "DREPM" else 0
            noches = c_o3.number_input("Noches", 1, 30, 1)
            tarifa = st.number_input("Tarifa Original (USD Total)", min_value=1.0)

        with col_u2:
            st.markdown("### 💰 Resultado")
            temp, p_nino = detectar_temporada(fecha)
            dif = (UPSELL_DATA[dest] - UPSELL_DATA[orig]) * (1.25 if temp == "OK RM" else 1)
            total_up = dif * noches
            
            st.markdown(f"""
            <div style="background-color:#f0f2f6; padding:20px; border-radius:10px; border-left: 5px solid #00338d;">
                <h4 style="margin:0;">Temporada: {temp}</h4>
                <hr>
                <h2 style="color:#00338d; margin:0;">${total_up:,.2f} USD</h2>
                <p style="font-size:18px;">≈ {total_up * TC_VAL:,.2f} MXN</p>
                <small>Total Estancia: ${(tarifa + total_up):,.2f} USD</small>
            </div>
            """, unsafe_allow_html=True)
            
            if hotel == "DREPM":
                st.info(f"👶 Costo Menor: ${p_nino} USD (≈ {p_nino*TC_VAL:,.0f} MXN)")

# =====================================================
# WOH
# =====================================================
elif menu == "🏨 WOH":
    st.title("🏨 World of Hyatt")
    st.markdown("[🌐 Ir al sitio oficial](https://world.hyatt.com)")
    t1, t2 = st.tabs(["📊 Status", "🧮 Calculadora"])
    with t1:
        st.table({"Nivel": ["Member", "Discoverist", "Explorist", "Globalist"], "Noches": [0, 10, 30, 60], "Bono": ["0%", "10%", "20%", "30%"]})
    with t2:
        monto = st.number_input("Gasto USD", 0)
        st.metric("Puntos Base Estimados", f"{monto * 5:,} pts")
