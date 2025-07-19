import streamlit as st
import requests
from PIL import Image
import io
import re

st.set_page_config(page_title="OCR Technique", page_icon="🔍", layout="centered")
st.title("📸 Analyseur OCR Technique")

uploaded_file = st.file_uploader("Importer une image (JPG, PNG)", type=["jpg", "jpeg", "png"])

def ocr_space_api(img_bytes, api_key="helloworld"):
    response = requests.post(
        "https://api.ocr.space/parse/image",
        files={"filename": img_bytes},
        data={
            "apikey": api_key,
            "language": "eng",
            "isOverlayRequired": False
        }
    )
    result = response.json()
    return result["ParsedResults"][0]["ParsedText"]

def extract_fields(text):
    def get(rx): m = re.search(rx, text, re.IGNORECASE); return m.group(1) if m else "Non détecté"
    convert = lambda v: round(float(v.replace(",", ".")), 2) if v not in ["", "Non détecté"] else v
    return {
        "Pmax": convert(get(r"Pmax\s*[:=]?\s*(\d+[.,]?\d*)")),
        "Vpm":  convert(get(r"Vpm\s*[:=]?\s*(\d+[.,]?\d*)")),
        "Ipm":  convert(get(r"Ipm\s*[:=]?\s*(\d+[.,]?\d*)")),
        "Voc":  convert(get(r"Voc\s*[:=]?\s*(\d+[.,]?\d*)")),
        "Isc":  convert(get(r"Isc\s*[:=]?\s*(\d+[.,]?\d*)")),
    }

if uploaded_file:
    img = Image.open(uploaded_file)
    st.image(img, caption="Image importée", use_column_width=True)

    # Convert image to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    text = ocr_space_api(img_bytes)
    with st.expander("📄 Texte OCR brut"):
        st.text(text)

    st.subheader("📊 Champs techniques extraits")
    results = extract_fields(text)
    for k, v in results.items():
        st.write(f"✅ **{k}** : {v}")
