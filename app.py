import streamlit as st
import pandas as pd
import os
import shutil
from datetime import datetime, date
from io import BytesIO

# =====================================================
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS HIC
# =====================================================
st.set_page_config(page_title="HIC Master Record", layout="wide", page_icon="🏨")

# Inyección de CSS para el Logo y Estética (Imagen 6)
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #00338d; color: white; }
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e0e0e0; }
    </style>
    """, unsafe_allow_html=True)

# Parámetros del Entorno
ADMIN_PASSWORD = st.secrets.get("admin_password", "admin")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROMOS_FILE = os.path.join(BASE_DIR, "promociones_produccion.csv")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
TC_VAL = 18.50  # Tipo de Cambio 2026

if not os.path.exists(BACKUP_DIR): os.makedirs(BACKUP_DIR)

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# =====================================================
# 2. MOTOR DE DATOS Y RESPALDOS (REVENUE OPS)
# =====================================================
def guardar_datos_y_respaldar(df, comentario="Actualización"):
    """Guarda el CSV principal y genera un backup con timestamp"""
    df.to_csv(PROMOS_FILE, index=False)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    df.to_csv(os.path.join(BACKUP_DIR, f"backup_{ts}.csv"), index=False)
    # Log de cambios para auditoría
    with open(os.path.join(BACKUP_DIR, "audit_log.txt"), "a") as f:
        f.write(f"{datetime.now()}: {comentario} - Filas: {len(df)}\n")

def cargar_datos():
    """Carga datos y asegura formato de fecha para evitar SyntaxErrors"""
    if not os.path.exists(PROMOS_FILE):
        return pd.DataFrame(columns=[
            "Hotel", "Promo", "Market", "Rate_Plan", "Descuento", 
            "BW_Inicio", "BW_Fin", "TW_Inicio", "TW_Fin", "Notas"
        ])
    df = pd.read_csv(PROMOS_FILE)
    for col in ["BW_Inicio", "BW_Fin", "TW_Inicio", "TW_Fin"]:
        if col in df.columns: 
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.date
    return df

def detectar_temporada_rm(fecha):
    """Lógica de Revenue para temporadas pico 2026"""
    semanas_pico = [
        (date(2026, 3, 26), date(2026, 4, 13)), # Semana Santa
        (date(2026, 12, 20), date(2026, 12, 31)) # Navidad
    ]
    for inicio, fin in semanas_pico:
        if inicio <= fecha <= fin: return "PREMIUM", 148
    return "REGULAR", 89

def generar_excel(df):
    """Crea el binario de Excel para descarga (Imagen 5)"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Master HIC')
    return output.getvalue()

# =====================================================
# 3. SIDEBAR Y LOGO (ELIMINADO ZVRIM)
# =====================================================
with st.sidebar:
    # Logo oficial centrado
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Hyatt_logo.svg/512px-Hyatt_logo.svg.png", width=180)
    st.markdown("<h2 style='text-align: center; color: #00338d;'>Master Record</h2>", unsafe_allow_html=True)
    st.divider()
    
    menu = st.radio("Navegación", 
                    ["🔍 Vista rápida y Filtros", "➕ Registro y Modificación", "📈 Upsell FD", "🏨 World of Hyatt"])
    st.divider()
    
    if st.session_state.is_admin:
        st.success("🔓 MODO ADMINISTRADOR")
        if st.button("Cerrar Sesión"):
            st.session_state.is_admin = False
            st.rerun()
    else:
        with st.expander("🔐 Acceso Distribución"):
            pwd = st.text_input("Password", type="password")
            if st.button("Login") and pwd == ADMIN_PASSWORD:
                st.session_state.is_admin = True
                st.rerun()

df = cargar_datos()

# =====================================================
# MÓDULO 1: VISTA RÁPIDA (FILTROS Y FIX TYPEERROR)
# =====================================================
if menu == "🔍 Vista rápida y Filtros":
    st.title("🔎 Consulta Integral de Promociones")
    if df.empty:
        st.info("No hay datos en el Master Record.")
    else:
        # Layout de Filtros (Imagen 5)
        f1, f2, f3 = st.columns([1, 1, 2])
        h_sel = f1.multiselect("Hoteles", ["DREPM", "SECPM"])
        m_sel = f2.multiselect("Mercados", df["Market"].unique() if "Market" in df.columns else [])
        t_busq = f3.text_input("Buscador Global (Promo/Code)").strip()

        df_f = df.copy()
        if h_sel: df_f = df_f[df_f["Hotel"].isin(h_sel)]
        if m_sel: df_f = df_f[df_f["Market"].isin(m_sel)]
        
        # --- FIX ROBUSTO AL TYPEERROR DE LA IMAGEN 5 ---
        if t_busq:
            mask = df_f.astype(str).apply(lambda row: row.str.contains(t_busq, case=False, na=False).any(), axis=1)
            df_f = df_f[mask]

        st.dataframe(df_f, use_container_width=True, hide_index=True)

        # Botón de Descarga Excel (Imagen 5)
        if st.session_state.is_admin and not df_f.empty:
            st.download_button(
                label="📥 Exportar Selección a Excel",
                data=generar_excel(df_f),
                file_name=f"HIC_Master_{date.today()}.xlsx",
                mime="application/vnd.ms-excel"
            )

