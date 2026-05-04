import streamlit as st
import pandas as pd
import io
import json
import time
import base64
import requests
from datetime import date

# =========================================================
# CONFIGURACIÓN GENERAL
# =========================================================
st.set_page_config(
    page_title="Master Record Playa Mujeres",
    layout="wide"
)

ADMIN_PASSWORD = st.secrets["admin_password"]
WEB_APP_URL = st.secrets["apps_script_url"]

SHEET_ID = "1dvYqQFpI7VqJFuOLeyqQdb2GijFrhoFrNrpWidakAq4"
WORKSHEET = "promociones"

# =========================================================
# FUNCIONES AUXILIARES
# =========================================================
def csv_url():
    return (
        f"https://docs.google.com/spreadsheets/d/"
        f"{SHEET_ID}/gviz/tq?"
        f"tqx=out:csv&sheet={WORKSHEET}&nocache={int(time.time())}"
    )


def cargar_df():
    try:
        df = pd.read_csv(csv_url())
    except Exception:
        df = pd.DataFrame()

    for c in ["BW_Inicio", "BW_Fin", "TW_Inicio", "TW_Fin"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce").dt.date

    return df


def estado(row):
    if pd.isna(row["TW_Inicio"]) or pd.isna(row["TW_Fin"]):
        return "Expirada"

    hoy = date.today()

    if row["TW_Inicio"] <= hoy <= row["TW_Fin"]:
        return "Activa"

    if hoy < row["TW_Inicio"]:
        return "Futura"

    return "Expirada"


def generar_excel(df):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False)
    buffer.seek(0)
    return buffer.getvalue()


# =========================================================
# SESSION STATE
# =========================================================
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False


# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    st.image("HIC.png", use_container_width=True)

    menu = st.radio(
        "Navegación",
        ["Vista rápida", "Nueva promoción", "Upsell", "World of Hyatt"]
    )

    with st.expander("Admin"):
        pwd = st.text_input("Password", type="password")
        if st.button("Entrar") and pwd == ADMIN_PASSWORD:
            st.session_state.is_admin = True
            st.rerun()


# =========================================================
# DATA
# =========================================================
df = cargar_df()
st.markdown("## Master Record Playa Mujeres")


# =========================================================
# VISTA RÁPIDA
# =========================================================
if menu == "Vista rápida":

    if df.empty:
        st.info("No hay promociones registradas.")

    else:
        df = df.copy()
        df["Estado"] = df.apply(estado, axis=1)

        search = st.text_input(
            "Buscar (Promoción, Hotel o Market)",
            placeholder="Ej. Summer Sale, DREPM, USA"
        )

        c1, c2, c3 = st.columns(3)

        with c1:
            filtro_estado = st.multiselect(
                "Estado",
                ["Activa", "Futura", "Expirada"],
                default=["Activa", "Futura", "Expirada"]
            )

        with c2:
            filtro_hotel = st.multiselect(
                "Hotel",
                sorted(df["Hotel"].dropna().unique())
            )

        with c3:
            filtro_market = st.multiselect(
                "Market",
                sorted(df["Market"].dropna().unique())
            )

        df_view = df.copy()

        if filtro_estado:
            df_view = df_view[df_view["Estado"].isin(filtro_estado)]

        if filtro_hotel:
            df_view = df_view[df_view["Hotel"].isin(filtro_hotel)]

        if filtro_market:
            df_view = df_view[df_view["Market"].isin(filtro_market)]

        if search:
            s = search.lower()
            df_view = df_view[
                df_view["Promo"].str.lower().str.contains(s, na=False)
                | df_view["Hotel"].str.lower().str.contains(s, na=False)
                | df_view["Market"].str.lower().str.contains(s, na=False)
            ]

        if df_view.empty:
            st.warning("No hay promociones con los filtros actuales.")

        else:
            columnas = [
                "Hotel", "Promo", "Market", "Rate_Plan", "Descuento",
                "BW_Inicio", "BW_Fin", "TW_Inicio", "TW_Fin", "Estado"
            ]
            columnas = [c for c in columnas if c in df_view.columns]

            st.dataframe(
                df_view[columnas],
                use_container_width=True,
                hide_index=True
            )

            st.download_button(
                "Descargar Excel",
                data=generar_excel(df_view[columnas]),
                file_name=f"MasterRecord_{date.today()}.xlsx"
            )

            st.divider()
            st.markdown("### Testigos / Material adjunto")

            if "Archivo_Path" in df_view.columns:
                for idx, row in df_view.iterrows():
                    link = row["Archivo_Path"]

                    if pd.isna(link) or str(link).strip() == "":
                        continue

                    st.markdown(
                        f"**{row['Promo']}**  \n"
                        f"{row['Hotel']} · {row['Market']}"
                    )

                    link = str(link)

                    if link.lower().endswith((".png", ".jpg", ".jpeg")):
                        st.image(link, use_container_width=True)

                    elif link.lower().endswith(".pdf"):
                        st.markdown(
                            f'<iframe src="{link}" width="100%" height="600"></iframe>',
                            unsafe_allow_html=True
                        )

                    else:
                        st.link_button(
                            "⬇️ Descargar archivo",
                            link,
                            key=f"file_{idx}"
                        )


