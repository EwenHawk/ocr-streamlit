import streamlit as st
import requests
from PIL import Image
import io
import re

st.set_page_config(page_title="OCR Indexé Intelligent", page_icon="🧠", layout="centered")
st.title("🔗 Lecture OCR par indexation champ + valeur")

# 🎯 Champs à extraire
target_fields = ["Voc", "Isc", "Pmax", "Vpm", "Ipm"]

# 📉 Prétraitement de l’image
def preprocess_image(img, rotation):
    if rotation:
        img = img.rotate(-rotation, expand=True)
    max_width = 1024
    if img.width > max_width:
        ratio = max_width / img.width
        new_height = int(img.height * ratio)
        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
    return img

# 🔍 Lecture OCR brute
def ocr_space_api(img_bytes, api_key="helloworld"):
    response = requests.post(
        "https://api.ocr.space/parse/image",
        files={"filename": ("image.jpg", img_bytes, "image/jpeg")},
        data={
            "apikey": api_key,
            "language": "eng",
            "isOverlayRequired": False
        }
    )
    result = response.json()
    return result.get("ParsedResults", [])[0].get("ParsedText", "")

# 🧠 Indexation des libellés techniques et des valeurs chiffrées
def index_and_match_fields(text, field_keys):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    field_block = []
    value_block = []

    # Étape 1: indexer les libellés (ex: "Voc:")
    for line in lines:
        clean = line.rstrip(":").strip()
        if clean.lower() in [f.lower() for f in field_keys]:
            field_block.append(clean)

    # Étape 2: indexer les valeurs chiffrées
    for line in lines:
        match = re.match(r"^\d+[.,]?\d*\s*[A-Za-z%ΩVWAm]*$", line)
        if match:
            value_block.append(match.group(0).strip())

    # Étape 3: associer par position
    full_pairs = {}
    for i in range(min(len(field_block), len(value_block))):
        full_pairs[field_block[i]] = value_block[i]

    # Étape 4: filtrer uniquement les champs qui t’intéressent
    filtered = {}
    for key in field_keys:
        for actual_key in full_pairs:
            if actual_key.lower() == key.lower():
                filtered[key] = full_pairs[actual_key]
                break
        else:
            filtered[key] = "Non détecté"
    return filtered

# 📥 Interface utilisateur
uploaded_file = st.file_uploader("📤 Importer une image technique", type=["jpg", "jpeg", "png"])
if uploaded_file:
    img = Image.open(uploaded_file)

    rotation = st.selectbox("🔁 Rotation ?", [0, 90, 180, 270], index=0)
    img = preprocess_image(img, rotation)
    st.image(img, caption="🖼️ Image traitée", use_container_width=True)

    # Compression JPEG
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG", quality=70)
    img_bytes.seek(0)

    raw_text = ocr_space_api(img_bytes)
    with st.expander("📄 Texte OCR brut"):
        st.text(raw_text)

    results = index_and_match_fields(raw_text, target_fields)

    st.subheader("📊 Champs techniques extraits :")
    for key in target_fields:
        st.write(f"🔹 **{key}** → {results.get(key)}")