# =====================================================
# MÓDULO 2: REGISTRO Y MODIFICACIÓN (IMAGEN 4 & 7)
# =====================================================
elif menu == "➕ Registro y Modificación":
    st.title("🛠️ Centro de Control de Inventario")
    if not st.session_state.is_admin:
        st.error("Requiere privilegios de Administrador.")
    else:
        t1, t2 = st.tabs(["🚀 Nueva Campaña", "📝 Extender/Modificar Fechas"])
        
        with t1:
            with st.form("new_promo", clear_on_submit=True):
                st.subheader("Datos de la Promoción")
                c1, c2 = st.columns(2)
                p_nom = c1.text_input("Nombre de la Promo (ej: Kids Stay Free)")
                p_htl = c2.multiselect("Hoteles", ["DREPM", "SECPM"])
                
                c3, c4, c5 = st.columns(3)
                p_mkt = c3.selectbox("Mercado", ["USA", "CAN", "MEX", "LATAM", "EUR", "Worldwide"])
                p_cod = c4.text_input("Rate Plan Code")
                p_des = c5.number_input("Descuento %", 0, 100, 0)
                
                st.divider()
                st.write("Vigencias (BW) y Viaje (TW)")
                d1, d2, d3, d4 = st.columns(4)
                bw_i, bw_f = d1.date_input("BW Ini"), d2.date_input("BW Fin")
                tw_i, tw_f = d3.date_input("TW Ini"), d4.date_input("TW Fin")
                
                p_not = st.text_area("Notas de Combinabilidad / Restricciones")
                
                if st.form_submit_button("✅ Registrar en Base de Datos"):
                    if p_nom and p_htl:
                        nuevos = pd.DataFrame([{
                            "Hotel": h, "Promo": p_nom, "Market": p_mkt, "Rate_Plan": p_cod,
                            "Descuento": p_des, "BW_Inicio": bw_i, "BW_Fin": bw_f,
                            "TW_Inicio": tw_i, "TW_Fin": tw_f, "Notas": p_not
                        } for h in p_htl])
                        df = pd.concat([df, nuevos], ignore_index=True)
                        guardar_datos_y_respaldar(df, f"Alta: {p_nom}")
                        st.success("Registro completado y backup generado.")
                        st.rerun()

        with t2:
            st.subheader("Modificación de Vigencias (Imagen 4)")
            if not df.empty:
                promo_mod = st.selectbox("Buscar Promo a Modificar", df["Promo"].unique())
                idx = df[df["Promo"] == promo_mod].index[0]
                
                with st.form("mod_form"):
                    st.info(f"Modificando: {df.at[idx, 'Hotel']} - {promo_mod}")
                    m1, m2 = st.columns(2)
                    new_bw_f = m1.date_input("Nueva fecha BW Fin", df.at[idx, 'BW_Fin'])
                    new_tw_f = m2.date_input("Nueva fecha TW Fin", df.at[idx, 'TW_Fin'])
                    new_notes = st.text_area("Actualizar Notas", df.at[idx, 'Notas'])
                    
                    if st.form_submit_button("💾 Guardar Cambios"):
                        # Actualizar todos los registros con ese nombre de promo
                        df.loc[df["Promo"] == promo_mod, "BW_Fin"] = new_bw_f
                        df.loc[df["Promo"] == promo_mod, "TW_Fin"] = new_tw_f
                        df.loc[df["Promo"] == promo_mod, "Notas"] = new_notes
                        guardar_datos_y_respaldar(df, f"Mod: {promo_mod}")
                        st.success("Cambios aplicados.")
                        st.rerun()

