import streamlit as st
import pandas as pd
import os
import io
from datetime import date

# ==============================
# CONFIGURACIÓN GENERAL
# ==============================
st.set_page_config(
    page_title="Administrador de Promociones",
    layout="wide"
)

CSV_FILE = "promociones_data.csv"
MEDIA_DIR = "media"
PASSWORD_MAESTRA = "PlayaMujeres2026"

if not os.path.exists(MEDIA_DIR):
    os.makedirs(MEDIA_DIR)

# ======================================
# CSS GLOBAL (TABS + FONDO SUAVE)
# ======================================
st.markdown(
    """
    <style>
    /* Fondo general suave */
    body {
        background-color: #f7f8fa;
    }

    /* Contenedor principal */
    .block-container {
        padding-top: 1.5rem;
        background-color: #f7f8fa;
    }

    /* Centrar el menú de tabs */
    div[data-baseweb="tab-list"] {
        justify-content: center;
    }

    /* Tabs más pequeñas y limpias */
    button[data-baseweb="tab"] {
        font-size: 0.85rem;
        padding: 6px 14px;
        font-weight: 400;
    }

    /* Tab activa más sutil */
    button[data-baseweb="tab"][aria-selected="true"] {
        font-weight: 500;
    }

    /* Header con línea inferior sutil */
    header {
        background-color: white;
        border-bottom: 1px solid #e6e6e6;
    }
    </style>
    """,
    unsafe_allow_html=True
)
``
