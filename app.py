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
# WORLD OF HYATT — ACTUALIZADO A INFO OFICIAL
# Fuente: world.hyatt.com (Free Nights & Upgrades)
# =========================================================
if menu == "World of Hyatt":

    st.markdown("## 🌟 World of Hyatt")
    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs(
        ["Calculadora", "Valor por dólar", "Niveles", "Beneficios"]
    )

    # =====================================================
    # TAB 1: CALCULADORA REAL DE NOCHES
    # =====================================================
    with tab1:
        st.markdown("### 🧮 Calculadora de Puntos Hyatt")

        c1, c2, c3 = st.columns(3)

        with c1:
            noches = st.number_input("Noches de la estadía", 1, 30, 5)
            tarifa = st.number_input("Tarifa por noche (USD)", 100, 5000, 500, step=50)

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

        # ----- PUNTOS POR DÓLAR -----
        pts_map = {
            "Member (5 pts/$)": 5,
            "Discoverist (5 pts/$)": 5,
            "Explorist (6 pts/$)": 6,
            "Globalist (6.5 pts/$)": 6.5
        }
        pts_por_dolar = pts_map[nivel]

        # ----- TABLA OFICIAL HYATT (Standard Room) -----
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

        gasto_total = noches * tarifa
        puntos_base = gasto_total * pts_por_dolar
        puntos_con_bonus = int(puntos_base * 1.15)

        pts_noche = puntos_por_categoria[categoria][temporada]
        noches_posibles = puntos_con_bonus // pts_noche

        r1, r2, r3, r4 = st.columns(4)
        r1.metric("💰 Gasto total", f"${gasto_total:,.0f}")
        r2.metric("⭐ Puntos base", f"{int(puntos_base):,}")
        r3.metric("🎁 +15% Bonus", f"{int(puntos_con_bonus - puntos_base):,}")
        r4.metric("🏆 Total puntos", f"{puntos_con_bonus:,}")

        st.success(
            f"Con **{puntos_con_bonus:,} puntos** puedes canjear "
            f"**{noches_posibles} noche(s)** en un hotel **Categoría {categoria} ({temporada})**."
        )

# =====================================================
    # TAB 2: VALOR POR DÓLAR — MEGA PRO (FIX FINAL)
    # =====================================================
    with tab2:
        st.markdown("### 💡 Valor real por cada dólar gastado")
        st.caption(
            "Cálculo basado en earning oficial World of Hyatt "
            "+ bonus promedio Inclusive (+15%)"
        )

        niveles_valor = [
            {"nivel": "Member", "pts": 5.0, "color": "#9aa5b1"},
            {"nivel": "Discoverist", "pts": 5.0, "color": "#9aa5b1"},
            {"nivel": "Explorist", "pts": 6.0, "color": "#4fc3f7"},
            {"nivel": "Globalist", "pts": 6.5, "color": "#f0c040"},
        ]

        cols = st.columns(4)

        for i, n in enumerate(niveles_valor):
            pts_reales = n["pts"] * 1.15
            with cols[i]:
                st.markdown(
                    f"""
                    <div style="
                        background:#1e1e2e;
                        border-radius:14px;
                        padding:1.25rem;
                        border:1px solid #333;
                        text-align:center;
                        height:160px;
                    ">
                        <div style="font-size:13px;color:#aaa;">
                            {n['nivel']}
                        </div>
                        <div style="font-size:36px;font-weight:600;color:{n['color']};">
                            {pts_reales:.2f}
                        </div>
                        <div style="font-size:12px;color:#aaa;">
                            pts reales / USD
                        </div>
                        <div style="margin-top:6px;font-size:11px;color:#666;">
                            Base {n['pts']} + 15% bonus
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown(
            f"""
            <div style="
                background:#0d2137;
                border-radius:12px;
                padding:18px 22px;
                border-left:6px solid #4fc3f7;
            ">
                <div style="font-size:14px;color:#d0e4ff;">
                    💰 <strong>Lectura ejecutiva:</strong><br>
                    Un huésped <strong>{nivel.split('(')[0].strip()}</strong> obtiene
                    <strong>{pts_por_dolar * 1.15:.2f} puntos reales</strong>
                    por cada dólar gastado.<br>
                    Subir de nivel incrementa el valor por noche
                    <strong>sin pagar más</strong>.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.info(
            "Las noches con puntos no tienen blackout dates "
            "en habitaciones estándar (sujetas a disponibilidad)."
        )

    # =====================================================
    # TAB 3: NIVELES — PRO (FIX LIMPIO)
    # =====================================================
    with tab3:
        st.markdown("### 🏆 Progreso de Nivel World of Hyatt")
        st.caption("Calificación anual basada en noches elegibles")

        niveles = [
            {
                "nombre": "Member",
                "emoji": "🔵",
                "req": 0,
                "pts": 5,
                "beneficio": "Acceso básico al programa"
            },
            {
                "nombre": "Discoverist",
                "emoji": "🟤",
                "req": 10,
                "pts": 5,
                "beneficio": "Late check-out 2 PM"
            },
            {
                "nombre": "Explorist",
                "emoji": "🔘",
                "req": 30,
                "pts": 6,
                "beneficio": "Upgrades y lounge access"
            },
            {
                "nombre": "Globalist",
                "emoji": "🟡",
                "req": 60,
                "pts": 6.5,
                "beneficio": "Suites, desayuno y check-out 4 PM"
            },
        ]

        nivel_actual = nivel.split(" ")[0]

        for n in niveles:
            pts_estadia = int(gasto_total * n["pts"] * 1.15)
            es_actual = n["nombre"] == nivel_actual

            st.markdown(
                f"""
                <div style="
                    background:{'#1a3c5e' if es_actual else '#1e1e2e'};
                    border-left:6px solid {'#f0c040' if es_actual else '#444'};
                    border-radius:12px;
                    padding:16px 20px;
                    margin-bottom:12px;
                ">
                    <div style="font-size:15px;font-weight:600;color:white;">
                        {n['emoji']} {n['nombre']}
                        {" ← Tu nivel actual" if es_actual else ""}
                    </div>
                    <div style="font-size:12px;color:#ccc;margin-top:4px;">
                        🎯 {n['req']} noches calificadas · ⭐ {n['pts']} pts/USD
                    </div>
                    <div style="font-size:12px;color:#aaa;margin-top:6px;">
                        🏆 En esta estadía ganarías aprox.
                        <strong>{pts_estadia:,} puntos</strong><br>
                        💎 {n['beneficio']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
