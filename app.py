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
    # 1. LOGO HIC (Prioridad Visual)
    logo_hic = "HIC.png"
    try:
        st.image(logo_hic, use_container_width=True)
    except:
        st.write("🏨 **Hyatt Inclusive Collection**")
        st.caption("Playa Mujeres Complex")

    st.write("---")

    # 2. GUÍA RÁPIDA (Lo que el equipo necesita ver siempre)
    st.subheader("Guía Rápida")
    st.write("🆕 **Nuevo**: Limpia el formulario.")
    st.write("💾 **Guardar**: Crea o actualiza promos.")
    st.write("📥 **Excel**: Baja el reporte actual.")

    # ESPACIADOR (Para empujar la zona de admin hacia abajo)
    st.write("")
    st.write("")
    st.write("")
    st.write("")
    st.write("")

    st.write("---")
    
    # 3. ZONA DE ADMINISTRADOR (Ahora al final)
    with st.expander("🔐 Zona de Administrador"):
        st.caption("Acceso restringido para limpieza de base de datos.")
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
# ... (El resto del código de carga de datos y pestañas se mantiene igual)
