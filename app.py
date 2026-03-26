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
    # 1. LOGO HIC (Nombre exacto del archivo en tu GitHub)
    logo_hic = "HIC.png"
    try:
        st.image(logo_hic, use_container_width=True)
    except:
        st.write("🏨 **Hyatt Inclusive Collection**")
        st.caption("Playa Mujeres Complex")

    st.write("---")

    # 2. GUÍA RÁPIDA (Visible para todo el equipo)
    st.subheader("Guía Rápida")
    st.write("🆕 **Nuevo**: Limpia el formulario actual.")
    st.write("💾 **Guardar**: Crea una nueva promoción.")
    st.write("🔄 **Actualizar**: Sobreescribe datos existentes.")
    st.write("📥 **Excel**: Descarga el reporte actual.")

    # Espacio visual para empujar la zona de admin al fondo
    for _ in range(5):
        st.write("")

    st.write("---")
    
    # 3. ZONA DE ADMINISTRADOR (Oculta y al final)
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

tab_
