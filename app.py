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
# SIDEBAR
# =====================================================
with st.sidebar:
    st.image("HIC.png", use_container_width=True)
    menu = st.radio(
        "Navegación",
        ["🔍 Vista rápida", "➕ Nueva promoción", "📈 Upsell"]
        if st.session_state.is_admin else
        ["🔍 Vista rápida", "📈 Upsell"]
    )

    st.divider()
    if st.session_state.is_admin:
        st.success("🟢 Modo ADMIN activo")
        if st.button("Salir de Admin"):
            st.session_state.is_admin = False
            st.rerun()
    else:
        with st.expander("🔒 Entrar como Admin"):
            pwd = st.text_input("Contraseña", type="password")
            if st.button("Entrar") and pwd == ADMIN_PASSWORD:
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
# UPSELL (COMPLETO – 100% AISLADO)
# =====================================================
elif menu == "📈 Upsell":
    st.subheader("📈 Upsell")

    HABITACIONES = ["JS Garden View", "JS Pool View", "JS Ocean View", "JS Swim Out"]

    col1, col2 = st.columns(2)

    # -----------------------------
    # INPUTS
    # -----------------------------
    with col1:
        cA, cB = st.columns(2)
        hotel = cA.selectbox("Hotel", ["DREPM", "SECPM"])
        fecha = cB.date_input("Fecha", value=date(2026, 4, 1))

        f, a, t = st.columns([4, 1, 4])
        habitacion_actual = f.selectbox("De", HABITACIONES)
        a.markdown("<br>➡️", unsafe_allow_html=True)

        idx = HABITACIONES.index(habitacion_actual)
        opciones = HABITACIONES[idx + 1:]
        habitacion_destino = t.selectbox("A", opciones if opciones else ["N/A"])

        cO1, cO2 = st.columns(2)
        if hotel == "DREPM":
            adultos = cO1.number_input("Adultos", 1, 4, 2)
            ninos = cO2.number_input("Niños", 0, 4, 0)
        else:
            adultos = cO1.number_input("Adultos", 1, 3, 2)
            ninos = 0
            st.caption("ℹ️ Resort solo adultos (18+)")

        cT, cN = st.columns(2)
        tarifa = cT.number_input("Tarifa USD", 500)
        noches = cN.number_input("Noches", 1)

        calcular = st.button("Calcular Upsell", use_container_width=True)

  # -----------------------------
# RESULTADOS
# -----------------------------
with col2:
    if calcular:
        temporada, precios = detectar_ok_rm(fecha)

        if not precios:
            st.warning("No hay reglas de temporada configuradas.")
        else:
            st.success(f"Temporada: {temporada}")

            st.markdown(
                f"🏨 **Upsell:** {habitacion_actual} → {habitacion_destino}"
            )

            if hotel == "DREPM" and ninos > 0:
                net, pub = precios["net"], precios["pub"]
                st.markdown(
                    f"👶 **Niños:** NET {net} USD / {round(net * TC_MXN):,} MXN · "
                    f"PUBLIC {pub} USD / {round(pub * TC_MXN):,} MXN\n\n"
                    "Edades: 0–2 gratis · 3–12 con cargo · 13+ adulto\n\n"
                    "🏊 Swim Out NO acepta niños"
                )

            # ✅ UPSWELL + TARIFA TOTAL (MEJORA)
            incremento = 75 * noches
            tarifa_total = tarifa + incremento

            st.markdown(
                f"""
### 💰 Resumen económico
- **Tarifa actual:** ${tarifa} USD  
- **Upsell estimado:** ${incremento} USD  
- ✅ **Nueva tarifa total:** **${tarifa_total} USD**
"""
            )
    else:
