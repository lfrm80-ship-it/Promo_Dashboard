import streamlit as st
import pandas as pd
import os
import io
from datetime import date

# =============================
# CONFIG
# =============================
st.set_page_config(page_title="Master Record Playa Mujeres", layout="wide")

ADMIN_PASSWORD = st.secrets.get("admin_password", "admin")

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

PROMOS_FILE = "promociones_produccion.csv"
MEDIA_DIR = "media"
os.makedirs(MEDIA_DIR, exist_ok=True)

PROPERTIES = [
    "DREPM - Dreams Playa Mujeres",
    "SECPM - Secrets Playa Mujeres"
]

MARKETS = ["USA", "CAN", "MEX", "LATAM", "EUR", "Worldwide"]

# =============================
# CSS
# =============================
st.markdown("""
<style>
.badge {
    padding: 4px 8px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 600;
    color: white;
}
.activa { background-color: #16a34a; }
.futura { background-color: #f59e0b; }
.expirada { background-color: #dc2626; }

.readonly {
    position: fixed;
    top: 90px;
    right: 22px;
    background: #f1f5f9;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# =============================
# HELPERS
# =============================
def cargar_promos():
    if os.path.exists(PROMOS_FILE):
        df = pd.read_csv(PROMOS_FILE)
        for c in ["BW_Inicio", "BW_Fin", "TW_Inicio", "TW_Fin"]:
            df[c] = pd.to_datetime(df[c]).dt.date
        return df
    return pd.DataFrame()

def generar_excel(df):
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False)
    return out.getvalue()

def calcular_status(row):
    hoy = date.today()
    if row["TW_Inicio"] <= hoy <= row["TW_Fin"]:
        return "Activa"
    elif hoy < row["TW_Inicio"]:
        return "Futura"
    else:
        return "Expirada"

# =============================
# SIDEBAR
# =============================
with st.sidebar:
    st.image("HIC.png", use_container_width=True)
    st.divider()

    menu = st.radio(
        "Navegación",
        ["🔍 Vista rápida"] + (
            ["📝 Editar promociones", "➕ Nueva promoción"]
            if st.session_state.is_admin else []
        )
    )

    st.divider()
    st.caption("Acceso administrativo")

    if st.session_state.is_admin:
        st.success("🟢 Modo ADMIN activo")
        if st.button("Salir de Admin"):
            st.session_state.is_admin = False
            st.rerun()
    else:
        with st.expander("🔒 Cambiar a Admin"):
            pwd = st.text_input("Contraseña", type="password")
            if st.button("Entrar"):
                if pwd == ADMIN_PASSWORD:
                    st.session_state.is_admin = True
                    st.rerun()
                else:
                    st.error("Contraseña incorrecta")

# =============================
# HEADER
# =============================
st.markdown("<h3 style='text-align:center;'>📊 Master Record Playa Mujeres</h3>", unsafe_allow_html=True)

if not st.session_state.is_admin:
    st.markdown("<div class='readonly'>READ ONLY</div>", unsafe_allow_html=True)

df = cargar_promos()

# =============================
# VISTA RÁPIDA
# =============================
if menu == "🔍 Vista rápida":

    if df.empty:
        st.info("No hay promociones registradas.")
    else:
        df["Estado"] = df.apply(calcular_status, axis=1)

        # 🔥 SEMÁFORO
        estados = ["Activa", "Futura", "Expirada"]
        default = ["Activa"] if not st.session_state.is_admin else estados

        filtro_estado = st.multiselect(
            "Estado de promoción",
            estados,
            default=default
        )

        df = df[df["Estado"].isin(filtro_estado)]

        search = st.text_input("Buscar…")

        mask = df.astype(str).apply(
            lambda x: x.str.contains(search, case=False, na=False)
        ).any(axis=1)

        st.dataframe(
            df[mask],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Estado": st.column_config.TextColumn(),
                "Archivo_Path": st.column_config.LinkColumn("Flyer / PDF")
            }
        )

        # 🔍 PREVIEW
        promo_sel = st.selectbox(
            "Vista previa",
            df[mask].index,
            format_func=lambda i: df.loc[i, "Promo"]
        )

        archivo = df.loc[promo_sel, "Archivo_Path"]

        if archivo and os.path.exists(archivo):
            if archivo.lower().endswith(".pdf"):
                st.markdown(
                    f"<iframe src='{archivo}' width='100%' height='600'></iframe>",
                    unsafe_allow_html=True
                )
            else:
                st.image(archivo, use_container_width=True)

# =============================
# NUEVA PROMO
# =============================
elif menu == "➕ Nueva promoción":

    with st.form("new", clear_on_submit=True):

        promo = st.text_input("Promoción *")
        hotels = st.multiselect("Hotel *", PROPERTIES)
        rate = st.text_input("Rate Plan *")
        discount = st.number_input("Descuento %", 0, 100)

        bw_i = st.date_input("BW Inicio")
        bw_f = st.date_input("BW Fin")
        tw_i = st.date_input("TW Inicio")
        tw_f = st.date_input("TW Fin")

        upload = st.file_uploader("Flyer / PDF", ["pdf", "png", "jpg", "jpeg"])
        notas = st.text_area("Notas")

        submit = st.form_submit_button("Registrar")

        if submit:
            if bw_f < bw_i or tw_f < tw_i:
                st.error("Fechas inválidas")
                st.stop()

            if not (bw_i <= tw_i <= bw_f and bw_i <= tw_f <= bw_f):
                st.error("TW debe estar dentro del BW")
                st.stop()

            file_path = ""
            if upload:
                file_path = os.path.join(MEDIA_DIR, upload.name)
                with open(file_path, "wb") as f:
                    f.write(upload.getbuffer())

            rows = [{
                "Hotel": h,
                "Promo": promo,
                "Rate_Plan": rate,
                "Descuento": discount,
                "BW_Inicio": bw_i,
                "BW_Fin": bw_f,
                "TW_Inicio": tw_i,
                "TW_Fin": tw_f,
                "Archivo_Path": file_path,
                "Notas": notas
            } for h in hotels]

            pd.concat([df, pd.DataFrame(rows)], ignore_index=True)\
              .to_csv(PROMOS_FILE, index=False)

            st.success("✅ Promoción registrada")
            st.rerun()
