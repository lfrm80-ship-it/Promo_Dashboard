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
            "Archivo (PNG, JPG, PDF, XLS, XLSX)",
            ["png", "jpg", "jpeg", "pdf", "xls", "xlsx"]
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
    st.markdown("## Upsell")
    st.info("Sección en construcción 🚧")


# =========================================================
# WORLD OF HYATT ✅ CORREGIDO
# =========================================================
if menu == "World of Hyatt":

    st.markdown("## 🌟 World of Hyatt")
    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs(
        ["Calculadora", "Valor por dólar", "Niveles", "Beneficios"]
    )

    # ---------- TAB 1 ----------
    with tab1:
        st.markdown("### 🧮 Calculadora de Puntos WOH")

        calc1, calc2, calc3 = st.columns(3)
        with calc1:
            noches = st.number_input("Número de noches", 1, 30, 7)
        with calc2:
            tarifa = st.number_input("Tarifa por noche (USD)", 100, 5000, 500, step=50)
        with calc3:
            nivel = st.selectbox("Nivel de membresía", [
                "Member (5 pts/$)",
                "Discoverist (5 pts/$)",
                "Explorist (6 pts/$)",
                "Globalist (6.5 pts/$)"
            ])

        pts_map = {
            "Member (5 pts/$)": 5,
            "Discoverist (5 pts/$)": 5,
            "Explorist (6 pts/$)": 6,
            "Globalist (6.5 pts/$)": 6.5
        }

        pts = pts_map[nivel]
        gasto_total = noches * tarifa
        puntos_totales = int(gasto_total * pts * 1.15)

        st.metric("Gasto total", f"${gasto_total:,.0f}")
        st.metric("Puntos totales", f"{puntos_totales:,}")
        st.success(f"Aprox. {puntos_totales // 3500} noche(s) gratis")

    # ---------- TAB 2 ----------
    with tab2:
        st.markdown("### 💡 Valor por dólar")
        st.info(f"Cada $1 USD genera **{pts * 1.15:.2f} puntos reales**")

    # ---------- TAB 3 ----------
    with tab3:
        st.markdown("### 📊 Progreso de nivel")
        st.progress(min(noches / 60, 1.0))

    # ✅ ---------- TAB 4 (FIX REAL) ----------
    with tab4:
        st.markdown("### 💎 Beneficios Globalist")
        st.markdown(
            "- Suite upgrades\n"
            "- Desayuno incluido\n"
            "- Late check-out 4 PM\n"
            "- Guest of Honor\n"
            "- +30% bonus puntos"
        )