# =========================================================
# NUEVA PROMOCIÓN
# =========================================================
if menu == "Nueva promoción":

    with st.form("new_promo", clear_on_submit=True):

        col1, col2 = st.columns(2)

        with col1:
            promo = st.text_input("Promoción *")
            hotels = st.multiselect("Hotel *", ["DREPM", "SECPM"])

        with col2:
            rate = st.text_input("Rate Plan *")
            discount = st.number_input("Descuento (%)", 0, 100, step=1)

        market = st.selectbox(
            "Market *",
            ["USA", "CAN", "MEX", "LATAM", "EUR", "Worldwide"]
        )

        st.markdown("### Booking & Travel Window")

        bw_i, bw_f, tw_i, tw_f = st.columns(4)
        bw_i = bw_i.date_input("BW IN")
        bw_f = bw_f.date_input("BW FIN")
        tw_i = tw_i.date_input("TW IN")
        tw_f = tw_f.date_input("TW FIN")

        archivo = st.file_uploader(
            "Archivo (PNG, JPG, PDF, XLS, XLSX, DOC, DOCX)",
            ["png", "jpg", "jpeg", "pdf", "xls", "xlsx", "doc", "docx"]
        )

        notas = st.text_area("Notas / Restricciones")

        submit = st.form_submit_button("Registrar promoción")

        if submit:

            file_name = None
            file_type = None
            file_content = None

            if archivo:
                file_name = archivo.name
                file_type = archivo.type
                file_content = base64.b64encode(
                    archivo.getvalue()
                ).decode()

            for h in hotels:
                payload = {
                    "Hotel": h,
                    "OTA": "",
                    "Promo": promo,
                    "Market": market,
                    "Rate_Plan": rate,
                    "Descuento": discount,
                    "BW_Inicio": str(bw_i),
                    "BW_Fin": str(bw_f),
                    "TW_Inicio": str(tw_i),
                    "TW_Fin": str(tw_f),
                    "Notas": notas
                }

                if file_content:
                    payload.update({
                        "FileName": file_name,
                        "FileType": file_type,
                        "FileContent": file_content
                    })

                r = requests.post(
                    WEB_APP_URL,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )

                if r.status_code != 200:
                    st.error("Error al guardar promoción")
                    st.stop()

            st.success("¡Promoción registrada correctamente!")


