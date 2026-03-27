import streamlit as st
import pandas as pd
import os
import io
import time
from datetime import date, datetime

# =====================================================
# CONFIGURACIÓN GENERAL
# =====================================================
st.set_page_config(page_title="Administrador de Promociones", layout="wide")

CSV_FILE = "promociones_data.csv"
MEDIA_DIR = "media"
PASSWORD_MAESTRA = "PlayaMujeres2026"

MARKETS = ["US", "Canada", "Mexico", "LATAM", "Europe", "Asia / ROW"]
PROPERTIES = [
    "DREPM - Dreams Playa Mujeres",
    "SECPM - Secrets Playa Mujeres"
]

os.makedirs(MEDIA_DIR, exist_ok=True)

# =====================================================
# CSS BASE
# =====================================================
st.markdown("""
<style>
body { background-color: #f7f8fa; }
.block-container { padding-top: 0.8rem; }
div[data-baseweb="tab-list"] { justify-content: center; }
button[data-baseweb="tab"][aria-selected="true"] {
    font-weight: 600;
    border-bottom: 2px solid #ff4b4b;
}
div[data-testid="stVerticalBlock"] { gap: 0.4rem; }
</style>
""", unsafe_allow_html=True)

# =====================================================
# SESSION STATE
# =====================================================
defaults = {
    "promo": "",
    "descuento": 0,
    "bw": (date.today(), date.today()),
    "tw": (date.today(), date.today()),
    "rate_raw": "",
    "hoteles": [],
    "markets": [],
    "notas": "",
    "reset_form": False,
    "is_admin": False
}
for k, v in defaults.items():
    st.session_state.setdefault(k, v)

# =====================================================
# FUNCIONES AUXILIARES
# =====================================================
def normalizar_market(x):
    if isinstance(x, list):
        return x
    if isinstance(x, str):
        x = x.replace("[", "").replace("]", "").replace("'", "")
        return [m.strip() for m in x.split("|") if m.strip()]
    return []

def cargar_datos():
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)

        for c in ["BW_Inicio", "BW_Fin", "TW_Inicio", "TW_Fin"]:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c]).dt.date

        if "Market" not in df.columns:
            df["Market"] = ""
        if "Archivo_Path" not in df.columns:
            df["Archivo_Path"] = ""

        df["Market"] = df["Market"].apply(normalizar_market)
        return df

    return pd.DataFrame(columns=[
        "Hotel","Market","Promo","Rate_Plan","Descuento",
        "BW_Inicio","BW_Fin","TW_Inicio","TW_Fin",
        "Notas","Archivo_Path"
    ])

def exportar_excel(df):
    buffer = io.BytesIO()
    fecha = datetime.now().strftime("%Y-%m-%d")

    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        ws = writer.book.add_worksheet("Promociones")
        writer.sheets["Promociones"] = ws

        ws.write("E2", "Fecha de generación:")
        ws.write("F2", fecha)

        df_x = df.copy()
        df_x["Market"] = df_x["Market"].apply(lambda x: ", ".join(x))
        df_x["Archivo_Respaldo"] = df_x["Archivo_Path"].apply(
            lambda x: os.path.basename(x) if isinstance(x, str) and x else ""
        )
        df_x.drop(columns=["Archivo_Path"], inplace=True)

        df_x.to_excel(writer, index=False, startrow=4)
        for i in range(len(df_x.columns)):
            ws.set_column(i, i, 18)

    buffer.seek(0)
    return buffer

# =====================================================
# HEADER FINAL – TEXTO CENTRADO, SIN IMAGEN
# =====================================================

# Espacio superior natural
st.markdown("")

# Título centrado (sin íconos ni saltos)
st.markdown(
    "<h1 style='text-align:center; margin-bottom:6px;'>"
    "Administrador de Promociones"
    "</h1>",
    unsafe_allow_html=True
)

# Subtítulo centrado
st.markdown(
    "<div style='text-align:center; color:#6b6b6b; font-size:14px;'>"
    "Playa Mujeres – DREPM &amp; SECPM"
    "</div>",
    unsafe_allow_html=True
)

