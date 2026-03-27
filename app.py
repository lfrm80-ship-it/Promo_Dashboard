import streamlit as st
import pandas as pd
import os
from datetime import date

# =============================
# CONFIGURACIÓN GENERAL
# =============================
st.set_page_config(
    page_title="Administrador de Promociones",
    layout="wide"
)

PROMOS_FILE = "promociones_data.csv"
PRODUCCION_FILE = "promociones_produccion.csv"

# =============================
# UTILIDADES
# =============================
def safe_read_csv(path):
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame()

# =============================
# CARGA DE PROMOS
# =============================
def cargar_promos():
    df = safe_read_csv(PROMOS_FILE)
    if df.empty:
        return df

    # Fechas
    for c in ["BW_Inicio","BW_Fin","TW_Inicio","TW_Fin"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c]).dt.date

    # Columnas opcionales seguras
    if "Market" not in df.columns:
        df["Market"] = ""
    if "Notas" not in df.columns:
        df["Notas"] = ""

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
# EXPORTAR EXCEL
# =============================
def exportar_excel(df):
    export_df = df.copy()
    export_df.to_excel("promociones_export.xlsx", index=False)
    return "promociones_export.xlsx"

# =============================
# HEADER
# =============================
st.markdown(
    "<h1 style='text-align:center;'>Administrador de Promociones</h1>",
    unsafe_allow_html=True
)
st.markdown(
    "<div style='text-align:center;color:#6b6b6b;font-size:14px;'>"
    "Playa Mujeres – DREPM &amp; SECPM"
    "</div>",
    unsafe_allow_html=True
)
st.divider()

# =============================
# TABS
# =============================
tab_promos, tab_registro, tab_admin = st.tabs(
    ["Promociones", "Registrar / Modificar", "Administración"]
)

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
        # Buscador
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

        # Tabla
        vista = df_f.copy()
        if "Descuento" in vista.columns:
            vista["Descuento"] = vista["Descuento"].astype(str) + " %"
        st.dataframe(vista, use_container_width=True)

        st.subheader("Estado y Vigencia de Promociones")

        filtro = st.radio(
            "Mostrar:",
            ["Todas", "🟢 Activas", "🟡 Por iniciar", "🔴 Expiradas"],
            horizontal=True
        )

        for idx, row in df_f.iterrows():

            tw_ini = row["TW_Inicio"]
            tw_fin = row["TW_Fin"]

            if hoy < tw_ini:
                estado = "🟡 Por iniciar"
            elif hoy > tw_fin:
                estado = "🔴 Expirada"
            else:
                estado = "🟢 Activa"

            if filtro != "Todas" and estado != filtro:
                continue

            header = (
                f"{estado} | {row['Promo']} | {row['Hotel']} | "
                f"{row['Rate_Plan']} ({row['Descuento']}%)"
            )

            with st.expander(header):
                st.caption(
                    f"BW: {row['BW_Inicio']} → {row['BW_Fin']}  |  "
                    f"TW: {row['TW_Inicio']} → {row['TW_Fin']}"
                )

                if hoy > tw_fin:
                    prod = obtener_produccion(
                        df_prod,
                        row["Promo"],
                        row["Hotel"],
                        row["Rate_Plan"]
                    )

                    if prod is None:
                        st.markdown("### 📊 Agregar Producción")
                        rn = st.number_input("Room Nights", 0, step=1, key=f"rn_{idx}")
                        revenue = st.number_input("Revenue", 0.0, step=1000.0, key=f"rev_{idx}")
                        comentario = st.text_area("Comentario / Insight", key=f"com_{idx}")

                        if st.button("Guardar Producción", key=f"save_{idx}"):
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

        # Botón Excel
        st.download_button(
            "📥 Descargar Excel Operativo",
            data=open(exportar_excel(df), "rb"),
            file_name="Promociones_Playa_Mujeres.xlsx"
        )

# =============================
# TAB REGISTRAR / MODIFICAR
# =============================
with tab_registro:

    st.subheader("Registrar nueva promoción")

    promo = st.text_input("Nombre de la Promoción")
    hotel = st.text_input("Hotel")
    rate_plan = st.text_input("Rate Plan")
    descuento = st.number_input("Descuento (%)", 0, 100, step=1)

    bw_ini = st.date_input("Booking Window Inicio")
    bw_fin = st.date_input("Booking Window Fin")
    tw_ini = st.date_input("Travel Window Inicio")
    tw_fin = st.date_input("Travel Window Fin")

    notas = st.text_area("Notas")

    if st.button("Guardar Promoción"):
        nueva = pd.DataFrame([{
            "Hotel": hotel,
            "Promo": promo,
            "Rate_Plan": rate_plan,
            "Descuento": descuento,
            "BW_Inicio": bw_ini,
            "BW_Fin": bw_fin,
            "TW_Inicio": tw_ini,
            "TW_Fin": tw_fin,
            "Notas": notas
        }])

        df_existente = cargar_promos()
        df_final = pd.concat([df_existente, nueva], ignore_index=True)
        df_final.to_csv(PROMOS_FILE, index=False)
        st.success("✅ Promoción guardada correctamente")

# =============================
# TAB ADMINISTRACIÓN
# =============================
with tab_admin:
    st.warning("⚠️ Zona Administrativa")
    if st.button("🗑️ Borrar todas las promociones"):
        if os.path.exists(PROMOS_FILE):
            os.remove(PROMOS_FILE)
        if os.path.exists(PRODUCCION_FILE):
            os.remove(PRODUCCION_FILE)
        st.success("Base eliminada. Recarga la app.")

# =============================
# ADMINISTRACIÓN (DISCRETA)
# =============================
with st.expander("⚙️ Administración"):
    st.warning("Zona administrativa")
    if st.button("🗑️ Borrar todas las promociones"):
        if os.path.exists(PROMOS_FILE):
            os.remove(PROMOS_FILE)
        if os.path.exists(PRODUCCION_FILE):
            os.remove(PRODUCCION_FILE)
        st.success("Base eliminada. Recarga la app.")
