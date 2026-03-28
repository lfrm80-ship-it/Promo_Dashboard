import streamlit as st
import pandas as pd
import os
from datetime import date

# =============================
# CONFIGURACIÓN GENERAL
# =============================
st.set_page_config(page_title="Administrador de Promociones", layout="wide")

PROMOS_FILE = "promociones_data.csv"
PRODUCCION_FILE = "promociones_produccion.csv"

PROPERTIES = [
    "DREPM - Dreams Playa Mujeres",
    "SECPM - Secrets Playa Mujeres"
]

# =============================
# CSS – Tabs centrados
# =============================
st.markdown("""
<style>
div[data-baseweb="tab-list"] {
    justify-content: center;
}
</style>
""", unsafe_allow_html=True)

# =============================
# HELPERS
# =============================
def safe_read_csv(path):
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame()

def cargar_promos():
    df = safe_read_csv(PROMOS_FILE)
    if df.empty:
        return df

    for c in ["BW_Inicio","BW_Fin","TW_Inicio","TW_Fin"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c]).dt.date

    for col in ["Notas", "Descuento"]:
        if col not in df.columns:
            df[col] = ""

    return df

# =============================
# PRODUCCIÓN
# =============================
def cargar_produccion():
    df = safe_read_csv(PRODUCCION_FILE)
    if df.empty:
        return pd.DataFrame(columns=[
            "Promo","Hotel","Rate_Plan",
            "Room_Nights","Revenue","Comentario"
        ])
    return df

def guardar_produccion(df):
    df.to_csv(PRODUCCION_FILE, index=False)

def obtener_produccion(df, promo, hotel, rate):
    f = df[
        (df["Promo"] == promo) &
        (df["Hotel"] == hotel) &
        (df["Rate_Plan"] == rate)
    ]
    return f.iloc[0] if not f.empty else None

# =============================
# EXCEL
# =============================
def exportar_excel(df):
    archivo = "Promociones_Playa_Mujeres.xlsx"
    df.to_excel(archivo, index=False)
    return archivo

# =============================
# HEADER
# =============================
st.markdown("<h1 style='text-align:center;'>Administrador de Promociones</h1>", unsafe_allow_html=True)
st.markdown(
    "<div style='text-align:center;color:#6b6b6b;font-size:14px;'>"
    "Playa Mujeres – DREPM &amp; SECPM"
    "</div>",
    unsafe_allow_html=True
)
st.divider()

# =============================
# TABS PRINCIPALES
# =============================
tab_promos, tab_registro = st.tabs(["Promociones", "Registrar / Modificar"])

