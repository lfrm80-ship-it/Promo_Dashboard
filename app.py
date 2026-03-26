import streamlit as st
import pandas as pd
import os
import io
from datetime import date

#======================================================# CONFIG GENERAL
#======================================================st.set_page_config(page_title="Promociones DREPM & SECPM | Hyatt AI",layout="wide")PASSWORD_MAESTRA="PlayaMujeres2026"
CSV_FILE="promociones_data.csv"
MEDIA_DIR="media"

if not os.path.exists(MEDIA_DIR):
    os.makedirs(MEDIA_DIR)#======================================================# ESTILOS SUAVES(CSS)#======================================================st.markdown("""
<style>
.block-container { padding-top: 2rem; }
.sidebar-divider { margin: 1rem 0; border-bottom: 1px solid #e0e0e0; }
.card-title { font-weight: 600; font-size: 1.1rem; }
.small-muted { color: #6b6b6b; font-size: 0.9rem; }
</style>
""",unsafe_allow_html=True)#======================================================# SIDEBAR
#======================================================with st.sidebar:
    try:
        st.image("HIC.png",width=140)except:
        st.markdown("### 🏨 Hyatt Inclusive Collection")st.caption("Playa Mujeres Complex")st.markdown('<div class="sidebar-divider"></div>',unsafe_allow_html=True)st.markdown("#### Guía rápida")st.markdown("""-🆕 Limpiar formulario-💾 Guardar promoción-🔄 Actualizar existente-📥 Descargar reporte  
    """)st.markdown('<div class="sidebar-divider"></div>',unsafe_allow_html=True)with st.expander("🔐 Zona Administrador"):
        st.caption("Acceso restringido – acción irreversible")pass_input=st.text_input("Clave maestra",type="password")if pass_input==PASSWORD_MAESTRA:
            st.success("Acceso autorizado")if st.button("⚠️ Borrar toda la base"):
                if os.path.exists(CSV_FILE):
                    os.remove(CSV_FILE)st.warning("Base eliminada")
