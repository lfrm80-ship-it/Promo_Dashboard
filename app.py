import streamlit as st
import pandas as pd
import os
import io
from datetime import date, datetime

# 1. CONFIGURACIÓN E IDENTIDAD HYATT
st.set_page_config(page_title="Promociones DREPM & SECPM | Hyatt AI", layout="wide")

# --- SEGURIDAD: TU CONTRASEÑA ---
PASSWORD_MAESTRA = "PlayaMujeres2026" 

# --- MENÚ LATERAL ---
with st.sidebar:
    # 1. LOGO HIC (AJUSTADO A 150px para que sea más pequeño)
    logo_hic = "HIC.png"
    try:
        # Aquí usamos width=150 para que no abarque todo el ancho y se vea más elegante
        st.image(logo_hic, width=150)
    except:
        st.write("🏨 **Hyatt Inclusive Collection**")
        st.caption("Playa Mujeres Complex")

    st.write("---")

    # 2. GUÍA RÁPIDA
    st.subheader("Guía Rápida")
    st.write("🆕 **Nuevo**: Limpia formulario")
    st.write("💾 **Guardar**: Crea nueva promoción")
    st.write("🔄 **Actualizar**: Sobreescribe datos existentes")
    st.write("📥 **Excel**: Descarga reporte")

    # Espacio visual
    for _ in range(5):
        st.write("")

    st.write("---")
    
    # 3. ZONA DE ADMINISTRADOR
    with st.expander("🔐 Zona de Administrador"):
        st.caption("Acceso restringido para limpieza profunda.")
        pass_input = st.text_input("Introduce clave maestra:", type="password")
        
        if pass_input == PASSWORD_MAESTRA:
            st.success("Acceso Autorizado")
            if st.button("⚠️ BORRAR TODA LA BASE DE DATOS"):
                if os.path.exists("promociones_data.csv"):
                    os.remove("promociones_data.csv")
                    st.warning("Base de datos eliminada. Reiniciando...")
                    st.rerun()
        elif pass_input != "":
            st.error("Contraseña Incorrecta")

st.title("🏨 Dashboard Maestro de Promociones")

CSV_FILE = "promociones_data.csv"
MEDIA_DIR = "media"

if not os.path.exists(MEDIA_DIR):
    os.makedirs(MEDIA_DIR)

def cargar_datos():
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        df['BW_Fin'] = pd.to_datetime(df['BW_Fin']).dt.date
        df['TW_Inicio'] = pd.to_datetime(df['TW_Inicio']).dt.date
        df['TW_Fin'] = pd.to_datetime(df['TW_Fin']).dt.date
        return df
    return pd.DataFrame(columns=["Hotel", "Promo", "Rate_Plan", "Descuento", "BW_Inicio", "BW_Fin", "TW_Inicio", "TW_Fin", "Notas", "Archivo_Path"])

# --- PESTAÑAS PRINCIPALES ---
tab_buscar, tab_registrar = st.tabs(["🔍 BUSCADOR & REPORTES", "➕ REGISTRAR O MODIFICAR"])

