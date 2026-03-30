import streamlit as st
import pandas as pd
import os
import shutil
from datetime import datetime, date
from io import BytesIO

# =====================================================
# 1. CONFIGURACIÓN DE PÁGINA Y RUTAS
# =====================================================
st.set_page_config(page_title="HIC Master Record", layout="wide", page_icon="🏨")

# Secretos y Directorios Operativos
ADMIN_PASSWORD = st.secrets.get("admin_password", "admin")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROMOS_FILE = os.path.join(BASE_DIR, "promociones_produccion.csv")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
MEDIA_DIR = os.path.join(BASE_DIR, "media")
TC_VAL = 18.50  # Tipo de cambio proyectado 2026

# Asegurar persistencia de carpetas
for d in [BACKUP_DIR, MEDIA_DIR]:
    if not os.path.exists(d): os.makedirs(d)

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# =====================================================
# 2. MOTOR DE DATOS Y RESPALDOS (REVENUE MANAGEMENT)
# =====================================================
def guardar_datos_y_respaldar(df, comentario="Actualización manual"):
    df.to_csv(PROMOS_FILE, index=False)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    df.to_csv(os.path.join(BACKUP_DIR, f"backup_{ts}.csv"), index=False)
    with open(os.path.join(BACKUP_DIR, "audit_log.txt"), "a") as f:
        f.write(f"{datetime.now()}: {comentario} - Filas: {len(df)}\n")

def cargar_datos():
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

def detecting_rm_season(fecha):
    premium_seasons = [
        (date(2026, 3, 26), date(2026, 4, 13)), 
        (date(2026, 12, 20), date(2026, 12, 31))
    ]
    for inicio, fin in premium_seasons:
        if inicio <= fecha <= fin: return "PREMIUM", 148
    return "REGULAR", 89

def converting_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Master Record HIC')
        worksheet = writer.sheets['Master Record HIC']
        for i, col in enumerate(df.columns):
            worksheet.set_column(i, i, max(df[col].astype(str).map(len).max(), len(col)) + 2)
    return output.getvalue()

# =====================================================
# 3. SIDEBAR Y CONTROL DE ACCESO (LOGO RESTAURADO)
# =====================================================
with st.sidebar:
    # --- LA IMAGEN QUE HACÍA FALTA ---
    st.image("https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR6A7GfGq-o9f2A-V0uYmCqYFzP6oP2B4S-RA&s", width=200) 
    st.divider()
    # Menú unificado
    menu = st.radio("Módulos HIC Master Record", ["🔍 Vista rápida y Filtros", "➕ Registro y Modificación", "📈 Upsell FD", "🏨 World of Hyatt"])
    st.divider()
    
    if st.session_state.is_admin:
        st.success("🔓 MODO ADMINISTRADOR ACTIVO")
        if st.button("Cerrar Sesión", use_container_width=True):
            st.session_state.is_admin = False
            st.rerun()
    else:
        with st.expander("🔐 Desbloquear Funciones Admin"):
            pwd = st.text_input("Contraseña de Distribución", type="password")
            if st.button("Ingresar", use_container_width=True) and pwd == ADMIN_PASSWORD:
                st.session_state.is_admin = True
                st.rerun()

df = cargar_datos()

