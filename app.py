import streamlit as st
import pandas as pd
import os
import io
from datetime import date, datetime

# 1. CONFIGURACIÓN E IDENTIDAD HYATT
st.set_page_config(page_title="Promociones DREPM & SECPM | Hyatt AI", layout="wide")

# --- SEGURIDAD: TU CONTRASEÑA ---
PASSWORD_MAESTRA = "PlayaMujeres2026" 

# --- MENÚ LATERAL CON LOGO HIC ---
with st.sidebar:
    # --- CAMBIO A HIC.png ---
    logo_hic = "HIC.png"
    
    # Verificamos si el archivo existe en tu GitHub
    if os.path.exists(logo_hic):
        st.image(logo_hic, use_container_width=True)
    else:
        # Texto de respaldo elegante si la imagen no se encuentra
        st.write("🏨 **Hyatt Inclusive Collection**")
        st.caption("Dreams & Secrets Playa Mujeres")
        
    st.write("---")
    # ... (El resto de tu código de la Zona de Administrador y Guía Rápida continúa igual)
