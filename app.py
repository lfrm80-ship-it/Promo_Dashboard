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
PROPERTIES = [
    "DREPM - Dreams Playa Mujeres",
    "SECPM - Secrets Playa Mujeres"
]

os.makedirs(MEDIA_DIR, exist_ok=True)

# =====================================================
# CSS
# =====================================================
st.markdown("""
<style>
body { background-color: #f7f8fa; }
.block-container { padding-top: 0.9rem; }
div[data-baseweb="tab-list"] { justify-content: center; }
button[data-baseweb="tab"][aria-selected="true"] { font-weight: 600; }
div[data-testid="stVerticalBlock"] { gap: 0.4rem; }
</style>
""", unsafe_allow_html=True)

st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

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
    if isinstance(x, list):
        return x
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

    return pd.DataFrame(cols := [
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
# HEADER
# =====================================================
col1, col2, col3 = st.columns([1,1,6])
with col1:
    st.image("HIC.png", width=80)
with col3:
    st.markdown("## Administrador de Promociones")
    st.markdown(
        "<span style='color:#6b6b6b'>Playa Mujeres – DREPM & SECPM</span>",
        unsafe_allow_html=True
    )

st.markdown("<hr>", unsafe_allow_html=True)

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
            "🔍 Buscar promoción (Nombre, Notas, Rate Plan, Hotel o Market)",
            placeholder="Ej. ATFPROMOC, BAR, US, Blackout..."
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
                if isinstance(path, str) and path.lower().endswith((".png",".jpg",".jpeg")) and os.path.exists(path):
                    st.image(path, width=400)

        st.download_button(
            "Descargar Excel",
            exportar_excel(df),
            file_name="Promociones_Playa_Mujeres.xlsx"
        )

    # ✅ ACCESO ADMINISTRADOR — SOLO AQUÍ, AL FINAL
    if not st.session_state.is_admin:
        st.markdown("---")
        with st.expander("🔒 Acceso administrador"):
            clave = st.text_input("Clave Administrador", type="password", key="admin_password")
            if clave == PASSWORD_MAESTRA:
                st.session_state.is_admin = True
                st.success("Acceso administrador habilitado")
                st.rerun()

# =====================================================
# REGISTRAR / MODIFICAR
# =====================================================
with tab_registro:
    st.info("Formulario de registro (sin acceso admin aquí).")

# =====================================================
# ADMINISTRACIÓN (SOLO SI ADMIN)
# =====================================================
if st.session_state.is_admin:
    with tab_admin:
        st.subheader("Zona Administrativa")
        if st.button("🗑️ Borrar toda la base"):
            if os.path.exists(CSV_FILE):
                os.remove(CSV_FILE)
            st.warning("Base de datos eliminada")
            st.rerun()