# =====================================================
# MÓDULO 1: VISTA RÁPIDA (FILTROS CORREGIDOS Y DESCARGAS)
# =====================================================
if menu == "🔍 Vista rápida y Filtros":
    st.title("🔎 Consulta Integral del Master Record")
    if df.empty:
        st.info("No hay promociones en la base de datos central.")
    else:
        # Panel de Filtros y Buscador
        fil_col1, fil_col2, fil_col3 = st.columns([1.2, 1.2, 2])
        h_fil = fil_col1.multiselect("Hoteles HIC", ["DREPM", "SECPM", "ZOE VR"], placeholder="Elegir propiedades...")
        m_fil = fil_col2.multiselect("Mercado Target", df["Market"].unique() if "Market" in df.columns else [], placeholder="Paises o Zonas...")
        t_global = fil_col3.text_input("Buscador Global (Promo o Rate Code)").strip()

        df_fil = df.copy()
        if h_fil: df_fil = df_fil[df_fil["Hotel"].isin(h_fil)]
        if m_fil: df_fil = df_fil[df_fil["Market"].isin(m_fil)]
        if t_global:
            # Fix robusto para el buscador global que dio error
            try:
                mask = df_fil.astype(str).apply(lambda row: row.str.contains(t_global, case=False, na=False).any(), axis=1)
                df_fil = df_fil[mask]
            except Exception as e:
                st.error(f"Error técnico en el buscador: {e}")
                if "Promo" in df_fil.columns:
                    df_fil = df_fil[df_fil["Promo"].str.contains(t_global, case=False, na=False)]

        # Visualización de la Tabla Maestra
        st.dataframe(df_fil, use_container_width=True, hide_index=True)

        # Módulo de Descarga y Respaldos
        down_col1, down_col2 = st.columns([1.5, 3])
        if st.session_state.is_admin:
            xlsx_data = converting_to_excel(df_fil)
            down_col1.download_button(
                label="📥 Descargar Master Record (Excel)",
                data=xlsx_data,
                file_name=f'HIC_Master_Record_{date.today()}.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                use_container_width=True
            )
            
            with down_col2.expander("🛠️ Gestión de Respaldos de Distribución"):
                respaldos = [f for f in os.listdir(BACKUP_DIR) if f.startswith("backup_") and f.endswith(".csv")]
                if respaldos:
                    respaldos.sort(reverse=True)
                    c_resp = st.selectbox("Elegir respaldo para descargar:", respaldos)
                    down_resp = BytesIO(converting_to_excel(pd.read_csv(os.path.join(BACKUP_DIR, c_resp))))
                    st.download_button(
                        label=f"📥 Descargar {c_resp[:-4]}",
                        data=down_resp,
                        file_name=f'{c_resp[:-4]}.xlsx',
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        use_container_width=True
                    )

