import streamlit as st
import pandas as pd
import io, json, time, base64, requests
from datetime import date

# =============================
# CONFIGURACIÓN
# =============================
st.set_page_config(
    page_title="Master Record Playa Mujeres",
    layout="wide"
)

ADMIN_PASSWORD = st.secrets["admin_password"]
WEB_APP_URL = st.secrets["apps_script_url"]

SHEET_ID = "1dvYqQFpI7VqJFuOLeyqQdb2GijFrhoFrNrpWidakAq4"
WORKSHEET = "promociones"

# =============================
# UTILIDADES
# =============================
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

    for c in ["BW_Inicio","BW_Fin","TW_Inicio","TW_Fin"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce").dt.date

    return df

def estado(row):
    if pd.isna(row["TW_Inicio"]) or pd.isna(row["TW_Fin"]):
        return "Expirada"
    if row["TW_Inicio"] <= date.today() <= row["TW_Fin"]:
        return "Activa"
    return "Futura"

def generar_excel(df):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False)
    buffer.seek(0)
    return buffer.getvalue()

# =============================
# SESSION STATE
# =============================
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# =============================
# SIDEBAR
# =============================
with st.sidebar:
    st.image("HIC.png", use_container_width=True)
    menu = st.radio(
        "Navegación",
        ["Vista rápida"] + (["Nueva promoción"] if st.session_state.is_admin else [])
    )

    with st.expander("🔒 Admin"):
        pwd = st.text_input("Password", type="password")
        if st.button("Entrar") and pwd == ADMIN_PASSWORD:
            st.session_state.is_admin = True
            st.rerun()

# =============================
# DATA
# =============================
df = cargar_df()

st.markdown("## 📊 Master Record Playa Mujeres")

# =============================
# VISTA RÁPIDA
# =============================
if menu == "Vista rápida":

    if df.empty:
        st.info("No hay promociones registradas.")
    else:
        df = df.copy()
        df["Estado"] = df.apply(estado, axis=1)

        # ---------- BUSCADOR ----------
        search = st.text_input(
            "🔎 Buscar (Promoción, Hotel o Market)",
            placeholder="Ej. Summer Sale, DREPM, USA…"
        )

        # ---------- FILTROS ----------
        f1, f2, f3 = st.columns(3)

        with f1:
            filtro_estado = st.multiselect(
                "Estado",
                ["Activa", "Futura", "Expirada"],
                default=["Activa"]
            )

        with f2:
            filtro_hotel = st.multiselect(
                "Hotel",
                sorted(df["Hotel"].dropna().unique())
            )

        with f3:
            filtro_market = st.multiselect(
                "Market",
                sorted(df["Market"].dropna().unique())
            )

        # ---------- APLICAR FILTROS ----------
        df_view = df.copy()

        if filtro_estado:
            df_view = df_view[df_view["Estado"].isin(filtro_estado)]

        if filtro_hotel:
            df_view = df_view[df_view["Hotel"].isin(filtro_hotel)]

        if filtro_market:
            df_view = df_view[df_view["Market"].isin(filtro_market)]

        # ---------- BUSQUEDA TEXTO ----------
        if search:
            search_l = search.lower()
            df_view = df_view[
                df_view["Promo"].str.lower().str.contains(search_l, na=False)
                | df_view["Hotel"].str.lower().str.contains(search_l, na=False)
                | df_view["Market"].str.lower().str.contains(search_l, na=False)
            ]

        # ---------- USUARIO NO ADMIN ----------
        if not st.session_state.is_admin:
            df_view = df_view[df_view["Estado"] == "Activa"]

        if df_view.empty:
            st.warning("No hay promociones con los filtros actuales.")
        else:
            # ---------- TABLA ----------
            columnas = [
                "Hotel",
                "Promo",
                "Market",
                "Rate_Plan",
                "Descuento",
                "BW_Inicio",
                "BW_Fin",
                "TW_Inicio",
                "TW_Fin",
                "Estado",
            ]
            columnas = [c for c in columnas if c in df_view.columns]

            st.dataframe(
                df_view[columnas],
                use_container_width=True,
                hide_index=True
            )

            # ---------- DESCARGA EXCEL ----------
            st.download_button(
                "📥 Descargar Excel",
                data=generar_excel(df_view[columnas]),
                file_name=f"MasterRecord_{date.today()}.xlsx"
            )

            # ---------- TESTIGOS / ADJUNTOS ----------
            st.divider()
            st.markdown("### 📎 Testigos / Material adjunto")

            for idx, row in df_view.iterrows():
                link = row.get("Archivo_Path")

                if isinstance(link, str) and link.strip() != "":
                    st.markdown(
                        f"**{row['Promo']}**  \n"
                        f"{row['Hotel']} · {row['Market']}"
                    )

                    # Preview imagen
                    if any(ext in link.lower() for ext in [".png", ".jpg", ".jpeg"]):
                        st.image(link, width=300)

                    # PDF: link clicable (Drive maneja visor)
                    elif ".pdf" in link.lower():
                        st.markdown(f"[📄 Ver PDF]({link})")

                    st.link_button(
                        "⬇️ Ver / Descargar archivo",
                        link,
                        key=f"file_{idx}"
                    )

