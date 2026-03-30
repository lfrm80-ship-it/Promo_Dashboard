import streamlit as st
import pandas as pd
import os
import io
from datetime import datetime, date

# =====================================================
# CONFIGURACIÓN GENERAL
# =====================================================
st.set_page_config(
    page_title="Master Record Playa Mujeres",
    layout="wide"
)

ADMIN_PASSWORD = st.secrets.get("admin_password", "admin")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROMOS_FILE = os.path.join(BASE_DIR, "promociones_produccion.csv")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")

# Crear carpetas necesarias si no existen
if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)
if not os.path.exists(os.path.join(BASE_DIR, "media")):
    os.makedirs(os.path.join(BASE_DIR, "media"))

# =====================================================
# SESSION STATE
# =====================================================
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# =====================================================
# CONSTANTES
# =====================================================
PROPERTIES = [
    "DREPM - Dreams Playa Mujeres",
    "SECPM - Secrets Playa Mujeres"
]

MARKETS = ["USA", "CAN", "MEX", "LATAM", "EUR", "Worldwide"]

# =====================================================
# FUNCIONES DE SEGURIDAD Y DATOS
# =====================================================
def crear_backup(df):
    """Genera una copia de seguridad física con timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(BACKUP_DIR, f"backup_promos_{timestamp}.csv")
    df.to_csv(filename, index=False)
    return filename

def cargar_promos():
    if not os.path.exists(PROMOS_FILE):
        return pd.DataFrame()
    df = pd.read_csv(PROMOS_FILE)
    for col in ["BW_Inicio", "BW_Fin", "TW_Inicio", "TW_Fin"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
    return df

def guardar_promos(df):
    if df is None or len(df) == 0:
        st.error("⛔ Seguridad: intento de guardar archivo vacío BLOQUEADO")
        st.stop()
    # Guardar maestro
    df.to_csv(PROMOS_FILE, index=False)
    # Crear respaldo automático
    crear_backup(df)

def generar_excel(df):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False)
    return buffer.getvalue()

def calcular_estado(row):
    hoy = date.today()
    if pd.isna(row["TW_Inicio"]) or pd.isna(row["TW_Fin"]):
        return "Expirada"
    if row["TW_Inicio"] <= hoy <= row["TW_Fin"]:
        return "Activa"
    if hoy < row["TW_Inicio"]:
        return "Futura"
    return "Expirada"

# =====================================================
# REGLAS OK RM (SOLO UPSELL)
# =====================================================
OK_RM_RULES = {
    2026: {
        "ok_rm": [("2026-03-26", "2026-04-13"), ("2026-12-21", "2026-12-31")],
        "regular": {"net": 67, "pub": 89},
        "ok": {"net": 111, "pub": 148}
    },
    2027: {
        "ok_rm": [("2027-03-20", "2027-04-11"), ("2027-12-21", "2028-01-04")],
        "regular": {"net": 71, "pub": 95},
        "ok": {"net": 118, "pub": 157}
    }
}

TC_VAL = 18.50

def detectar_ok_rm(fecha_llegada):
    reglas = OK_RM_RULES.get(fecha_llegada.year)
    if not reglas: return "REGULAR", {"net": 0, "pub": 0}
    for i, f in reglas["ok_rm"]:
        if datetime.strptime(i, "%Y-%m-%d").date() <= fecha_llegada <= datetime.strptime(f, "%Y-%m-%d").date():
            return "OK RM", reglas["ok"]
    return "REGULAR", reglas["regular"]

# =====================================================
# SIDEBAR
# =====================================================
with st.sidebar:
    c1, c2, c3 = st.columns([1, 2, 1]) 
    with c2:
        st.image("HIC.png") 
    st.write("") 
    
    menu = st.radio(
        "Navegación",
        ["🔍 Vista rápida", "➕ Nueva promoción", "📈 Upsell", "🏨 WOH"] 
        if st.session_state.is_admin else
        ["🔍 Vista rápida", "📈 Upsell", "🏨 WOH"]
    )

    st.divider()
    if st.session_state.is_admin:
        st.success("🟢 Modo ADMIN")
        if st.button("Salir de Admin", use_container_width=True):
            st.session_state.is_admin = False
            st.rerun()
    else:
        with st.expander("🔒 Admin Login"):
            pwd = st.text_input("Contraseña", type="password")
            if st.button("Entrar", use_container_width=True) and pwd == ADMIN_PASSWORD:
                st.session_state.is_admin = True
                st.rerun()

# Carga de datos
df = cargar_promos()

# =====================================================
# VISTA RÁPIDA (ACTUALIZADA CON EDICIÓN PARA ADMIN)
# =====================================================
if menu == "🔍 Vista rápida":
    if df.empty:
        st.info("No hay promociones registradas.")
    else:
        df_view = df.copy()
        df_view["Estado"] = df_view.apply(calcular_estado, axis=1)

        st.subheader("🔎 Filtros y Gestión")
        c1, c2, c3, c4 = st.columns(4)
        f_hotel = c1.multiselect("Hotel", df_view["Hotel"].dropna().unique())
        f_estado = c2.multiselect("Estado", ["Activa", "Futura", "Expirada"])
        f_market = c3.multiselect("Market", df_view["Market"].dropna().unique())
        f_texto = c4.text_input("Buscar promoción específica")

        # Aplicar Filtros
        if f_hotel: df_view = df_view[df_view["Hotel"].isin(f_hotel)]
        if f_estado: df_view = df_view[df_view["Estado"].isin(f_estado)]
        if f_market: df_view = df_view[df_view["Market"].isin(f_market)]
        if f_texto:
            txt = f_texto.lower()
            df_view = df_view[df_view.apply(lambda r: txt in str(r["Promo"]).lower(), axis=1)]

        # --- SECCIÓN DE EDICIÓN (SOLO ADMIN) ---
        if st.session_state.is_admin and not df_view.empty:
            with st.expander("📝 Panel de Edición Rápida (Solo Admin)", expanded=False):
                st.warning("Selecciona una promoción para modificar sus fechas o detalles.")
                
                # Elegir cuál editar de los resultados filtrados
                promo_to_edit = st.selectbox(
                    "Selecciona la promoción a editar:", 
                    df_view["Promo"].unique(),
                    key="selector_edit"
                )
                
                # Extraer datos actuales
                idx = df[df["Promo"] == promo_to_edit].index[0]
                row = df.iloc[idx]

                with st.form("edit_form"):
                    col_ed1, col_ed2 = st.columns(2)
                    new_bw_f = col_ed1.date_input("Nueva fecha fin BW", value=row["BW_Fin"])
                    new_tw_f = col_ed2.date_input("Nueva fecha fin TW", value=row["TW_Fin"])
                    
                    new_notes = st.text_area("Actualizar Notas", value=row["Notas"])
                    
                    if st.form_submit_button("Actualizar y Crear Backup"):
                        # Actualizar el DataFrame original
                        df.at[idx, "BW_Fin"] = new_bw_f
                        df.at[idx, "TW_Fin"] = new_tw_f
                        df.at[idx, "Notas"] = new_notes
                        
                        # Guardar (esto dispara el backup automático que ya configuramos)
                        guardar_promos(df)
                        st.success(f"✅ '{promo_to_edit}' actualizada correctamente.")
                        st.rerun()

        st.divider()
        st.dataframe(df_view, use_container_width=True, hide_index=True)
        
        st.download_button(
            "📥 Descargar Excel del Master Record",
            generar_excel(df_view),
            f"MasterRecord_{date.today()}.xlsx"
        )
# =====================================================
# NUEVA PROMOCIÓN (ESCRIBE DATOS + BACKUP)
# =====================================================
elif menu == "➕ Nueva promoción":
    if not st.session_state.is_admin:
        st.warning("⚠️ Acceso restringido a administradores.")
    else:
        with st.form("new_promo"):
            st.subheader("➕ Registro de Promoción")
            promo = st.text_input("Nombre de la Promoción")
            hotels = st.multiselect("Hoteles aplicables", PROPERTIES)
            market = st.selectbox("Mercado", MARKETS)
            rate = st.text_input("Rate Plan Code")
            discount = st.number_input("Descuento %", 0, 100)
            c1, c2, c3, c4 = st.columns(4)
            bw_i = c1.date_input("BW Inicio")
            bw_f = c2.date_input("BW Fin")
            tw_i = c3.date_input("TW Inicio")
            tw_f = c4.date_input("TW Fin")
            
            st.subheader("📎 Carga Masiva (Opcional)")
            excel_file = st.file_uploader("Subir Excel Master", type=["xlsx"])
            submit = st.form_submit_button("Guardar todo y crear Backup")

            if submit:
                df_actual = cargar_promos()
                if excel_file:
                    df_excel = pd.read_excel(excel_file)
                    df_actual = pd.concat([df_actual, df_excel], ignore_index=True)
                elif promo and hotels:
                    new_rows = []
                    for h in hotels:
                        new_rows.append({
                            "Hotel": h, "Promo": promo, "Market": market, "Rate_Plan": rate,
                            "Descuento": discount, "BW_Inicio": bw_i, "BW_Fin": bw_f,
                            "TW_Inicio": tw_i, "TW_Fin": tw_f
                        })
                    df_actual = pd.concat([df_actual, pd.DataFrame(new_rows)], ignore_index=True)
                
                guardar_promos(df_actual)
                st.success("✅ Datos guardados y Backup generado con éxito.")
                st.rerun()

# =====================================================
# MÓDULO: UPSELL (VERSIÓN CON EDADES RESTAURADAS)
# =====================================================
elif menu == "📈 Upsell":
    st.subheader("📈 Calculadora de Upsell Profesional")
    
    UPSELL_VALUES = {
        "JS Garden View": 0, 
        "JS Pool View": 45, 
        "JS Ocean View": 90, 
        "JS Swim Out": 150
    }
    HABITACIONES = list(UPSELL_VALUES.keys())
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📋 Datos de la Reserva")
        
        # Fila 1: Hotel y Fecha
        c_hotel, c_fecha = st.columns(2)
        hotel_sel = c_hotel.selectbox("Hotel", ["DREPM", "SECPM"])
        fecha_sel = c_fecha.date_input("Fecha de llegada", value=date.today())
        
        # Fila 2: Categorías en una sola línea
        st.write("**Selección de Categorías**")
        c_orig, c_flecha, c_dest = st.columns([4, 1, 4])
        
        hab_actual = c_orig.selectbox("Original", HABITACIONES, label_visibility="collapsed", key="hab_orig")
        c_flecha.markdown("<h3 style='text-align: center; margin-top: 0;'>➡️</h3>", unsafe_allow_html=True)
        
        idx_act = HABITACIONES.index(hab_actual)
        posibles = HABITACIONES[idx_act + 1:]
        hab_destino = c_dest.selectbox("Upgrade", posibles if posibles else ["Máxima"], label_visibility="collapsed", key="hab_dest")
        
        # Fila 3: Ocupación
        c_a, c_n = st.columns(2)
        adultos = c_a.number_input("Adultos", 1, 4, 2)
        
        # Lógica de Niños (Solo Dreams)
        if hotel_sel == "DREPM":
            ninos = c_n.number_input("Niños (0-12)", 0, 4, 0)
        else:
            ninos = 0
            c_n.write("") # Espaciador
            c_n.caption("Solo adultos (18+)")

        # Fila 4: Tarifa y Noches
        c_tar, c_noc = st.columns(2)
        tarifa_orig = c_tar.number_input("Tarifa Original (USD)", min_value=1, value=500)
        noches = c_noc.number_input("Noches", 1, 30, 1)
        
        btn_calc = st.button("🚀 Calcular Upgrade", use_container_width=True)

    with col2:
        if btn_calc:
            # 1. Validaciones Críticas de Front Desk
            if ninos > 0 and "Swim Out" in hab_destino:
                st.error("❌ **RESTRICCIÓN OPERATIVA:** No se permiten menores en categorías **Swim Out**.")
            elif hab_destino == "Máxima":
                st.warning("La reserva ya está en la categoría más alta.")
            else:
                # 2. Cálculos de Temporada y Upgrade
                temp, precios = detectar_ok_rm(fecha_sel)
                dif_noche = (UPSELL_VALUES[hab_destino] - UPSELL_VALUES[hab_actual])
                
                if temp == "OK RM": 
                    dif_noche *= 1.25
                
                up_usd = dif_noche * noches
                tot_usd = tarifa_orig + up_usd
                
                # 3. Visualización de Resultados
                color_bg = "#d4edda" if temp == "REGULAR" else "#fff3cd"
                st.markdown(f"<div style='background-color:{color_bg}; padding:10px; border-radius:10px; text-align:center; border: 1px solid #ddd;'><h4 style='margin:0; color:#333;'>📅 Temporada: {temp} (TC: {TC_VAL})</h4></div>", unsafe_allow_html=True)
                
                st.write("")
                m1, m2 = st.columns(2)
                m1.metric("Costo Upgrade", f"${up_usd:,.2f} USD", f"≈ {up_usd*TC_VAL:,.2f} MXN")
                m2.metric("Total Estancia", f"${tot_usd:,.2f} USD", f"≈ {tot_usd*TC_VAL:,.2f} MXN")

                # 4. POLÍTICA DE EDADES (RESTAURADA)
                if hotel_sel == "DREPM":
                    st.divider()
                    st.markdown("#### 👶 Política y Costos de Menores")
                    e1, e2, e3 = st.columns(3)
                    
                    pub_val = precios.get('pub', 0)
                    
                    with e1: 
                        st.info("**Infantes**\n\n0-2 años: $0")
                    with e2: 
                        st.success(f"**Menores**\n\n3-12 años: ${pub_val} USD\n(≈ {round(pub_val*TC_VAL):,} MXN)")
                    with e3: 
                        st.warning("**Juniors**\n\n13+ años: Adulto")
                
                # 5. Resumen para copiar
                with st.expander("📋 Resumen para el Cliente"):
                    resumen = f"Hotel: {hotel_sel}\nUpgrade: {hab_actual} ➡️ {hab_destino}\nCosto Total: ${up_usd:,.2f} USD (${up_usd*TC_VAL:,.2f} MXN)"
                    st.code(resumen, language="text")
        else:
            st.info("Ingresa los datos de la reserva y presiona 'Calcular'.")
# =====================================================
# WOH
# =====================================================
elif menu == "🏨 WOH":
    st.subheader("🏨 World of Hyatt - Programa de Lealtad")
    st.markdown("""<div style="text-align: right; margin-top: -45px;"><a href="https://world.hyatt.com/content/gp/en/program-overview.html" target="_blank" style="color: #00338d; text-decoration: none; font-weight: bold; border: 1px solid #00338d; padding: 5px 15px; border-radius: 5px;">🌐 Página Oficial WOH</a></div><br>""", unsafe_allow_html=True)

    t1, t2, t3 = st.tabs(["🏅 Status", "🎁 Milestones", "✨ Beneficios"])
    with t1:
        st.table({"Nivel": ["Member", "Discoverist", "Explorist", "Globalist"], "Noches": ["0", "10", "30", "60"], "Bono Pts": ["-", "10%", "20%", "30%"]})
    with t2:
        milestones = {"20 Noches": "2 Club Access Awards O 2,000 Pts", "30 Noches": "1 Free Night (Cat 1-4)", "60 Noches": "2 Guest of Honor + 2 Suite Upgrades"}
        for n, p in milestones.items():
            with st.expander(f"🚩 {n}"): st.write(p)
    with t3:
        st.markdown("**Late Check-out:**\n* Discoverist/Explorist: 2 PM\n* Globalist: 4 PM")
    
    st.divider()
    st.markdown("### 🧮 Calculadora de Puntos")
    m_usd = st.number_input("Gasto USD", 0, 10000, 100)
    status = st.selectbox("Status", ["Member", "Discoverist", "Explorist", "Globalist"])
    bono = {"Member": 1.0, "Discoverist": 1.1, "Explorist": 1.2, "Globalist": 1.3}
    st.metric("Puntos Estimados", f"{int((m_usd * 5) * bono[status])} pts")