# Línea divisoria estable
st.divider()

# =====================================================
# TABS (ADMIN CONDICIONAL)
# =====================================================
tab_names = ["Promociones", "Registrar / Modificar"]
if st.session_state.is_admin:
    tab_names.append("Administración")

tabs = st.tabs(tab_names)
tab_promos = tabs[0]
tab_registro = tabs[1]
if st.session_state.is_admin:
    tab_admin = tabs[2]

with tab_promos:

    df = cargar_datos()
    df_prod = cargar_produccion()
    hoy = date.today()

    if df.empty:
        st.info("No hay promociones registradas.")
    else:
        # =========================
        # BUSCADOR
        # =========================
        search = st.text_input(
            "🔍 Buscar promoción",
            placeholder="Nombre, Rate Plan, Market, Hotel, Notas…"
        )

        df_f = df.copy()
        if search:
            mask = (
                df_f["Promo"].astype(str).str.contains(search, case=False, na=False)
                | df_f["Notas"].astype(str).str.contains(search, case=False, na=False)
                | df_f["Rate_Plan"].astype(str).str.contains(search, case=False, na=False)
                | df_f["Hotel"].astype(str).str.contains(search, case=False, na=False)
                | df_f["Market"].apply(lambda x: ", ".join(x)).str.contains(search, case=False, na=False)
            )
            df_f = df_f[mask]

        # =========================
        # TABLA OPERATIVA
        # =========================
        view = df_f.copy()
        view["Market"] = view["Market"].apply(lambda x: ", ".join(x))
        view["Descuento"] = view["Descuento"].apply(lambda x: f"{int(x)} %")

        st.dataframe(view, use_container_width=True)

        st.subheader("Estado y Vigencia de Promociones")

        # =========================
        # FILTRO DE ESTADO
        # =========================
        filtro = st.radio(
            "Mostrar:",
            ["Todas", "🟢 Activas", "🟡 Por iniciar", "🔴 Expiradas"],
            horizontal=True
        )

        # =========================
        # LOOP PRINCIPAL
        # =========================
        for idx, row in df_f.iterrows():

            tw_ini = row["TW_Inicio"]
            tw_fin = row["TW_Fin"]

            # ---- Calcular estado ----
            if hoy < tw_ini:
                estado = "🟡 Por iniciar"
            elif hoy > tw_fin:
                estado = "🔴 Expirada"
            else:
                estado = "🟢 Activa"

            # ---- Aplicar filtro (CLAVE: misma indentación) ----
            if filtro != "Todas" and estado != filtro:
                continue

            # ---- Header de la promo ----
            with st.expander(f"{estado} | {row['Promo']} | {row['Hotel']} | {row['Rate_Plan']}"):
                st.caption(f"Travel Window: {tw_ini} → {tw_fin}")

                # =========================
                # PRODUCCIÓN SOLO EXPIRADAS
                # =========================
                if hoy > tw_fin:
                    prod = obtener_produccion(
                        df_prod,
                        row["Promo"],
                        row["Hotel"],
                        row["Rate_Plan"]
                    )

                    if prod is None:
                        st.markdown("### 📊 Agregar Producción")

                        rn = st.number_input(
                            "Room Nights",
                            min_value=0,
                            step=1,
                            key=f"rn_{idx}"
                        )
                        revenue = st.number_input(
                            "Revenue",
                            min_value=0.0,
                            step=1000.0,
                            key=f"rev_{idx}"
                        )
                        comentario = st.text_area(
                            "Comentario / Insight",
                            key=f"com_{idx}"
                        )

                        if st.button("Guardar Producción", key=f"save_prod_{idx}"):
                            nueva_fila = pd.DataFrame([{
                                "Promo": row["Promo"],
                                "Hotel": row["Hotel"],
                                "Rate_Plan": row["Rate_Plan"],
                                "Room_Nights": rn,
                                "Revenue": revenue,
                                "Comentario": comentario
                            }])

                            df_prod = pd.concat([df_prod, nueva_fila], ignore_index=True)
                            guardar_produccion(df_prod)

                            st.success("✅ Producción guardada correctamente")
                            st.rerun()

                    else:
                        st.success("✅ Producción cargada")
                        st.markdown(
                            f"""
                            - **Room Nights:** {int(prod["Room_Nights"])}
                            - **Revenue:** ${prod["Revenue"]:,.0f}
                            - **Insight:** {prod["Comentario"]}
                            """
                        )

        # =========================
        # DESCARGA EXCEL
        # =========================
        st.download_button(
            "Descargar Excel Operativo",
            exportar_excel(df),
            file_name="Promociones_Playa_Mujeres.xlsx"
        )

