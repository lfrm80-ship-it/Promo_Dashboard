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

# ==============================
# CSS (FONDO + TABS)
# ==============================
st.markdown(
    """
    <style>
    body {
        background-color: #f7f8fa;
    }
    .block-container {
        background-color: #f7f8fa;
        padding-top: 1.5rem;
    }
    div[data-baseweb="tab-list"] {
        justify-content: center;
    }
    button[data-baseweb="tab"] {
        font-size: 0.85rem;
        padding: 6px 14px;
        font-weight: 400;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