# --- PESTAÑA: REGISTRO / MODIFICACIÓN ---
with tab_registrar:
    df_actual = cargar_datos()
    
    if st.button("🧹 Limpiar Formulario"):
        st.rerun()

    st.write("---")
    rate_a_buscar = st.text_input("🔑 Introduce Rate Plan:", help="Escribe el código para buscar o crear")

    promo_existente = df_actual[df_actual['Rate_Plan'] == rate_a_buscar]
    es_modificacion = not promo_existente.empty

    if es_modificacion:
        st.info(f"📂 Editando promoción existente: `{rate_a_buscar}`")
    
    with st.form("registro_form"):
        col1, col2 = st.columns(2)
        opciones_hoteles = ["DREPM - Dreams Playa Mujeres", "SECPM - Secrets Playa Mujeres"]
        default_hotel = [promo_existente['Hotel'].values[0]] if es_modificacion else []
        hoteles_seleccionados = col1.multiselect("Propiedad(es)", opciones_hoteles, default=default_hotel)
        
        promo = col2.text_input("Nombre de la Promoción", value=promo_existente['Promo'].values[0] if es_modificacion else "")
        
        c1, c2 = st.columns(2)
        desc = c1.number_input("% Descuento", min_value=0, max_value=100, step=5, value=int(promo_existente['Descuento'].values[0]) if es_modificacion else 0)
        archivo_subido = st.file_uploader("📁 Backup (Imagen/PDF)", type=["png", "jpg", "pdf"])
        
        st.write("---")
        col_bw, col_tw = st.columns(2)
        bw_range = col_bw.date_input("Rango de BW", value=(date.today(), date.today()))
        tw_range = col_tw.date_input("Rango de TW", value=(date.today(), date.today()))
        
        notas = st.text_area("Notas / Restricciones", value=promo_existente['Notas'].values[0] if es_modificacion else "")
        
        b_col1, b_col2 = st.columns(2)
        texto_main = "🔄 Actualizar Cambios" if es_modificacion else "💾 Guardar Promo"
        submit = b_col1.form_submit_button(texto_main, use_container_width=True)
        
        eliminar = False
        if es_modificacion:
            eliminar = b_col2.form_submit_button("🗑️ Eliminar esta Promo", use_container_width=True)

        if submit:
            if not rate_a_buscar or not hoteles_seleccionados:
                st.error("Error: Falta el Rate Plan o el Hotel.")
            else:
                path_destino = promo_existente['Archivo_Path'].values[0] if es_modificacion else ""
                if archivo_subido:
                    path_destino = os.path.join(MEDIA_DIR, f"{rate_a_buscar}_{archivo_subido.name}")
                    with open(path_destino, "wb") as f: f.write(archivo_subido.getbuffer())

                bw_i, bw_f = bw_range if len(bw_range) == 2 else (bw_range[0], bw_range[0])
                tw_i, tw_f = tw_range if len(tw_range) == 2 else (tw_range[0], tw_range[0])
                
                if es_modificacion:
                    df_actual = df_actual[df_actual['Rate_Plan'] != rate_a_buscar]
                
                nuevos_registros = []
                for h in hoteles_seleccionados:
                    nuevos_registros.append({
                        "Hotel": h, "Promo": promo, "Rate_Plan": rate_a_buscar, 
                        "Descuento": desc, "BW_Inicio": bw_i, "BW_Fin": bw_f, 
                        "TW_Inicio": tw_i, "TW_Fin": tw_f, "Notas": notas, 
                        "Archivo_Path": path_destino
                    })
                
                df_actual = pd.concat([df_actual, pd.DataFrame(nuevos_registros)], ignore_index=True)
                df_actual.to_csv(CSV_FILE, index=False)
                st.success(f"✅ ¡Guardado con éxito!")
                st.rerun()

        if eliminar:
            df_actual = df_actual[df_actual['Rate_Plan'] != rate_a_buscar]
            df_actual.to_csv(CSV_FILE, index=False)
            st.warning("❌ Registro eliminado.")
            st.rerun()

# --- PESTAÑA: BUSCADOR & REPORTES ---
with tab_buscar:
    df = cargar_datos()
    if not df.empty:
        col_filtro, col_excel = st.columns([3, 1])
        with col_filtro:
            busqueda = st.text_input("🔎 Filtrar búsqueda:")
        
        df_f = df[df.astype(str).apply(lambda x: x.str.contains(busqueda, case=False)).any(axis=1)] if busqueda else df
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_f.drop(columns=['Archivo_Path']).to_excel(writer, index=False, sheet_name='Promociones')
        
        with col_excel:
            st.write(" ")
            st.download_button(label="📥 Excel", data=output.getvalue(), file_name=f"Reporte_{date.today()}.xlsx", use_container_width=True)

        for i, r in df_f.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                c1.subheader(f"{r['Hotel']} | {r['Promo']}")
                c2.metric("Desc.", f"{r['Descuento']}%")
                st.write(f"**Rate:** `{r['Rate_Plan']}` | **Viaje:** {r['TW_Inicio']} al {r['TW_Fin']}")
    else:
        st.info("La base de datos está vacía. Lista para empezar.")