# =========================================================
# UPSELL
# =========================================================
if menu == "Upsell":

    st.markdown("## 💰 Calculadora de Upsell")
    st.markdown("Optimiza el revenue sugiriendo upgrades de habitación")
    st.divider()

    # =====================================================
    # INPUTS PRINCIPALES
    # =====================================================
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        hotel = st.selectbox("Hotel *", ["DREPM (Familia)", "SECPM (Solo Adultos)"])

    with col2:
        noches = st.number_input("Noches de estadía *", 1, 30, 1)

    with col3:
        tarifa_actual = st.number_input("Tarifa Actual (USD/noche) *", 50, 5000, 200, step=10)

    with col4:
        hab_reservada = st.selectbox("Habitación Reservada *", ["Single", "Double", "Suite", "Grand Suite"])

    st.divider()

    # =====================================================
    # CONFIGURACIÓN POR HOTEL
    # =====================================================
    if "DREPM" in hotel:
        st.subheader("🏨 DREPM - Resort Familiar")
        st.caption("Incluye opciones con Children / Extra Pax")

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            single = st.number_input("Single (USD/noche)", 100, 2000, 150, step=10, key="drepm_single")

        with col2:
            double = st.number_input("Double (USD/noche)", 120, 2500, 200, step=10, key="drepm_double")

        with col3:
            xtra_pax = st.number_input("Extra Pax (USD/noche)", 50, 1000, 80, step=10, key="drepm_xtra")

        with col4:
            children = st.number_input("Children (USD/noche)", 30, 800, 60, step=10, key="drepm_children")

        with col5:
            suite = st.number_input("Suite (USD/noche)", 200, 3000, 350, step=10, key="drepm_suite")

        col1b, col2b, col3b = st.columns(3)

        with col1b:
            grand_suite = st.number_input("Grand Suite (USD/noche)", 250, 4000, 500, step=10, key="drepm_grand")

        tarifas = {
            "Single": single,
            "Double": double,
            "Suite": suite,
            "Grand Suite": grand_suite,
            "Extra Pax": xtra_pax,
            "Children": children
        }

    else:
        st.subheader("🌆 SECPM - Resort Adultos")
        st.caption("Solo para huéspedes adultos - Sin Children")

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            single = st.number_input("Single (USD/noche)", 100, 2000, 180, step=10, key="secpm_single")

        with col2:
            double = st.number_input("Double (USD/noche)", 120, 2500, 250, step=10, key="secpm_double")

        with col3:
            xtra_pax = st.number_input("Extra Pax (USD/noche)", 50, 1000, 120, step=10, key="secpm_xtra")

        with col4:
            suite = st.number_input("Suite (USD/noche)", 200, 3000, 400, step=10, key="secpm_suite")

        with col5:
            grand_suite = st.number_input("Grand Suite (USD/noche)", 250, 4000, 600, step=10, key="secpm_grand")

        tarifas = {
            "Single": single,
            "Double": double,
            "Suite": suite,
            "Grand Suite": grand_suite,
            "Extra Pax": xtra_pax
        }

    st.divider()

    # =====================================================
    # CÁLCULOS
    # =====================================================
    tarifa_reservada = tarifas[hab_reservada]
    inversion_actual = tarifa_actual * noches

    st.markdown("### 📊 Análisis de Opciones de Upsell")

    # Crear dataframe de opciones
    opciones = []

    for categoria, tarifa in tarifas.items():
        if categoria == hab_reservada:
            continue

        diferencial = tarifa - tarifa_actual
        inversion_nueva = tarifa * noches
        revenue_adicional = diferencial * noches

        opciones.append({
            "Categoría": categoria,
            "Tarifa/Noche": f"${tarifa:,.0f}",
            "Diferencial": f"${diferencial:+,.0f}",
            "Inversión Total": f"${inversion_nueva:,.0f}",
            "Revenue Adicional": f"${revenue_adicional:+,.0f}"
        })

    df_opciones = pd.DataFrame(opciones)

    # Mostrar tabla
    st.dataframe(df_opciones, use_container_width=True, hide_index=True)

    # =====================================================
    # RESUMEN Y RECOMENDACIONES
    # =====================================================
    st.divider()
    st.markdown("### 🎯 Resumen de la Reserva")

    m1, m2, m3, m4 = st.columns(4)

    m1.metric("Habitación Actual", hab_reservada)
    m2.metric("Tarifa/Noche", f"${tarifa_actual:,.0f}")
    m3.metric("Noches", f"{noches} noche(s)")
    m4.metric("Inversión Total", f"${inversion_actual:,.0f}")

    # Opción de mayor revenue
    st.divider()
    st.markdown("### 💡 Mejor Oportunidad de Upsell")

    opciones_positivas = [
        (cat, tarif, (tarif - tarifa_actual) * noches)
        for cat, tarif in tarifas.items()
        if tarif > tarifa_actual and cat != hab_reservada
    ]

    if opciones_positivas:
        opciones_positivas.sort(key=lambda x: x[2], reverse=True)
        mejor_cat, mejor_tarif, mejor_revenue = opciones_positivas[0]

        col_rec1, col_rec2, col_rec3 = st.columns(3)

        with col_rec1:
            st.metric("🏆 Categoría Recomendada", mejor_cat)

        with col_rec2:
            st.metric("📈 Revenue Adicional", f"${mejor_revenue:,.0f}")

        with col_rec3:
            incremento_pct = ((mejor_tarif - tarifa_actual) / tarifa_actual) * 100
            st.metric("% Incremento", f"{incremento_pct:+.1f}%")

        st.success(
            f"✅ **Sugerencia:** Ofrecer upgrade a **{mejor_cat}** "
            f"por **${mejor_tarif:,.0f}/noche** generaría **${mejor_revenue:,.0f}** "
            f"adicionales en esta estadía."
        )
    else:
        st.info("💬 No hay opciones de upgrade disponibles para esta tarifa.")


