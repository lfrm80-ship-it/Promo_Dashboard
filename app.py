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

MARKETS = ["US", "LATAM", "EU", "UK", "CA"]
PROPERTIES = [
    "DREPM - Dreams Playa Mujeres",
    "SECPM - Secrets Playa Mujeres"
]

# =============================
# UTILIDADES
# =============================

def normalizar_market(x):
    if isinstance(x, list):
        return x
    if isinstance(x, str):
        return [m.strip() for m in x.split("|") if m.strip()]
    return []

# =============================
# CARGA DE DATA
# =============================

def cargar_promos():
    if os.path.exists(PROMOS_FILE):
        df = pd.read_csv(PROMOS_FILE)

        # Convertir fechas
        for c in ["BW_Inicio","BW_Fin","TW_Inicio","TW_Fin"]:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c]).dt.date

        # ✅ Asegurar columna Market
        if "Market" not in df.columns:
            df["Market"] = [[] for _ in range(len(df))]
        else:
            df["Market"] = df["Market"].apply(normalizar_market)

        return df

    return pd.DataFrame()

# =============================
# HEADER EJECUTIVO (SIMPLE Y ESTABLE)
# =============================

st.markdown(
    "<h1 style='text-align:center;'>Administrador de Promociones</h1>",
    unsafe_allow_html=True
)
st.markdown(
    "<div style='text-align:center; color:#6b6b6b; font-size:14px;'>"
    "Playa Mujeres – DREPM &amp; SECPM"
    "</div>",
    unsafe_allow_html=True
)
st.divider()

# =============================
# TABS
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
        # -------------------------
        # BUSCADOR
        # -------------------------
        search = st.text_input(
            "🔍 Buscar promoción",
            placeholder="Nombre, Rate Plan, Market, Hotel, Notas…"
        )

        df_f = df.copy()
        if search:
            mask = (
                df_f["Promo"].astype(str).str.contains(search, case=False, na=False)
                | df_f["Rate_Plan"].astype(str).str.contains(search, case=False, na=False)
                | df_f["Hotel"].astype(str).str.contains(search, case=False, na=False)
                | df_f["Notas"].astype(str).str.contains(search, case=False, na=False)
            )
            df_f = df_f[mask]

        # -------------------------
        # TABLA OPERATIVA
        # -------------------------
        vista = df_f.copy()
        vista["Market"] = vista["Market"].apply(lambda x: ", ".join(x))
        vista["Descuento"] = vista["Descuento"].astype(int).astype(str) + " %"
        st.dataframe(vista, use_container_width=True)

        st.subheader("Estado y Vigencia de Promociones")

        filtro = st.radio(
            "Mostrar:",
            ["Todas", "🟢 Activas", "🟡 Por iniciar", "🔴 Expiradas"],
            horizontal=True
        )

        # -------------------------
        # LOOP DE PROMOS
        # -------------------------
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

            with st.expander(
                f"{estado} | {row['Promo']} | {row['Hotel']} | {row['Rate_Plan']}"
            ):
                st.caption(f"Travel Window: {tw_ini} → {tw_fin}")

                # -------------------------
                # PRODUCCIÓN (FINAL DE CICLO)
                # -------------------------
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

# =============================
# TAB REGISTRAR / MODIFICAR
# =============================
with tab_registro:
    st.info("Formulario de registro sin cambios (usa tu versión existente).")