# =====================================================
# MÓDULO 3: UPSELL FD (DISEÑO IMAGEN 3 - SIN PUNTOS)
# =====================================================
elif menu == "📈 Upsell FD":
    st.title("📈 Calculadora de Upsell Front Desk")
    # Tarifas HIC
    CATS = {"JS Garden View": 0, "JS Pool View": 45, "JS Ocean View": 90, "JS Swim Out": 150}
    
    with st.container(border=True):
        # Renglón 1: Logística (Imagen 3)
        r1 = st.columns([1, 1, 1.5, 1])
        hotel = r1[0].selectbox("Hotel", ["DREPM", "SECPM"])
        f_arr = r1[1].date_input("Llegada", date.today())
        p_ori = r1[2].number_input("Tarifa Original USD (Total)", value=500.0)
        nts = r1[3].number_input("Noches", 1, 30, 1)
        
        st.divider()
        
        # Renglón 2: Categorías y Pax (Imagen 3)
        r2 = st.columns([2, 2, 0.8, 0.8, 1])
        c_de = r2[0].selectbox("De:", list(CATS.keys()))
        c_a = r2[1].selectbox("A:", [k for k in CATS.keys() if CATS[k] > CATS[c_de]])
        adt = r2[2].number_input("Adt", 1, 4, 2)
        chd = r2[3].number_input("Chd", 0, 4, 0)
        btn_calc = r2[4].button("🚀 Calcular")

    if btn_calc:
        temp, p_chd = detectar_temporada_rm(f_arr)
        # Lógica de cálculo 2026
        diff_noche = CATS[c_a] - CATS[c_de]
        total_u = diff_noche * nts
        
        # Resultados (Imagen 1)
        res1, res2 = st.columns([1, 1.5])
        with res1:
            st.markdown(f"""
                <div style='background-color:#e1f5fe; padding:20px; border-radius:10px; border-left:5px solid #01579b;'>
                    <p style='margin:0; color:#01579b;'><b>Total Upgrade</b></p>
                    <h2 style='margin:0;'>${total_u:,.2f} USD</h2>
                    <p style='color:gray;'>≈ {(total_u * TC_VAL):,.2f} MXN</p>
                </div>
            """, unsafe_allow_html=True)
        
        with res2:
            st.info(f"👶 Niño (3-12): ${p_chd} USD | Temporada: {temp}")
            if chd > 0 and "Swim Out" in c_a:
                st.error("⚠️ POLÍTICA: No se permiten menores en Swim Out.")

# =====================================================
# MÓDULO 4: WORLD OF HYATT (IMAGEN 6) – VERSIÓN MEJORADA
# =====================================================
elif menu == "🏨 World of Hyatt":
    st.title("🏨 World of Hyatt – Programa de Lealtad")
    st.caption("Visión operativa y estratégica de estatus, beneficios y generación de puntos")

    ta, tb = st.tabs(["🏆 Estatus, Beneficios y Milestones", "🔢 Simulador de Puntos"])

    # -------------------------------------------------
    # TAB 1: ESTATUS Y BENEFICIOS
    # -------------------------------------------------
    with ta:
        st.subheader("Estatus World of Hyatt – Beneficios Operativos 2026")

        st.markdown("""
        ### 🎯 ¿Cómo se interpreta este cuadro?
        - Los **estatus** determinan prioridad operativa y beneficios al huésped.
        - A mayor estatus, mayor **impacto en satisfacción, fidelidad y valor del cliente**.
        """)

        st.table({
            "Estatus": ["Member", "Discoverist", "Explorist", "Globalist"],
            "Noches calificadas": [0, 10, 30, 60],
            "Bono sobre puntos base": ["—", "10%", "20%", "30%"],
            "Late Check-Out": [
                "Sujeto a disponibilidad",
                "Hasta 2:00 PM",
                "Hasta 2:00 PM",
                "Garantizado hasta 4:00 PM"
            ],
            "Impacto Operativo": [
                "Básico",
                "Preferencia moderada",
                "Alta prioridad",
                "Prioridad premium"
            ]
        })

        st.divider()

        # ---------------- Milestones ----------------
        st.markdown("### 🌟 Premios por Milestone (No ligados a estatus)")

        c1, c2, c3 = st.columns(3)

        with c1:
            st.info("🏅 **40 Noches**\n\nGuest of Honor\n\nPermite compartir beneficios Globalist con otro huésped.")

        with c2:
            st.warning("⭐ **Milestones Intermedios**\n\nBonos y premios incrementales acumulables.")

        with c3:
            st.success("🚀 **60+ Noches**\n\nMáximo aprovechamiento del programa y mayor rentabilidad del cliente.")

        st.caption(
            "💡 *Nota operativa:* Guest of Honor no es un estatus, es un premio Milestone y debe tratarse como beneficio compartido."
        )

    # -------------------------------------------------
    # TAB 2: SIMULADOR DE PUNTOS
    # -------------------------------------------------
    with tb:
        st.subheader("Simulador de Generación de Puntos Base")

        st.markdown("""
        Este simulador permite visualizar **el impacto real del estatus** en la acumulación de puntos,
        útil para entender incentivos, upselling y valor del huésped frecuente.
        """)

        c1, c2 = st.columns(2)

        with c1:
            t_w = st.number_input("Tarifa elegible por noche (USD)", value=300, step=50)
        with c2:
            n_w = st.number_input("Total de noches", value=4, step=1)

        st.divider()

        p_base = (t_w * n_w) * 5

        m1, m2, m3, m4 = st.columns(4)

        m1.metric("Member", f"{int(p_base):,}", help="Sin bono adicional")
        m2.metric("Discoverist", f"{int(p_base * 1.10):,}", help="+10% sobre puntos base")
        m3.metric("Explorist", f"{int(p_base * 1.20):,}", help="+20% sobre puntos base")
        m4.metric("Globalist", f"{int(p_base * 1.30):,}", help="+30% sobre puntos base")

        st.caption("📊 Los puntos base se calculan a razón de **5 puntos por USD elegible**.")