# =========================================================
# WORLD OF HYATT — PRO
# Calculadora + Valor por Dólar
# =========================================================
if menu == "World of Hyatt":

    st.markdown("## 🌟 World of Hyatt")
    st.markdown("Optimiza el valor de cada estadía usando puntos Hyatt")
    st.divider()

    tab1, tab2 = st.tabs(["🧮 Calculadora", "💡 Valor por dólar"])

    # =====================================================
    # TAB 1: CALCULADORA PRO
    # =====================================================
    with tab1:
        st.subheader("🧮 Calculadora de Puntos Hyatt")
        st.caption("Estimación basada en earning oficial World of Hyatt + bonus promedio Inclusive (+15%)")

        c1, c2, c3 = st.columns(3)

        with c1:
            noches = st.number_input("Noches de la estadía", 1, 30, 5)
            tarifa = st.number_input("Tarifa promedio por noche (USD)", 100, 5000, 500, step=50)

        with c2:
            nivel = st.selectbox(
                "Nivel de membresía",
                [
                    "Member (5 pts/$)",
                    "Discoverist (5 pts/$)",
                    "Explorist (6 pts/$)",
                    "Globalist (6.5 pts/$)"
                ]
            )

        with c3:
            categoria = st.selectbox("Categoría del hotel", [1,2,3,4,5,6,7,8])
            temporada = st.selectbox("Temporada", ["Off-Peak", "Standard", "Peak"])

        # ---- CONFIG ----
        pts_map = {
            "Member (5 pts/$)": 5,
            "Discoverist (5 pts/$)": 5,
            "Explorist (6 pts/$)": 6,
            "Globalist (6.5 pts/$)": 6.5
        }
        pts_por_dolar = pts_map[nivel]

        puntos_por_categoria = {
            1: {"Off-Peak":3500,  "Standard":5000,  "Peak":6500},
            2: {"Off-Peak":6500,  "Standard":8000,  "Peak":9500},
            3: {"Off-Peak":9000,  "Standard":12000, "Peak":15000},
            4: {"Off-Peak":12000, "Standard":15000, "Peak":18000},
            5: {"Off-Peak":17000, "Standard":20000, "Peak":23000},
            6: {"Off-Peak":21000, "Standard":25000, "Peak":29000},
            7: {"Off-Peak":25000, "Standard":30000, "Peak":35000},
            8: {"Off-Peak":35000, "Standard":40000, "Peak":45000},
        }

        # ---- CÁLCULOS ----
        gasto_total = noches * tarifa
        puntos_base = gasto_total * pts_por_dolar
        puntos_totales = int(puntos_base * 1.15)

        pts_noche = puntos_por_categoria[categoria][temporada]
        noches_posibles = puntos_totales // pts_noche

        # ---- RESULTADOS ----
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("💰 Gasto total", f"${gasto_total:,.0f}")
        r2.metric("⭐ Puntos base", f"{int(puntos_base):,}")
        r3.metric("🎁 Bonus 15%", f"{int(puntos_totales - puntos_base):,}")
        r4.metric("🏆 Total puntos", f"{puntos_totales:,}")

        st.success(
            f"Con **{puntos_totales:,} puntos** puedes canjear "
            f"**{noches_posibles} noche(s)** en un hotel "
            f"**Categoría {categoria} ({temporada})**."
        )

    # =====================================================
    # TAB 2: VALOR POR DÓLAR — PRO
    # =====================================================
    with tab2:
        st.subheader("💡 Valor real por cada $1 USD")
        st.caption("Comparación clara del retorno según nivel Hyatt")

        niveles_valor = [
            ("Member", 5.0),
            ("Discoverist", 5.0),
            ("Explorist", 6.0),
            ("Globalist", 6.5),
        ]

        for nombre, pts in niveles_valor:
            pts_reales = pts * 1.15
            col1, col2 = st.columns([2,1])

            with col1:
                st.write(f"### {nombre}")
                st.write(f"Puntos base por dólar: **{pts}**")
                st.write("Bonus promedio Inclusive: **+15%**")

            with col2:
                st.metric("Pts reales / USD", f"{pts_reales:.2f}")

            st.divider()

        st.info(
            f"💼 **Lectura ejecutiva:** con nivel **{nivel.split('(')[0].strip()}**, "
            f"cada $1 USD genera aprox. **{pts_por_dolar * 1.15:.2f} puntos reales**. "
            "Subir de nivel incrementa el retorno sin aumentar el gasto."
        )