# =====================================================
# REGISTRAR / MODIFICAR
# =====================================================
with tab_registro:
    df = cargar_datos()

    if st.session_state.reset_form:
        for k in ["promo","rate_raw","notas"]:
            st.session_state[k] = ""
        st.session_state.descuento = 0
        st.session_state.hoteles = []
        st.session_state.markets = []
        st.session_state.bw = (date.today(), date.today())
        st.session_state.tw = (date.today(), date.today())
        st.session_state.reset_form = False

    with st.form("form_registro"):
        col1, col2 = st.columns([3,1])
        col1.text_input("Nombre de la promoción", key="promo")
        col2.number_input("Descuento (%)", 0, 100, 5, key="descuento")

        col_bw, col_tw = st.columns(2)
        col_bw.date_input("Booking Window", key="bw")
        col_tw.date_input("Travel Window", key="tw")

        st.text_area("Rate Plan(s) – uno por línea", height=90, key="rate_raw")

        col_p, col_m = st.columns(2)
        col_p.multiselect("Propiedad(es)", PROPERTIES, key="hoteles")
        col_m.multiselect("Market(s)", MARKETS, key="markets")

        st.text_area("Notas / Restricciones", height=80, key="notas")

        archivo = st.file_uploader("Archivo de respaldo", type=["png","jpg","jpeg","pdf"])
        guardar = st.form_submit_button("💾 Guardar")

        if guardar:
            rate_plans = [r.strip() for r in st.session_state.rate_raw.replace(",", "\n").split("\n") if r.strip()]

            if not rate_plans or not st.session_state.hoteles or not st.session_state.markets:
                st.error("Rate Plan, Market y Propiedad son obligatorios.")
            else:
                archivo_path = ""
                if archivo:
                    archivo_path = os.path.join(MEDIA_DIR, archivo.name)
                    with open(archivo_path, "wb") as f:
                        f.write(archivo.getbuffer())

                rows = []
                for rp in rate_plans:
                    for h in st.session_state.hoteles:
                        rows.append({
                            "Hotel": h,
                            "Market": "|".join(st.session_state.markets),
                            "Promo": st.session_state.promo,
                            "Rate_Plan": rp,
                            "Descuento": st.session_state.descuento,
                            "BW_Inicio": st.session_state.bw[0],
                            "BW_Fin": st.session_state.bw[1],
                            "TW_Inicio": st.session_state.tw[0],
                            "TW_Fin": st.session_state.tw[1],
                            "Notas": st.session_state.notas,
                            "Archivo_Path": archivo_path
                        })

                pd.concat([df, pd.DataFrame(rows)], ignore_index=True).to_csv(CSV_FILE, index=False)
                st.success("✅ Promoción guardada correctamente")
                st.session_state.reset_form = True
                time.sleep(1)
                st.rerun()

# =====================================================
# ADMINISTRACIÓN
# =====================================================
if st.session_state.is_admin:
    with tab_admin:
        st.subheader("Zona Administrativa")
        if st.button("🗑️ Borrar toda la base"):
            if os.path.exists(CSV_FILE):
                os.remove(CSV_FILE)
            st.warning("Base de datos eliminada")
            st.rerun()
