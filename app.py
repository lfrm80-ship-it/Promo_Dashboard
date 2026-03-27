import streamlit as st
import pandas as pd
import os, io, time
from datetime import date, datetime

# =====================================================
# CONFIGURACIÓN GENERAL
# =====================================================
st.set_page_config(page_title="Administrador de Promociones", layout="wide")

CSV_FILE = "promociones_data.csv"
MEDIA_DIR = "media"
PASSWORD_MAESTRA = "PlayaMujeres2026"

MARKETS = ["US", "Canada", "Mexico", "LATAM", "Europe", "Asia / ROW"]
PROPERTIES = ["DREPM - Dreams Playa Mujeres", "SECPM - Secrets Playa Mujeres"]

os.makedirs(MEDIA_DIR, exist_ok=True)

# =====================================================
# CSS
# =====================================================
st.markdown("""
<style>
body { background-color: #f7f8fa; }
.block-container { padding-top: 1rem; }
div[data-baseweb="tab-list"] { justify-content: center; }
button[data-baseweb="tab"][aria-selected="true"] { font-weight: 600; }
div[data-testid="stVerticalBlock"] { gap: 0.5rem; }
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
# HELPERS
# =====================================================
def normalizar_market(x):
    if isinstance(x, list): return x
    if isinstance(x, str):
        x = x.replace("[", "").replace("]", "").replace("'", "")
        return [m.strip() for m in x.split("|") if m.strip()]
    return []

def cargar_datos():
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        for c in ["BW_Inicio","BW_Fin","TW_Inicio","TW_Fin"]:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c]).dt.date
        for col in ["Market","Archivo_Path"]:
            if col not in df.columns:
                df[col] = ""
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
            lambda x: os.path.basename(x) if isinstance(x,str) and x else ""
        )
        df_x.drop(columns=["Archivo_Path"], inplace=True)
        df_x.to_excel(writer, index=False, startrow=4)
        for i in range(len(df_x.columns)):
            ws.set_column(i, i, 18)
    buffer.seek(0)
    return buffer



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

# =====================================================
# PROMOCIONES
# =====================================================
with tab_promos:
    df = cargar_datos()
    if df.empty:
        st.info("No hay promociones registradas.")
    else:
        search = st.text_input(
            "🔍 Buscar promoción",
            placeholder="Nombre, Rate Plan, Market, Hotel, Notas..."
        )

        df_filtrado = df.copy()
        if search:
            mask = (
                df_filtrado["Promo"].astype(str).str.contains(search, case=False, na=False)
                | df_filtrado["Notas"].astype(str).str.contains(search, case=False, na=False)
                | df_filtrado["Rate_Plan"].astype(str).str.contains(search, case=False, na=False)
                | df_filtrado["Hotel"].astype(str).str.contains(search, case=False, na=False)
                | df_filtrado["Market"].apply(lambda x: ", ".join(x)).str.contains(search, case=False, na=False)
            )
            df_filtrado = df_filtrado[mask]

        view = df_filtrado.copy()
        view["Market"] = view["Market"].apply(lambda x: ", ".join(x))
        view["Descuento"] = view["Descuento"].apply(lambda x: f"{int(x)} %")
        st.dataframe(view, use_container_width=True)

        st.subheader("Estado y Vigencia de Promociones")

        filtro = st.radio(
            "Mostrar:",
            ["Todas", "🟢 Activas", "🟡 Por iniciar", "🔴 Expiradas"],
            horizontal=True
        )

        hoy = date.today()

        for _, row in df_filtrado.iterrows():
            tw_ini, tw_fin = row["TW_Inicio"], row["TW_Fin"]
            if hoy < tw_ini:
                estado, avance = "🟡 Por iniciar", 0
            elif hoy > tw_fin:
                estado, avance = "🔴 Expirada", 100
            else:
                estado = "🟢 Activa"
                total = max((tw_fin - tw_ini).days, 1)
                avance = int((hoy - tw_ini).days / total * 100)

            if filtro != "Todas" and estado != filtro:
                continue

            with st.expander(f"{estado} | {row['Promo']} | {row['Hotel']} | {row['Rate_Plan']}"):
                st.progress(avance)
                st.caption(f"Travel Window: {tw_ini} → {tw_fin} ({avance} %)")
                path = row["Archivo_Path"]
                if (
                    isinstance(path, str)
                    and path.lower().endswith((".png",".jpg",".jpeg"))
                    and os.path.exists(path)
                ):
                    st.image(path, width=400)

        st.download_button("Descargar Excel", exportar_excel(df), file_name="Promociones.xlsx")

        # 🔒 ACCESO ADMINISTRADOR SOLO AQUÍ
        if not st.session_state.is_admin:
            st.markdown("---")
            with st.expander("🔒 Acceso administrador"):
                clave = st.text_input("Clave Administrador", type="password", key="admin_password")
                if clave == PASSWORD_MAESTRA:
                    st.session_state.is_admin = True
                    st.success("Acceso administrador habilitado")
                    st.rerun()

# =====================================================
# REGISTRAR / MODIFICAR (RESTAURADO ✅)
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
        st.subheader("Registrar / Modificar Promoción")

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
