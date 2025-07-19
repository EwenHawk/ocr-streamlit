import streamlit as st
import requests
import re

# 📌 Clés des champs à extraire
TARGET_FIELDS = ["pmax", "voc", "isc", "vpm", "imp"]

# 🧹 Nettoyage du texte OCR
def clean(text):
    return re.sub(r"\s+", " ", text.strip().lower())

# 🔍 Fonction d’extraction OCR via OCR.Space API
def extract_fields_from_image(image_bytes, api_key="helloworld"):
    url = "https://api.ocr.space/parse/image"
    response = requests.post(
        url,
        files={"filename": image_bytes},
        data={"apikey": api_key, "language": "eng", "isOverlayRequired": False},
    )

    result = response.json()
    text = result.get("ParsedResults", [{}])[0].get("ParsedText", "")
    results = {}

    for line in text.split("\n"):
        line_clean = clean(line)
        for field in TARGET_FIELDS:
            match = re.search(rf"{field}\s*:\s*([\w\.\-]+)", line_clean, re.IGNORECASE)
            if match:
                results[field.upper()] = match.group(1)

    return results

# 🖼️ Interface Streamlit
st.title("🔎 OCR Technique – PV Specs Extractor")
st.write("Upload une image avec des spécifications (Voc, Isc, etc.) et récupère les données automatiquement 📥")

uploaded_file = st.file_uploader("🖼️ Choisis ton image :", type=["jpg", "png", "jpeg"])

if uploaded_file:
    with st.spinner("Lecture OCR en cours..."):
        specs = extract_fields_from_image(uploaded_file)

    st.success("✅ Extraction terminée !")
    st.json(specs)