# =====================================================
# MÓDULO 2: REGISTRO Y MODIFICACIÓN (SOLO ADMIN)
# =====================================================
elif menu == "➕ Registro y Modificación":
    st.title("🛠️ Gestión de Campañas de Distribución")
    if not st.session_state.is_admin:
        st.error("Permiso denegado. Se requiere acceso de Administrador.")
    else:
        # Pestañas operativas
        tabs_gest = st.tabs(["🚀 Nueva Promo", "📝 Extender/Modificar Existente"])
        
        # PESTAÑA: Nueva Promo (Uploader Incluido)
        with tabs_gest[0]:
            with st.form("new_promo_form", clear_on_submit=True):
                col_n1, col_n2 = st.columns([2, 1])
                name_camp = col_n1.text_input("Nombre de la Campaña")
                prop_af = col_n2.multiselect("Propiedades", ["DREPM", "SECPM", "ZOE VR"])
                
                m1, m2, m3 = st.columns(3)
                mkt_geo = m1.selectbox("Mercado", ["USA", "CAN", "MEX", "LATAM", "EUR", "Worldwide"])
                rate_code = m2.text_input("Rate Plan Code (PKG, PKGUP, etc.)")
                desc_p = m3.number_input("Descuento (%)", 0, 100, 0)
                
                d1, d2, d3, d4 = st.columns(4)
                bw_ini, bw_fin = d1.date_input("BW Ini"), d2.date_input("BW Fin")
                tw_ini, tw_fin = d3.date_input("TW Ini"), d4.date_input("TW Fin")
                
                st.divider()
                upload_p = st.file_uploader("Subir evidencia PDF/Excel", type=["pdf", "xlsx", "jpg", "png"])
                combin_notes = st.text_area("Notas / Restricciones / Combinabilidad con Resident")
                
                if st.form_submit_button("🚀 Registrar en Master Record y Backup"):
                    if name_camp and prop_af:
                        nuevos_datos = pd.DataFrame([{
                            "Hotel": h, "Promo": name_camp, "Market": mkt_geo, 
                            "Rate_Plan": rate_code, "Descuento": desc_p, 
                            "BW_Inicio": bw_ini, "BW_Fin": bw_fin, 
                            "TW_Inicio": tw_ini, "TW_Fin": tw_fin, "Notas": combin_notes
                        } for h in prop_af])
                        
                        df = pd.concat([df, nuevos_datos], ignore_index=True)
                        guardar_datos_y_respaldar(df, f"Nueva Promo: {name_camp}")
                        st.success(f"✅ Se registraron {len(prop_af)} entradas para la promo {name_camp}.")
                        st.rerun()

        # PESTAÑA: Modificar Existente (Extender Fechas)
        with tabs_gest[1]:
            st.subheader("Buscador de Promoción para Extender/Modificar")
            if not df.empty:
                s_col1, s_col2 = st.columns(2)
                h_sel = s_col1.multiselect("Hotel", df["Hotel"].unique(), placeholder="Elegir hotel...")
                r_sel = s_col2.text_input("Palabra clave (Promo o Rate Code)").strip()
                
                df_s = df.copy()
                if h_sel: df_s = df_s[df_s["Hotel"].isin(h_sel)]
                if r_sel:
                    try:
                        mask = df_s.astype(str).apply(lambda row: row.str.contains(r_sel, case=False, na=False).any(), axis=1)
                        df_s = df_s[mask]
                    except:
                        pass
                
                if not df_s.empty:
                    rows_for_mod = df_s.Promo.unique()
                    mod_promo = st.selectbox("Elegir Promo Específica a Modificar:", rows_for_mod)
                    idx_mod = df[df["Promo"] == mod_promo].index[0]
                    
                    with st.form("mod_form", clear_on_submit=True):
                        st.write(f"Modificando registro para: **{df.at[idx_mod, 'Hotel']} - {mod_promo}**")
                        mod_rate = st.text_input("Modificar Rate Code:", value=df.at[idx_mod, 'Rate_Plan'])
                        st.divider()
                        mod_col1, mod_col2 = st.columns(2)
                        mod_bw_fin = mod_col1.date_input("Extender BW Fin hasta:", value=df.at[idx_mod, 'BW_Fin'])
                        mod_tw_fin = mod_col2.date_input("Extender travel TW Fin hasta:", value=df.at[idx_mod, 'TW_Fin'])
                        mod_notes = st.text_area("Modificar Notas:", value=df.at[idx_mod, 'Notas'])
                        
                        if st.form_submit_button("📝 Actualizar Registro y Respaldar"):
                            df.at[idx_mod, 'Rate_Plan'] = mod_rate
                            df.at[idx_mod, 'BW_Fin'] = mod_bw_fin
                            df.at[idx_mod, 'TW_Fin'] = mod_tw_fin
                            df.at[idx_mod, 'Notas'] = mod_notes
                            
                            guardar_datos_y_respaldar(df, f"Extensión/Modificación: {mod_promo}")
                            st.success(f"✅ Promoción {mod_promo} actualizada con éxito.")
                            st.rerun()
                else:
                    st.warning("No se encontraron promociones con esos filtros de modificación.")

