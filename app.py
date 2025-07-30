import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image, ImageEnhance
import io
import requests
import re
import gspread
from google.oauth2.service_account import Credentials

# 🆔 Récupération de l'ID_Panneau depuis l'URL
id_panneau = st.query_params.get("id_panneau", [""])[0]
TARGET_KEYS = ["Voc", "Isc", "Pmax", "Vpm", "Ipm"]

# États Streamlit
for key, default in [
    ("selection_mode", False),
    ("sheet_saved", False),
    ("results", {}),
]:
    if key not in st.session_state:
        st.session_state[key] = default

st.set_page_config(page_title="✂️ Rognage + OCR", layout="centered")
st.title("📸 Rognage + Retouche + OCR 🔎")

uploaded_file = st.file_uploader("Téléverse une image (max 200 MB)", type=["jpg", "png", "jpeg"])

# Désactive le scroll sur le canvas pour améliorer le tactile
st.markdown("""
<style>
  canvas {
    touch-action: none;
  }
</style>
""", unsafe_allow_html=True)

# 📄 Fonction extraction intelligente
def extract_ordered_fields(text, expected_keys=TARGET_KEYS):
    aliases = {
        "voc": "Voc", "v_oc": "Voc",
        "isc": "Isc", "lsc": "Isc", "i_sc": "Isc", "isci": "Isc", "Isci": "Isc",
        "pmax": "Pmax", "p_max": "Pmax", "pmax.": "Pmax",
        "vpm": "Vpm", "v_pm": "Vpm", "vpm.": "Vpm",
        "ipm": "Ipm", "i_pm": "Ipm", "ipm.": "Ipm", "lpm": "Ipm",
        "Iom": "Ipm", "iom": "Ipm", "lom": "Ipm", "Lom":
