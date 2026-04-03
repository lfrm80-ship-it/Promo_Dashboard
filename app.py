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
# VISTA RÁPIDA (PRO)
# =============================
if menu == "Vista rápida":

    if df.empty:
        st.info("No hay promociones registradas.")
    else:
        df = df.copy()
        df["Estado"] = df.apply(estado, axis=1)

        # -------- FILTROS --------
        f1, f2, f3, f4 = st.columns(4)

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
            filtro_ota = st.multiselect(
                "OTA",
                sorted(df["OTA"].dropna().unique())
            )
        with f4:
            filtro_market = st.multiselect(
                "Market",
                sorted(df["Market"].dropna().unique())
            )

        df_view = df.copy()
        if filtro_estado:
            df_view = df_view[df_view["Estado"].isin(filtro_estado)]
        if filtro_hotel:
            df_view = df_view[df_view["Hotel"].isin(filtro_hotel)]
        if filtro_ota:
            df_view = df_view[df_view["OTA"].isin(filtro_ota)]
        if filtro_market:
            df_view = df_view[df_view["Market"].isin(filtro_market)]

        if not st.session_state.is_admin:
            df_view = df_view[df_view["Estado"] == "Activa"]

        if df_view.empty:
            st.warning("No hay promociones con los filtros seleccionados.")
        else:
            # -------- ORDEN DE COLUMNAS --------
            columnas = [
                "Hotel","OTA","Promo","Market","Rate_Plan","Descuento",
                "BW_Inicio","BW_Fin","TW_Inicio","TW_Fin","Estado"
            ]
            columnas = [c for c in columnas if c in df_view.columns]

            st.dataframe(
                df_view[columnas],
                use_container_width=True,
                hide_index=True
            )

            st.download_button(
                "📥 Descargar Excel",
                data=generar_excel(df_view[columnas]),
                file_name=f"MasterRecord_{date.today()}.xlsx"
            )

            # -------- TESTIGOS / PREVIEW --------
            st.divider()
            st.markdown("### 📎 Testigos / Material adjunto")

            for idx, row in df_view.iterrows():
                link = row.get("Archivo_Path")
                if isinstance(link, str) and link:
                    st.markdown(
                        f"**{row['Promo']}** · {row['Hotel']} · {row['OTA']}"
                    )

                    if any(ext in link.lower() for ext in [".png", ".jpg", ".jpeg"]):
                        st.image(link, width=300)

                    elif ".pdf" in link.lower():
                        st.markdown(f"[📄 Ver PDF]({link})")

                    st.link_button(
                        "⬇️ Descargar archivo",
                        link,
                        key=f"file_{idx}"
                    )

# =============================
# NUEVA PROMOCIÓN
# =============================
if menu == "Nueva promoción":

    with st.form("new_promo", clear_on_submit=True):

        # -------- PROMO / HOTEL / RATE --------
        c1, c2 = st.columns(2)

        with c1:
            promo = st.text_input("Promoción *")
            hotels = st.multiselect("Hotel *", ["DREPM", "SECPM"])

        with c2:
            rate = st.text_input("Rate Plan *")
            discount = st.number_input("Descuento (%)", 0, 100, step=1)

        st.divider()

        # -------- OTA / MARKET + FECHAS (PRO) --------
        left, right = st.columns([1.1, 2.6])

        with left:
            ota = st.selectbox("OTA *", ["Direct", "Booking", "Expedia"])
            market = st.selectbox("Market", ["USA", "CAN", "MEX", "LATAM", "EUR", "Worldwide"])

        with right:
            h1, h2, h3, h4 = st.columns(4)
            with h1: st.caption("BW IN")
            with h2: st.caption("BW FIN")
            with h3: st.caption("TW IN")
            with h4: st.caption("TW FIN")

            i1, i2, i3, i4 = st.columns(4)
            with i1: bw_i = st.date_input("", value=None, label_visibility="collapsed", key="bw_i")
            with i2: bw_f = st.date_input("", value=None, label_visibility="collapsed", key="bw_f")
            with i3: tw_i = st.date_input("", value=None, label_visibility="collapsed", key="tw_i")
            with i4: tw_f = st.date_input("", value=None, label_visibility="collapsed", key="tw_f")

        st.divider()

        archivo = st.file_uploader(
            "Archivo (PNG, JPG, PDF, XLS, XLSX)",
            ["png", "jpg", "jpeg", "pdf", "xls", "xlsx"]
        )

        notas = st.text_area("Notas / Restricciones")

        # ✅ EL SUBMIT ES LO ÚLTIMO (CRÍTICO)
        submit = st.form_submit_button("✅ Registrar promoción")

        if submit:
            for h in hotels:
                payload = {
                    "Hotel": h,
                    "OTA": ota,
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

                r = requests.post(WEB_APP_URL, data=json.dumps(payload))
                if r.status_code != 200:
                    st.error("Error al guardar promoción")
                    st.stop()

            st.success("✅ Promoción guardada correctamente")
            st.rerun()
