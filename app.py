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
# FUNCIONES DE PROMOCIONES (ÚNICA ESCRITURA)
# =====================================================
def cargar_promos():
    if not os.path.exists(PROMOS_FILE):
        return pd.DataFrame()
    df = pd.read_csv(PROMOS_FILE)
    for col in ["BW_Inicio", "BW_Fin", "TW_Inicio", "TW_Fin"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
    return df


def guardar_promos(df):
    # 🔒 PROTECCIÓN CRÍTICA — nunca guardar vacío
    if df is None or len(df) == 0:
        st.error("⛔ Seguridad: intento de guardar CSV vacío BLOQUEADO")
        st.stop()
    df.to_csv(PROMOS_FILE, index=False)


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
# REGLAS OK RM (SOLO UPSELL – READ ONLY)
# =====================================================
OK_RM_RULES = {
    2026: {
        "ok_rm": [
            ("2026-03-26", "2026-04-13"),
            ("2026-12-21", "2026-12-31")
        ],
        "regular": {"net": 67, "pub": 89},
        "ok": {"net": 111, "pub": 148}
    },
    2027: {
        "ok_rm": [
            ("2027-03-20", "2027-04-11"),
            ("2027-12-21", "2028-01-04")
        ],
        "regular": {"net": 71, "pub": 95},
        "ok": {"net": 118, "pub": 157}
    }
}

TC_MXN = 18.50


def detectar_ok_rm(fecha_llegada):
    reglas = OK_RM_RULES.get(fecha_llegada.year)
    if not reglas:
        return None, None
    for i, f in reglas["ok_rm"]:
        if datetime.strptime(i, "%Y-%m-%d").date() <= fecha_llegada <= datetime.strptime(f, "%Y-%m-%d").date():
            return "OK RM", reglas["ok"]
    return "REGULAR", reglas["regular"]

# =====================================================
# SIDEBAR (LOGO PEQUEÑO Y CENTRADO)
# =====================================================
with st.sidebar:
    # --- TRUCO DE CENTRADO Y TAMAÑO ---
    # Creamos 3 columnas en el sidebar. La imagen va en la central (proporción 2).
    # Las columnas laterales vacías (proporción 1) crean el efecto de tamaño y centrado sutil.
    c1, c2, c3 = st.columns([1, 2, 1]) 
    with c2:
        # Aquí cargamos la imagen. Ya no usamos use_container_width=True
        # para que no se estire. 
        # Asegúrate de usar el nombre correcto del archivo de imagen que tienes.
        # En la imagen de muestra se ve "InclusiveCollection_Stacked_RGB_FullColor.png" o similar.
        # Reemplaza "HIC.png" con el nombre exacto de tu archivo si es necesario.
        st.image("HIC.png") 

    st.write("") # Espaciador sutil
    
    # Navegación
    menu = st.radio(
    "Navegación",
    ["🔍 Vista rápida", "➕ Nueva promoción", "📈 Upsell", "🏨 WOH"] # <--- Agrégalo aquí
    if st.session_state.is_admin else
    ["🔍 Vista rápida", "📈 Upsell", "🏨 WOH"] # <--- Y aquí para usuarios normales
)

    st.divider()
    if st.session_state.is_admin:
        st.success("🟢 Modo ADMIN activo")
        if st.button("Salir de Admin", use_container_width=True): # Botón ancho para equilibrio visual
            st.session_state.is_admin = False
            st.rerun()
    else:
        with st.expander("🔒 Entrar como Admin"):
            pwd = st.text_input("Contraseña", type="password")
            if st.button("Entrar", use_container_width=True) and pwd == ADMIN_PASSWORD:
                st.session_state.is_admin = True
                st.rerun()
# =====================================================
# DATA (CARGA ÚNICA)
# =====================================================
df = cargar_promos()

# =====================================================
# VISTA RÁPIDA (READ ONLY + FILTROS)
# =====================================================
if menu == "🔍 Vista rápida":
    if df.empty:
        st.info("No hay promociones registradas.")
    else:
        df_view = df.copy()
        df_view["Estado"] = df_view.apply(calcular_estado, axis=1)

        st.subheader("🔎 Filtros")

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            f_hotel = st.multiselect("Hotel", df_view["Hotel"].dropna().unique())
        with c2:
            f_estado = st.multiselect("Estado", ["Activa", "Futura", "Expirada"])
        with c3:
            f_market = st.multiselect("Market", df_view["Market"].dropna().unique())
        with c4:
            f_texto = st.text_input("Buscar texto")

        if f_hotel:
            df_view = df_view[df_view["Hotel"].isin(f_hotel)]
        if f_estado:
            df_view = df_view[df_view["Estado"].isin(f_estado)]
        if f_market:
            df_view = df_view[df_view["Market"].isin(f_market)]
        if f_texto:
            txt = f_texto.lower()
            df_view = df_view[
                df_view.apply(
                    lambda r: txt in " ".join(r.astype(str)).lower(), axis=1
                )
            ]

        st.dataframe(df_view, use_container_width=True, hide_index=True)
        st.download_button(
            "📥 Descargar Excel filtrado",
            generar_excel(df_view),
            f"MasterRecord_{date.today()}.xlsx"
        )

# =====================================================
# NUEVA PROMOCIÓN (ÚNICA SECCIÓN QUE ESCRIBE CSV)
# =====================================================
elif menu == "➕ Nueva promoción":
    with st.form("new_promo"):
        st.subheader("➕ Nueva promoción")

        # =============================
        # CARGA MANUAL
        # =============================
        promo = st.text_input("Promoción")
        hotels = st.multiselect("Hotel", PROPERTIES)
        market = st.selectbox("Market", MARKETS)
        rate = st.text_input("Rate Plan")
        discount = st.number_input("Descuento (%)", 0, 100)

        c1, c2, c3, c4 = st.columns(4)
        bw_i = c1.date_input("BW Inicio")
        bw_f = c2.date_input("BW Fin")
        tw_i = c3.date_input("TW Inicio")
        tw_f = c4.date_input("TW Fin")

        # =============================
        # ADJUNTOS (UNA SOLA OPCIÓN)
        # =============================
        st.subheader("📎 Adjuntos")
        adjuntos = st.file_uploader(
            "Subir archivos (Imagen / PDF / Excel)",
            type=["png", "jpg", "jpeg", "pdf", "xlsx"],
            accept_multiple_files=True,
            key="adjuntos_unicos"
        )

        notas = st.text_area("Notas")

        # =============================
        # CARGA MASIVA (MASTER)
        # =============================
        st.subheader("📥 Carga masiva desde Excel")
        excel = st.file_uploader(
            "Archivo Excel para Master Record",
            ["xlsx"],
            key="excel_master"
        )

        submit = st.form_submit_button("Guardar")

        # =============================
        # GUARDADO SEGURO (FIX DEFINITIVO)
        # =============================
        if submit:
            st.info("Procesando información…")  # feedback visual inmediato

            df_actual = cargar_promos()

            # ---- Caso 1: Excel Master ----
            if excel is not None:
                df_excel = pd.read_excel(excel)

                if df_excel.empty:
                    st.error("⛔ El Excel está vacío. No se guardó nada.")
                    st.stop()

                df_actual = pd.concat([df_actual, df_excel], ignore_index=True)

            # ---- Caso 2: Carga Manual ----
            elif promo and hotels:
                os.makedirs("media", exist_ok=True)

                image_path = ""
                pdf_path = ""
                excel_ref_path = ""

                if adjuntos:
                    for archivo in adjuntos:
                        file_path = os.path.join("media", archivo.name)
                        with open(file_path, "wb") as f:
                            f.write(archivo.getbuffer())

                        nombre = archivo.name.lower()
                        if nombre.endswith((".png", ".jpg", ".jpeg")):
                            image_path = file_path
                        elif nombre.endswith(".pdf"):
                            pdf_path = file_path
                        elif nombre.endswith(".xlsx"):
                            excel_ref_path = file_path

                rows = []
                for h in hotels:
                    rows.append({
                        "Hotel": h,
                        "Promo": promo,
                        "Market": market,
                        "Rate_Plan": rate,
                        "Descuento": discount,
                        "BW_Inicio": bw_i,
                        "BW_Fin": bw_f,
                        "TW_Inicio": tw_i,
                        "TW_Fin": tw_f,
                        "Archivo_Imagen": image_path,
                        "Archivo_PDF": pdf_path,
                        "Archivo_Excel_Referencia": excel_ref_path,
                        "Notas": notas
                    })

                df_actual = pd.concat(
                    [df_actual, pd.DataFrame(rows)],
                    ignore_index=True
                )

            else:
                st.error("⛔ Debes cargar un Excel o completar el formulario manual.")
                st.stop()

            guardar_promos(df_actual)
            st.success("✅ Promoción guardada correctamente")
            st.rerun()

# =====================================================
# MÓDULO: UPSELL
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
    TC_VAL = 18.5 

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📋 Datos de la Reserva")
        cA, cB = st.columns(2)
        hotel_sel = cA.selectbox("Hotel", ["DREPM", "SECPM"])
        fecha_sel = cB.date_input("Fecha de estancia", value=date(2026, 4, 1))

        f, a, t = st.columns([4, 1, 4])
        hab_actual = f.selectbox("Categoría Original", HABITACIONES)
        a.markdown("<br><center>➡️</center>", unsafe_allow_html=True)
        
        idx_act = HABITACIONES.index(hab_actual)
        posibles_destinos = HABITACIONES[idx_act + 1:]
        hab_destino = t.selectbox("Upgrade a", posibles_destinos if posibles_destinos else ["Máxima categoría"])

        cO1, cO2 = st.columns(2)
        adultos = cO1.number_input("Adultos", 1, 4, 2)
        
        if hotel_sel == "DREPM":
            ninos = cO2.number_input("Niños (0-12)", 0, 4, 0)
        else:
            ninos = 0
            st.caption("ℹ️ Secrets: Solo adultos (18+).")

        cT, cN = st.columns(2)
        tarifa_orig = cT.number_input("Tarifa Original (Total USD)", min_value=1, value=500)
        noches_sel = cN.number_input("Noches", 1, 30, 1)

        btn_calcular = st.button("🚀 Calcular Upgrade", use_container_width=True)

    with col2:
        if btn_calcular:
            pub_val = 0
            if ninos > 0 and "Swim Out" in hab_destino:
                st.error("❌ **RESTRICCIÓN:** No se permiten menores en categorías **Swim Out**.")
            elif hab_destino == "Máxima categoría":
                st.warning("La reserva ya está en la categoría más alta.")
            else:
                temporada, precios_temp = detectar_ok_rm(fecha_sel)
                dif_noche = (UPSELL_VALUES[hab_destino] - UPSELL_VALUES[hab_actual])
                if temporada == "OK RM":
                    dif_noche *= 1.25 
                
                total_upsell_usd = dif_noche * noches_sel
                total_final_usd = tarifa_orig + total_upsell_usd
                total_upsell_mxn = total_upsell_usd * TC_VAL
                total_final_mxn = total_final_usd * TC_VAL

                color_bg = "#d4edda" if temporada == "REGULAR" else "#fff3cd"
                st.markdown(f"<div style='background-color:{color_bg}; padding:10px; border-radius:10px; text-align:center; border: 1px solid #ddd;'><h4 style='margin:0; color:#333;'>📅 Temporada: {temporada} (TC: {TC_VAL})</h4></div>", unsafe_allow_html=True)
                
                st.write("") 
                m1, m2 = st.columns(2)
                m1.metric("Costo Upgrade", f"${total_upsell_usd:,.2f} USD")
                m1.write(f"**≈ {total_upsell_mxn:,.2f} MXN**")
                m2.metric("Total Estancia", f"${total_final_usd:,.2f} USD")
                m2.write(f"**≈ {total_final_mxn:,.2f} MXN**")

                st.divider()

                if hotel_sel == "DREPM":
                    pub_val = precios_temp['pub']
                    st.markdown("#### 👶 Política y Costos de Menores")
                    e1, e2, e3 = st.columns(3)
                    with e1: st.info("**0-2 años**\n\nGratis")
                    with e2: st.success(f"**3-12 años**\n\n${pub_val} USD\n({round(pub_val*TC_VAL):,} MXN)")
                    with e3: st.warning("**13+ años**\n\nAdulto")
                
                with st.expander("📋 Resumen para el Cliente", expanded=True):
                    txt = f"Upgrade: {hab_actual} ➡️ {hab_destino}\nCosto: ${total_upsell_usd:,.2f} USD (${total_upsell_mxn:,.2f} MXN)\nTotal: ${total_final_usd:,.2f} USD (${total_final_mxn:,.2f} MXN)"
                    st.code(txt, language="text")
        else:
            st.info("Configura los datos y presiona 'Calcular'.")

# =====================================================
# MÓDULO: WOH (RESTAURADO + ENLACE HTML)
# =====================================================
elif menu == "🏨 WOH":
    st.subheader("🏨 World of Hyatt - Programa de Lealtad")
    
    # Botón HTML elegante a la derecha para la página oficial
    st.markdown("""
        <div style="text-align: right; margin-top: -45px;">
            <a href="https://world.hyatt.com/content/gp/en/program-overview.html" target="_blank" 
               style="color: #00338d; text-decoration: none; font-weight: bold; font-size: 14px; border: 1px solid #00338d; padding: 5px 15px; border-radius: 5px; background-color: #f8f9fa;">
                🌐 Ir a Página Oficial WOH
            </a>
        </div>
        <br>
    """, unsafe_allow_html=True)

    # Organización por Tabs para que se vea "Super Pro"
    tab_niveles, tab_milestones, tab_beneficios = st.tabs([
        "🏅 Niveles y Status", 
        "🎁 Milestone Rewards", 
        "✨ Beneficios Clave"
    ])

    with tab_niveles:
        st.markdown("### Requisitos para alcanzar Status")
        # Tabla comparativa de niveles oficial
        niveles_data = {
            "Nivel": ["Member", "Discoverist", "Explorist", "Globalist"],
            "Noches Req.": ["0", "10", "30", "60"],
            "Puntos Base": ["0", "25,000", "50,000", "100,000"],
            "Bono Puntos": ["-", "10%", "20%", "30%"]
        }
        st.table(niveles_data)
        st.info("💡 Recuerda: Se acumulan 5 puntos base por cada $1 USD en cargos elegibles.")

    with tab_milestones:
        st.markdown("### 🎯 Premios por Hitos (Milestones)")
        st.write("Premios elegibles por el huésped al acumular noches anuales:")
        
        milestones = {
            "20 Noches": "2 Club Access Awards O 2,000 Bonus Points",
            "30 Noches": "1 Free Night (Cat 1-4) + 2 Club Access Awards",
            "40 Noches": "1 Guest of Honor Award + Suite Upgrade O 5,000 pts",
            "60 Noches": "2 Guest of Honor + 2 Suite Upgrades + Cat 1-7 Free Night",
            "100 Noches": "1 Free Night (Cat 1-7) + Opción de Suite Upgrade o Puntos"
        }
        
        for noches, premio in milestones.items():
            with st.expander(f"🚩 Al llegar a {noches} noches"):
                st.write(f"**Beneficio:** {premio}")

    with tab_beneficios:
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.markdown("""
            #### 🕒 Check-out Extendido
            * **Discoverist:** 2:00 PM (Sujeto a disp.)
            * **Explorist:** 2:00 PM (Sujeto a disp.)
            * **Globalist:** 4:00 PM (Garantizado en resorts)
            """)
            
        with col_b:
            st.markdown("""
            #### 💎 Guest of Honor (Preciado)
            * El Globalist puede otorgar sus beneficios a amigos o familiares.
            * Incluye: Desayuno, Upgrades y Late Check-out para el beneficiario.
            """)

    # --- CALCULADORA DE PUNTOS (EL TOQUE FINAL) ---
    st.divider()
    st.markdown("### 🧮 Calculadora Rápida de Puntos")
    c1, c2, c3 = st.columns([2, 2, 2])
    
    monto_usd = c1.number_input("Gasto en Habitación/Consumos ($USD)", min_value=0, value=100, key="woh_usd")
    status_calculo = c2.selectbox("Status del Huésped", ["Member", "Discoverist", "Explorist", "Globalist"], key="woh_status")
    
    # Lógica de bonos
    bonos = {"Member": 1.0, "Discoverist": 1.1, "Explorist": 1.2, "Globalist": 1.3}
    pts_base = monto_usd * 5
    pts_totales = pts_base * bonos[status_calculo]
    
    c3.metric("Puntos Estimados", f"{int(pts_totales)} pts")
    st.caption(f"Desglose: {pts_base} base + {int(pts_totales - pts_base)} bono de status.")