# =============================
# NUEVA PROMOCIÓN
# =============================
if menu == "Nueva promoción":

    with st.form("new_promo", clear_on_submit=True):

        # -------- PROMOCIÓN / HOTEL / RATE --------
        col1, col2 = st.columns(2)

        with col1:
            promo = st.text_input("Promoción *")
            hotels = st.multiselect("Hotel *", ["DREPM", "SECPM"])

        with col2:
            rate = st.text_input("Rate Plan *")
            discount = st.number_input("Descuento (%)", 0, 100, step=1)

        st.divider()

        # -------- MARKET --------
        market = st.selectbox(
            "Market *",
            ["USA", "CAN", "MEX", "LATAM", "EUR", "Worldwide"]
        )

        st.divider()

        # -------- BOOKING & TRAVEL WINDOW --------
        st.markdown("**Booking & Travel Window**")

        label_cols = st.columns(4)
        label_cols[0].caption("BW IN")
        label_cols[1].caption("BW FIN")
        label_cols[2].caption("TW IN")
        label_cols[3].caption("TW FIN")

        input_cols = st.columns(4)
        bw_i = input_cols[0].date_input("", value=None, label_visibility="collapsed", key="bw_i")
        bw_f = input_cols[1].date_input("", value=None, label_visibility="collapsed", key="bw_f")
        tw_i = input_cols[2].date_input("", value=None, label_visibility="collapsed", key="tw_i")
        tw_f = input_cols[3].date_input("", value=None, label_visibility="collapsed", key="tw_f")

        st.divider()

        archivo = st.file_uploader(
            "Archivo (PNG, JPG, PDF, XLS, XLSX)",
            ["png", "jpg", "jpeg", "pdf", "xls", "xlsx"]
        )

        notas = st.text_area("Notas / Restricciones")

        # ✅ SUBMIT (DEBE SER LO ÚLTIMO)
        submit = st.form_submit_button("✅ Registrar promoción")

        if submit:
            for h in hotels:
                payload = {
                    "Hotel": h,
                    "Promo": promo,
                    "Market": market,
                    "Rate_Plan": rate,
                    "Descuento": discount,
                    "BW_Inicio": str(bw_i or ""),
                    "BW_Fin": str(bw_f or ""),
                    "TW_Inicio": str(tw_i or ""),
                    "TW_Fin": str(tw_f or ""),
                    "Notas": notas
                }

                if archivo:
                    payload["FileName"] = archivo.name
                    payload["FileType"] = archivo.type
                    payload["FileContent"] = base64.b64encode(
                        archivo.getvalue()
                    ).decode()

                response = requests.post(
                    WEB_APP_URL,
                    data=json.dumps(payload)
                )

                if response.status_code != 200:
                    st.error("Error al guardar promoción")
                    st.stop()

            st.success("✅ Promoción guardada correctamente")
            st.rerun()
