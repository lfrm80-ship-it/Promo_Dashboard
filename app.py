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

        # ---------- BUSCADOR ----------
        search = st.text_input(
            "Buscar (Promoción, Hotel o Market)",
            placeholder="Ej. Summer Sale, DREPM, USA"
        )

        # ---------- FILTROS ----------
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

        # ---------- APLICAR FILTROS ----------
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
            # ---------- TABLA ----------
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

            # ---------- EXCEL ----------
            st.download_button(
                "Descargar Excel",
                data=generar_excel(df_view[columnas]),
                file_name=f"MasterRecord_{date.today()}.xlsx"
            )

            # ---------- TESTIGOS / MATERIAL ADJUNTO ----------
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

            if archivo is not None:
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
                    payload["FileName"] = file_name
                    payload["FileType"] = file_type
                    payload["FileContent"] = file_content

                r = requests.post(
                    WEB_APP_URL,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )

                st.write("Status:", r.status_code)
                st.write("Respuesta:", r.text)

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
# WORLD OF HYATT
# =========================================================
if menu == "World of Hyatt":
    st.markdown("## 🌟 World of Hyatt")
    st.markdown("---")

    # ---- CALCULADORA WOH ----
    st.markdown("### 🧮 Calculadora de Puntos WOH")

    calc1, calc2, calc3 = st.columns(3)

    with calc1:
        noches = st.number_input("Número de noches", min_value=1, max_value=30, value=7, step=1)

    with calc2:
        tarifa = st.number_input("Tarifa por noche (USD)", min_value=100, max_value=5000, value=500, step=50)

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
    pts_por_dolar = pts_map[nivel]
    gasto_total = noches * tarifa
    puntos_base = gasto_total * pts_por_dolar
    puntos_bonus = puntos_base * 0.15
    puntos_total = int(puntos_base + puntos_bonus)
    noches_gratis = puntos_total // 3500

    st.markdown("---")
    r1, r2, r3, r4 = st.columns(4)
    with r1:
        st.metric("💰 Gasto total", f"${gasto_total:,.0f} USD")
    with r2:
        st.metric("⭐ Puntos base", f"{int(puntos_base):,}")
    with r3:
        st.metric("🎁 Bonus Inclusive (15%)", f"{int(puntos_bonus):,}")
    with r4:
        st.metric("🏆 Total puntos", f"{puntos_total:,}")

    st.success(f"🌙 Con {puntos_total:,} puntos puedes canjear aproximadamente **{noches_gratis} noche(s) gratis** en propiedades Category 1.")

    # ---- VALOR POR DÓLAR ----
    st.markdown("---")
    st.markdown("### 💡 ¿Cuánto vale cada dólar gastado?")

    v1, v2, v3, v4 = st.columns(4)

    with v1:
        st.markdown(
            "<div style='background:#1e1e2e;border-radius:12px;padding:20px;text-align:center;'>"
            "<div style='font-size:2em;'>🔵</div>"
            "<div style='color:#aaa;font-size:0.85em;margin-top:4px;'>Member</div>"
            "<div style='color:white;font-size:2em;font-weight:bold;'>5 pts</div>"
            "<div style='color:#aaa;font-size:0.8em;'>por cada $1 USD</div>"
            "</div>",
            unsafe_allow_html=True)

    with v2:
        st.markdown(
            "<div style='background:#1e1e2e;border-radius:12px;padding:20px;text-align:center;'>"
            "<div style='font-size:2em;'>🟤</div>"
            "<div style='color:#aaa;font-size:0.85em;margin-top:4px;'>Discoverist</div>"
            "<div style='color:white;font-size:2em;font-weight:bold;'>5 pts</div>"
            "<div style='color:#aaa;font-size:0.8em;'>por cada $1 USD</div>"
            "</div>",
            unsafe_allow_html=True)

    with v3:
        st.markdown(
            "<div style='background:#1e1e2e;border-radius:12px;padding:20px;text-align:center;'>"
            "<div style='font-size:2em;'>🔘</div>"
            "<div style='color:#aaa;font-size:0.85em;margin-top:4px;'>Explorist</div>"
            "<div style='color:#4fc3f7;font-size:2em;font-weight:bold;'>6 pts</div>"
            "<div style='color:#aaa;font-size:0.8em;'>por cada $1 USD</div>"
            "</div>",
            unsafe_allow_html=True)

    with v4:
        st.markdown(
            "<div style='background:#1a3c5e;border:2px solid #f0c040;border-radius:12px;padding:20px;text-align:center;'>"
            "<div style='font-size:2em;'>🟡</div>"
            "<div style='color:#f0c040;font-size:0.85em;margin-top:4px;'>Globalist</div>"
            "<div style='color:#f0c040;font-size:2em;font-weight:bold;'>6.5 pts</div>"
            "<div style='color:#cce0ff;font-size:0.8em;'>por cada $1 USD</div>"
            "</div>",
            unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='background:#0d2137;border-radius:12px;padding:16px 24px;text-align:center;'>"
        f"<span style='color:#aaa;'>Con tu nivel </span>"
        f"<span style='color:#f0c040;font-weight:bold;'>{nivel.split('(')[0].strip()}</span>"
        f"<span style='color:#aaa;'>, cada </span>"
        f"<span style='color:white;font-weight:bold;'>$1 USD</span>"
        f"<span style='color:#aaa;'> gastado te genera </span>"
        f"<span style='color:#4fc3f7;font-size:1.3em;font-weight:bold;'>{pts_por_dolar} pts</span>"
        f"<span style='color:#aaa;'> + </span>"
        f"<span style='color:#81c995;font-weight:bold;'>15% bonus Inclusive Collection</span>"
        f"<span style='color:#aaa;'> = </span>"
        f"<span style='color:white;font-size:1.3em;font-weight:bold;'>{pts_por_dolar * 1.15:.2f} pts reales</span>"
        f"</div>",
        unsafe_allow_html=True)

    # ---- TABLA DE NIVELES ----
    st.markdown("---")
    st.markdown("### 📊 Tu nivel actual")

    niveles = [
        {"nivel": "🔵 Member",      "noches": "0",  "pts": 5,   "beneficios": "Acceso básico"},
        {"nivel": "🟤 Discoverist", "noches": "10", "pts": 5,   "beneficios": "Late checkout 2PM"},
        {"nivel": "🔘 Explorist",   "noches": "30", "pts": 6,   "beneficios": "Suite upgrades, lounge access"},
        {"nivel": "🟡 Globalist",   "noches": "60", "pts": 6.5, "beneficios": "Suite upgrades, desayuno, late checkout 4PM"},
    ]

    nivel_actual = nivel.split(" ")[0]

    for n in niveles:
        nombre = n["nivel"].split(" ")[1]
        pts_estadia = int(gasto_total * n["pts"] * 1.15)
        es_actual = nombre == nivel_actual

        if es_actual:
            st.markdown(
                f"<div style='background:#1a3c5e;border-left:6px solid #f0c040;border-radius:10px;padding:16px 20px;margin-bottom:10px;'>"
                f"<span style='font-size:1.2em;font-weight:bold;color:#f0c040;'>{n['nivel']} ← Tu nivel actual</span><br>"
                f"<span style='color:#cce0ff;'>📅 Noches requeridas: {n['noches']} &nbsp;|&nbsp; "
                f"⭐ {n['pts']} pts/$ &nbsp;|&nbsp; "
                f"🏆 {pts_estadia:,} pts en tu estadía &nbsp;|&nbsp; "
                f"✅ {n['beneficios']}</span>"
                f"</div>",
                unsafe_allow_html=True)
        else:
            st.markdown(
                f"<div style='background:#1e1e2e;border-left:6px solid #444;border-radius:10px;padding:12px 20px;margin-bottom:10px;opacity:0.75;'>"
                f"<span style='font-size:1em;font-weight:bold;color:#aaa;'>{n['nivel']}</span><br>"
                f"<span style='color:#888;'>📅 Noches requeridas: {n['noches']} &nbsp;|&nbsp; "
                f"⭐ {n['pts']} pts/$ &nbsp;|&nbsp; "
                f"🏆 {pts_estadia:,} pts en tu estadía &nbsp;|&nbsp; "
                f"✅ {n['beneficios']}</span>"
                f"</div>",
                unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 💎 Beneficios Globalist")
    st.markdown(
        "- ✅ Upgrade a suite (sujeto a disponibilidad)\n"
        "- ✅ Late check-out a las 4:00 PM\n"
        "- ✅ Early check-in sujeto a disponibilidad\n"
        "- ✅ Desayuno de cortesía (propiedades select)\n"
        "- ✅ Puntos de bonificación (30% extra)\n"
        "- ✅ Club lounge access\n"
        "- ✅ Guest of Honor (transferir estatus)"
    )

    st.info("Para más información visita [world.hyatt.com](https://world.hyatt.com)", icon="🌐")