# =============================
# TAB PROMOCIONES
# =============================
with tab_promos:

    df = cargar_promos()
    df_prod = cargar_produccion()
    hoy = date.today()

    if df.empty:
        st.info("No hay promociones registradas.")
    else:
        search = st.text_input("🔍 Buscar promoción")
        df_f = df.copy()

        if search:
            mask = (
                df_f["Promo"].astype(str).str.contains(search, case=False, na=False)
                | df_f["Rate_Plan"].astype(str).str.contains(search, case=False, na=False)
                | df_f["Hotel"].astype(str).str.contains(search, case=False, na=False)
                | df_f["Notas"].astype(str).str.contains(search, case=False, na=False)
            )
            df_f = df_f[mask]

        st.subheader("Estado y Vigencia de Promociones")

        filtro = st.radio(
            "Mostrar:",
            ["Todas", "🟢 Activas", "🟡 Por iniciar", "🔴 Expiradas"],
            horizontal=True
        )

        for idx, row in df_f.iterrows():

            tw_ini, tw_fin = row["TW_Inicio"], row["TW_Fin"]

            if hoy < tw_ini:
                estado = "🟡 Por iniciar"
            elif hoy > tw_fin:
                estado = "🔴 Expirada"
            else:
                estado = "🟢 Activa"

            if filtro != "Todas" and estado != filtro:
                continue

            header = f"{estado} | {row['Promo']} | {row['Hotel']} | {row['Rate_Plan']} ({row['Descuento']}%)"

            with st.expander(header):
                st.caption(
                    f"BW: {row['BW_Inicio']} → {row['BW_Fin']}  |  "
                    f"TW: {row['TW_Inicio']} → {row['TW_Fin']}"
                )

                if hoy > tw_fin:
                    prod = obtener_produccion(df_prod, row["Promo"], row["Hotel"], row["Rate_Plan"])

                    if prod is None:
                        rn = st.number_input("Room Nights", 0, step=1, key=f"rn_{idx}")
                        revenue = st.number_input("Revenue", 0.0, step=1000.0, key=f"rev_{idx}")
                        comentario = st.text_area("Comentario / Insight", key=f"com_{idx}")

                        if st.button("Guardar Producción", key=f"save_prod_{idx}"):
                            nueva = pd.DataFrame([{
                                "Promo": row["Promo"],
                                "Hotel": row["Hotel"],
                                "Rate_Plan": row["Rate_Plan"],
                                "Room_Nights": rn,
                                "Revenue": revenue,
                                "Comentario": comentario
                            }])
                            df_prod = pd.concat([df_prod, nueva], ignore_index=True)
                            guardar_produccion(df_prod)
                            st.success("✅ Producción guardada")
                            st.rerun()
                    else:
                        st.success("✅ Producción cargada")
                        st.markdown(
                            f"""
                            - **Room Nights:** {int(prod['Room_Nights'])}
                            - **Revenue:** ${prod['Revenue']:,.0f}
                            - **Insight:** {prod['Comentario']}
                            """
                        )

        st.download_button(
            "📥 Descargar Excel Operativo",
            data=open(exportar_excel(df), "rb"),
            file_name="Promociones_Playa_Mujeres.xlsx"
        )

    # =============================
    # ADMINISTRACIÓN (SOLO AQUÍ)
    # =============================
    with st.expander("⚙️ Administración"):
    st.warning("Zona administrativa – usar con cuidado")

    password = st.text_input(
        "Contraseña de administrador",
        type="password",
        key="admin_pass"
    )

    if st.button("Acceder", key="btn_admin_login"):
        if password == "admin123":  # cambia la clave si quieres
            st.success("Acceso concedido")

            if st.button("🗑️ Borrar todas las promociones", key="btn_borrar_admin"):
                if os.path.exists(PROMOS_FILE):
                    os.remove(PROMOS_FILE)
                if os.path.exists(PRODUCCION_FILE):
                    os.remove(PRODUCCION_FILE)

                st.success("Base eliminada. Recarga la app.")
        else:
            st.error("Contraseña incorrecta")
# =============================
# TAB REGISTRAR / MODIFICAR
# =============================
with tab_registro:
    st.subheader("Registrar nueva promoción")

    promo = st.text_input("Nombre de la Promoción")

    hoteles = st.multiselect("Propiedad(es)", PROPERTIES)

    col_rp, col_desc = st.columns([2, 1])
    with col_rp:
        rate_plan = st.text_input("Rate Plan")
    with col_desc:
        descuento = st.number_input("Descuento (%)", 0, 100, step=1)

    col_bw1, col_bw2 = st.columns(2)
    with col_bw1:
        bw_ini = st.date_input("BW Inicio")
    with col_bw2:
        bw_fin = st.date_input("BW Fin")

    col_tw1, col_tw2 = st.columns(2)
    with col_tw1:
        tw_ini = st.date_input("TW Inicio")
    with col_tw2:
        tw_fin = st.date_input("TW Fin")

    notas = st.text_area("Notas")

    if st.button("Guardar Promoción", key="btn_guardar_promo"):
        if not promo or not rate_plan or not hoteles:
            st.error("Completa todos los campos obligatorios.")
        else:
            df_existente = cargar_promos()

            rows = []
            for h in hoteles:
                rows.append({
                    "Hotel": h,
                    "Promo": promo,
                    "Rate_Plan": rate_plan,
                    "Descuento": descuento,
                    "BW_Inicio": bw_ini,
                    "BW_Fin": bw_fin,
                    "TW_Inicio": tw_ini,
                    "TW_Fin": tw_fin,
                    "Notas": notas
                })

            df_final = pd.concat([df_existente, pd.DataFrame(rows)], ignore_index=True)
            df_final.to_csv(PROMOS_FILE, index=False)

            st.success("✅ Promoción guardada correctamente")