# =====================================================
# MÓDULO 3: UPSELL FD (DISEÑO PRO DE 2 RENGLONES)
# =====================================================
elif menu == "📈 Upsell FD":
    st.title("📈 Calculadora de Upsell Front Desk HIC")
    CAT_VALS = {"JS Garden View": 0, "JS Pool View": 45, "JS Ocean View": 90, "JS Swim Out": 150}
    
    with st.container(border=True):
        # RENGLÓN 1: LOGÍSTICA
        r1 = st.columns([1, 1.2, 1.2, 1])
        hotel = r1[0].selectbox("Propiedad HIC", ["DREPM", "SECPM"], index=0)
        llegada = r1[1].date_input("Fecha de Arribo", date.today())
        p_original = r1[2].number_input("Tarifa Reserva (Total USD)", min_value=1.0, value=500.0)
        noches = r1[3].number_input("Noches", 1, 30, 1)

        st.markdown("<hr style='margin:10px 0; border:0.5px solid #eee;'>", unsafe_allow_html=True)

        # RENGLÓN 2: HABITACIONES Y PAX
        if hotel == "DREPM":
            r2 = st.columns([2, 2, 0.8, 0.8, 1.2]) # Dreams: Incluye Niños
            c_ori = r2[0].selectbox("Habitación Reservada", list(CAT_VALS.keys()))
            c_des = r2[1].selectbox("Upgrade propuesto a", [k for k in CAT_VALS.keys() if CAT_VALS[k] > CAT_VALS[c_ori]])
            adultos = r2[2].number_input("Adt", 1, 4, 2)
            ninos = r2[3].number_input("Chd", 0, 4, 0)
            btn_upsell = r2[4].button("🚀 Calcular", use_container_width=True)
        else:
            r2 = st.columns([2, 2, 0.8, 1.2]) # Secrets: Adults Only
            c_ori = r2[0].selectbox("Habitación Reservada", list(CAT_VALS.keys()))
            c_des = r2[1].selectbox("Upgrade propuesto a", [k for k in CAT_VALS.keys() if CAT_VALS[k] > CAT_VALS[c_ori]])
            adultos = r2[2].number_input("Adt", 1, 4, 2)
            ninos = 0
            btn_upsell = r2[3].button("🚀 Calcular", use_container_width=True)

    if btn_upsell:
        status_rm, p_nino = detecting_rm_season(llegada)
        markup = 1.25 if status_rm == "PREMIUM" else 1.0 # Markup RM por temporada
        
        diff_base = (CAT_VALS[c_des] - CAT_VALS[c_ori]) * markup
        total_upsell = diff_base * noches
        
        c_res1, c_res2 = st.columns([1, 1.5])
        with c_res1:
            st.markdown(f"""
                <div style="background-color:#f0f2f6; padding:20px; border-radius:10px; border: 1px solid #00338d;">
                    <h5 style="color:#00338d; margin:0;">Monto de Upgrade (TC: {TC_VAL})</h5>
                    <h2 style="margin:0;">${total_upsell:,.2f} USD</h2>
                    <p style="color:gray;">≈ {(total_upsell * TC_VAL):,.2f} MXN</p>
                    <hr style="margin:10px 0;">
                    <h6 style="margin:0;">Total Estancia con Upgrade: ${p_original + total_upsell:,.2f} USD</h6>
                </div>
            """, unsafe_allow_html=True)
        
        with c_res2:
            if hotel == "DREPM":
                st.markdown(f"### 👶 Recordatorio de Edades ({status_rm})")
                col_e1, col_e2 = st.columns(2)
                col_e1.metric("Niño (3-12)", f"${p_nino} USD")
                col_e2.metric("Infante (0-2)", "$0 USD")
                if ninos > 0 and "Swim Out" in c_des:
                    st.error("⚠️ POLÍTICA DREAMS: No se permiten menores en habitaciones Swim Out.")
            else:
                st.info("✨ SECPM: Propiedad Adults Only. El cálculo ignora menores por política de marca.")

# =====================================================
# MÓDULO 4: WORLD OF HYATT (BENEFICIOS 2026)
# =====================================================
elif menu == "🏨 World of Hyatt":
    st.title("🏨 WOH Inclusive Collection")
    tab1, tab2 = st.tabs(["🏆 Estatus y Beneficios", "🔢 Simulador de Puntos"])
    
    with tab1:
        st.subheader("Beneficios Operativos por Nivel")
        beneficios = {
            "Estatus": ["Member", "Discoverist", "Explorist", "Globalist"],
            "Noches Req.": ["0", "10", "30", "60"],
            "Bono Puntos Base": ["--", "10%", "20%", "30%"],
            "Late C/O (Sujeto)": ["--", "2:00 PM", "2:00 PM", "4:00 PM"]
        }
        st.table(beneficios)
        st.markdown("""
            **📣 Notas de Distribución HIC 2026:**
            * Guest of Honor Award: Ahora es premio Milestone al alcanzar las 40 noches.
            * Bono de Puntos se aplica sobre los 5 Puntos Base por USD elegible.
        """)

    with tab2:
        st.subheader("🧮 Simulador de Acumulación de Puntos")
        with st.container(border=True):
            w_col1, w_col2 = st.columns(2)
            tarifa_n = w_col1.number_input("Tarifa elegible por noche (USD)", min_value=0, value=300)
            noches_w = w_col2.number_input("Noches de estancia", min_value=1, value=4)
            
            puntos_base_totales = (tarifa_n * noches_w) * 5
            
            st.divider()
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Member Base", f"{int(puntos_base_totales):,}")
            m2.metric("Discoverist", f"{int(puntos_base_totales * 1.1):,}")
            m3.metric("Explorist", f"{int(puntos_base_totales * 1.2):,}")
            m4.metric("Globalist", f"{int(puntos_base_totales * 1.3):,}")
            st.caption("Puntos estimados. Los impuestos y propinas no generan puntos.")
