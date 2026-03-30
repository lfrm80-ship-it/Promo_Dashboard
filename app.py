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
.stButton>button {
    width: 100%;
    border-radius: 5px;
    height: 3em;
    background-color: #00338d;
    color: white;
}
[data-testid="stSidebar"] {
    background-color: #ffffff;
    border-right: 1px solid #e0e0e0;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# 2. PARÁMETROS DEL ENTORNO
# =====================================================
ADMIN_PASSWORD = st.secrets.get("admin_password", "admin")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROMOS_FILE = os.path.join(BASE_DIR, "promociones_produccion.csv")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
TC_VAL = 18.50  # Tipo de Cambio 2026

if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# =====================================================
# 3. MOTOR DE DATOS Y RESPALDOS (REVENUE OPS)
# =====================================================
def guardar_datos_y_respaldar(df, comentario="Actualización"):
    """Guarda el CSV principal y genera un backup con timestamp"""
    df.to_csv(PROMOS_FILE, index=False)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    df.to_csv(os.path.join(BACKUP_DIR, f"backup_{ts}.csv"), index=False)
    with open(os.path.join(BACKUP_DIR, "audit_log.txt"), "a") as f:
        f.write(f"{datetime.now()}: {comentario} - Filas: {len(df)}\n")

def cargar_datos():
    """Carga datos y asegura formato de fecha"""
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
    semanas_pico = [
        (date(2026, 3, 26), date(2026, 4, 13)),
        (date(2026, 12, 20), date(2026, 12, 31))
    ]
    for inicio, fin in semanas_pico:
        if inicio <= fecha <= fin:
            return "PREMIUM", 148
    return "REGULAR", 89

def generar_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Master HIC')
    return output.getvalue()

# =====================================================
# ✅ FIX CRÍTICO STREAMLIT: CARGA GLOBAL DE DATOS
# =====================================================
df = cargar_datos()

# =====================================================
# 4. SIDEBAR Y LOGO
# =====================================================
with st.sidebar:
    # ✅ Logo local siempre visible
    st.image("HIC.png", use_container_width=True)

    st.markdown(
        "<h2 style='text-align:center; color:#00338d;'>Master Record</h2>",
        unsafe_allow_html=True
    )
    st.divider()

    menu = st.radio(
        "Navegación",
        ["🔍 Vista rápida y Filtros",
         "➕ Registro y Modificación",
         "📈 Upsell FD",
         "🏨 World of Hyatt"]
    )

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

# =====================================================
# MÓDULO 1: VISTA RÁPIDA (FILTROS)
# =====================================================
if menu == "🔍 Vista rápida y Filtros":
    st.title("🔎 Consulta Integral de Promociones")

    if df.empty:
        st.info("No hay datos en el Master Record.")
    else:
        # -------------------------------------------------
        # Cálculo de Estatus por Fecha
        # -------------------------------------------------
        today = date.today()

        def estatus_promo(row):
            if pd.isna(row["BW_Inicio"]) or pd.isna(row["TW_Fin"]):
                return "Sin Fecha"
            if row["BW_Inicio"] <= today <= row["TW_Fin"]:
                return "Vigente"
            elif today < row["BW_Inicio"]:
                return "Iniciada"
            else:
                return "Expirada"

        df_view = df.copy()
        df_view["Estatus"] = df_view.apply(estatus_promo, axis=1)

        # -------------------------------------------------
        # Filtros
        # -------------------------------------------------
        f1, f2, f3, f4 = st.columns([1, 1, 1, 2])

        h_sel = f1.multiselect("Hoteles", ["DREPM", "SECPM"])
        m_sel = f2.multiselect(
            "Mercados",
            df_view["Market"].unique() if "Market" in df_view.columns else []
        )
        e_sel = f3.multiselect(
            "Estatus",
            ["Vigente", "Iniciada", "Expirada"],
            default=["Vigente"]
        )
        t_busq = f4.text_input("Buscador Global (Promo / Rate Plan)").strip()

        # -------------------------------------------------
        # Aplicación de filtros
        # -------------------------------------------------
        df_f = df_view.copy()

        if h_sel:
            df_f = df_f[df_f["Hotel"].isin(h_sel)]
        if m_sel:
            df_f = df_f[df_f["Market"].isin(m_sel)]
        if e_sel:
            df_f = df_f[df_f["Estatus"].isin(e_sel)]
        if t_busq:
            mask = df_f.astype(str).apply(
                lambda row: row.str.contains(t_busq, case=False, na=False).any(),
                axis=1
            )
            df_f = df_f[mask]

        # -------------------------------------------------
        # Tabla principal
        # -------------------------------------------------
        st.dataframe(df_f, use_container_width=True, hide_index=True)

        # -------------------------------------------------
        # Exportar a Excel
        # -------------------------------------------------
        if st.session_state.is_admin and not df_f.empty:
            st.download_button(
                label="📥 Exportar Selección a Excel",
                data=generar_excel(df_f),
                file_name=f"HIC_Master_{date.today()}.xlsx",
                mime="application/vnd.ms-excel"
            )

        # -------------------------------------------------
        # Adjuntos / Soportes (VISUALIZACIÓN)
        # -------------------------------------------------
        st.divider()
        st.subheader("📎 Soportes de Promoción")

        soporte_dir = os.path.join(BASE_DIR, "soportes_promos")

        if os.path.exists(soporte_dir):
            soportes = {}

            for archivo in os.listdir(soporte_dir):
                promo_name = archivo.split("_")[0].replace("_", " ")
                soportes.setdefault(promo_name, []).append(archivo)

            if not soportes:
                st.info("No hay archivos de soporte cargados.")
            else:
                for promo, files in soportes.items():
                    with st.expander(f"📌 {promo}", expanded=False):
                        for f in files:
                            ruta = os.path.join(soporte_dir, f)
                            ext = f.lower().split(".")[-1]

                            # Preview de imágenes
                            if ext in ["png", "jpg", "jpeg"]:
                                st.image(
    ruta,
    caption=f,
    use_container_width=True
)



# =====================================================
# MÓDULO 2: REGISTRO Y MODIFICACIÓN (CORREGIDO)
# =====================================================
elif menu == "➕ Registro y Modificación":
    st.title("🛠️ Centro de Control de Inventario")

    if not st.session_state.is_admin:
        st.error("Requiere privilegios de Administrador.")
    else:
        t1, t2 = st.tabs(["🚀 Nueva Campaña", "📝 Extender / Modificar Fechas"])

        # -------------------------------------------------
        # TAB 1: NUEVA CAMPAÑA
        # -------------------------------------------------
        with t1:
            with st.form("new_promo", clear_on_submit=True):
                st.subheader("Datos de la Promoción")

                c1, c2 = st.columns(2)
                p_nom = c1.text_input("Nombre de la Promo (ej: Kids Stay Free)")
                p_htl = c2.multiselect("Hoteles", ["DREPM", "SECPM"])

                c3, c4, c5 = st.columns(3)
                p_mkt = c3.selectbox(
                    "Mercado",
                    ["USA", "CAN", "MEX", "LATAM", "EUR", "Worldwide"]
                )
                p_cod = c4.text_input("Rate Plan Code")
                p_des = c5.number_input("Descuento %", 0, 100, 0)

                st.divider()

                st.markdown("**Vigencias de Booking (BW)**")
                bw1, bw2 = st.columns(2)
                bw_i = bw1.date_input("BW Inicio")
                bw_f = bw2.date_input("BW Fin")

                st.markdown("**Vigencias de Viaje (TW)**")
                tw1, tw2 = st.columns(2)
                tw_i = tw1.date_input("TW Inicio")
                tw_f = tw2.date_input("TW Fin")

                st.divider()

                st.markdown("**Soporte de la Promoción (opcional)**")
                archivo = st.file_uploader(
                    "Subir Imagen, PDF o Excel",
                    type=["png", "jpg", "jpeg", "pdf", "xlsx"]
                )

                p_not = st.text_area("Notas de Combinabilidad / Restricciones")

                if st.form_submit_button("✅ Registrar en Base de Datos"):
                    if p_nom and p_htl:
                        nuevos = pd.DataFrame([{
                            "Hotel": h,
                            "Promo": p_nom,
                            "Market": p_mkt,
                            "Rate_Plan": p_cod,
                            "Descuento": p_des,
                            "BW_Inicio": bw_i,
                            "BW_Fin": bw_f,
                            "TW_Inicio": tw_i,
                            "TW_Fin": tw_f,
                            "Notas": p_not
                        } for h in p_htl])

                        df = pd.concat([df, nuevos], ignore_index=True)
                        guardar_datos_y_respaldar(df, f"Alta: {p_nom}")

                        if archivo is not None:
                            soporte_dir = os.path.join(BASE_DIR, "soportes_promos")
                            os.makedirs(soporte_dir, exist_ok=True)
                            ruta = os.path.join(
                                soporte_dir,
                                f"{p_nom.replace(' ', '_')}_{archivo.name}"
                            )
                            with open(ruta, "wb") as f:
                                f.write(archivo.getbuffer())

                        st.success("Registro completado y respaldo generado.")
                        st.rerun()

        # -------------------------------------------------
        # TAB 2: EXTENDER / MODIFICAR FECHAS (SIN FORM)
        # -------------------------------------------------
        with t2:
            st.subheader("Extender / Modificar Vigencias")

            if df.empty:
                st.info("No hay promociones registradas para modificar.")
            else:
                promo_sel = st.selectbox(
                    "Selecciona la Promoción",
                    sorted(df["Promo"].unique())
                )

                idx = df[df["Promo"] == promo_sel].index[0]

                st.markdown("**Booking Window (BW)**")
                bw1, bw2 = st.columns(2)
                new_bw_i = bw1.date_input("BW Inicio", df.at[idx, "BW_Inicio"])
                new_bw_f = bw2.date_input("BW Fin", df.at[idx, "BW_Fin"])

                st.markdown("**Travel Window (TW)**")
                tw1, tw2 = st.columns(2)
                new_tw_i = tw1.date_input("TW Inicio", df.at[idx, "TW_Inicio"])
                new_tw_f = tw2.date_input("TW Fin", df.at[idx, "TW_Fin"])

                new_notes = st.text_area(
                    "Actualizar Notas",
                    df.at[idx, "Notas"]
                )

                if st.button("💾 Guardar Cambios"):
                    df.loc[df["Promo"] == promo_sel, "BW_Inicio"] = new_bw_i
                    df.loc[df["Promo"] == promo_sel, "BW_Fin"] = new_bw_f
                    df.loc[df["Promo"] == promo_sel, "TW_Inicio"] = new_tw_i
                    df.loc[df["Promo"] == promo_sel, "TW_Fin"] = new_tw_f
                    df.loc[df["Promo"] == promo_sel, "Notas"] = new_notes

                    guardar_datos_y_respaldar(
                        df, f"Modificación de Fechas: {promo_sel}"
                    )
                    st.success("Fechas actualizadas correctamente.")
                    st.rerun()

# =====================================================
# MÓDULO 3: UPSELL FD
# =====================================================
elif menu == "📈 Upsell FD":
    st.title("📈 Calculadora de Upsell Front Desk")

    CATS = {
        "JS Garden View": 0,
        "JS Pool View": 45,
        "JS Ocean View": 90,
        "JS Swim Out": 150
    }

    with st.container(border=True):
        r1 = st.columns([1, 1, 1, 1])
        f_arr = r1[0].date_input("Llegada", date.today())
        nts = r1[1].number_input("Noches", 1, 30, 1)
        c_de = r1[2].selectbox("De", list(CATS))
        c_a = r1[3].selectbox("A", [k for k in CATS if CATS[k] > CATS[c_de]])

        if st.button("🚀 Calcular"):
            diff = (CATS[c_a] - CATS[c_de]) * nts
            temp, _ = detectar_temporada_rm(f_arr)
            st.success(f"Upgrade total: ${diff:,.2f} USD | Temporada {temp}")

# =====================================================
# MÓDULO 4: WORLD OF HYATT – VISTA OPERATIVA
# =====================================================
elif menu == "🏨 World of Hyatt":
    st.title("🏨 World of Hyatt – Operational Guide")
    st.caption(
        "Apply benefits accurately and calculate points based on guest tier and eligible spend."
    )

    # -------------------------------------------------
    # Definición de estatus WOH (operativa)
    # -------------------------------------------------
    woh = {
        "Member": {
            "noches": 0,
            "bonus": 0,
            "late": "Subject to availability",
            "priority": "Standard recognition",
            "tooltip": "Members earn points on eligible spend and access member‑only rates."
        },
        "Discoverist": {
            "noches": 10,
            "bonus": 10,
            "late": "Up to 2:00 PM",
            "priority": "Enhanced recognition",
            "tooltip": "Discoverist members enjoy added recognition and a points bonus."
        },
        "Explorist": {
            "noches": 30,
            "bonus": 20,
            "late": "Up to 2:00 PM",
            "priority": "High priority service",
            "tooltip": "Explorist members receive elevated benefits suited for frequent stays."
        },
        "Globalist": {
            "noches": 60,
            "bonus": 30,
            "late": "Guaranteed 4:00 PM",
            "priority": "Premium priority",
            "tooltip": "Globalist members receive the highest level of recognition and benefits."
        }
    }

    # -------------------------------------------------
    # Selector de estatus
    # -------------------------------------------------
    estatus = st.radio(
        "World of Hyatt Tier",
        list(woh.keys()),
        horizontal=True,
        help="Select the guest's World of Hyatt tier to apply benefits correctly."
    )

    b = woh[estatus]

    # -------------------------------------------------
    # Beneficios operativos
    # -------------------------------------------------
    st.markdown("### 🛎️ Tier Benefits")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "Tier Qualification",
        f"{b['noches']} nights",
        help="Eligible nights required in a calendar year."
    )
    c2.metric(
        "Points Bonus",
        f"{b['bonus']}%",
        help="Bonus applied to base points on eligible spend."
    )
    c3.metric(
        "Late Check‑Out",
        b["late"],
        help="Late check‑out benefit according to tier terms."
    )
    c4.metric(
        "Service Priority",
        b["priority"],
        help="Operational level of recognition for this tier."
    )

    st.info(b["tooltip"])

    # -------------------------------------------------
    # Calculadora de puntos
    # -------------------------------------------------
    st.divider()
    st.markdown("### 🔢 Points Accrual Calculator")

    col1, col2 = st.columns(2)

    with col1:
        tarifa = st.number_input(
            "Eligible nightly rate (USD)",
            value=300,
            help="Base room rate eligible for World of Hyatt points."
        )

    with col2:
        noches = st.number_input(
            "Number of nights",
            value=3,
            min_value=1,
            help="Total eligible nights for the stay."
        )

    puntos_base = tarifa * noches * 5
    puntos_totales = puntos_base * (1 + b["bonus"] / 100)

    r1, r2, r3 = st.columns(3)
    r1.metric(
        "Base Points",
        f"{int(puntos_base):,}",
        help="Standard earning rate: 5 points per USD."
    )
    r2.metric(
        "Tier Bonus",
        f"+{int(puntos_totales - puntos_base):,}",
        help="Bonus points earned from tier status."
    )
    r3.metric(
        f"Total Points ({estatus})",
        f"{int(puntos_totales):,}",
        help="Total points credited for the stay."
    )

    st.caption(
        "Operational note: Points are awarded only on eligible spend in accordance with "
        "World of Hyatt terms and conditions."
    )
