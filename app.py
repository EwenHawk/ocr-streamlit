import streamlit as st
import requests
from PIL import Image
import io
import re

st.set_page_config(page_title="OCR Indexation", page_icon="🔎", layout="centered")
st.title("🧠 Lecture OCR par indexation ciblée")

# 🎯 Champs à extraire
target_fields = ["Voc", "Isc", "Pmax", "Vpm", "Ipm"]

# 📉 Prétraitement de l’image
def preprocess_image(img, rotation):
    if rotation:
        img = img.rotate(-rotation, expand=True)
    max_width = 1024
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.Resampling.LANCZOS)
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

# 🧠 Indexation champ → valeur par ordre
def extract_indexed_values(text, field_keys):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    field_block = []
    value_block = []

    # Étape 1: détecter les champs techniques (ex: "Voc:")
    for line in lines:
        if line.endswith(":") and re.sub(r"[^a-zA-Z]", "", line).lower() in [f.lower() for f in field_keys]:
            field_block.append(line.rstrip(":").strip())

    # Étape 2: collecter les valeurs numériques après le bloc
    if field_block:
        start_index = lines.index(field_block[0] + ":") + 1
        for line in lines[start_index:]:
            match = re.search(r"\d+[.,]?\d*\s*[A-Za-z%ΩVWAm]*", line)
            if match:
                value_block.append(match.group(0).strip())
            if len(value_block) >= len(field_block):
                break

    # Étape 3: associer par position
    result = {}
    for i in range(min(len(field_block), len(value_block))):
        result[field_block[i]] = value_block[i]

    # Filtrer les champs cibles
    filtered = {key: result.get(key, "Non détecté") for key in field_keys}
    return filtered

# 📥 Interface utilisateur
uploaded_file = st.file_uploader("📤 Importer une image technique", type=["jpg", "jpeg", "png"])
if uploaded_file:
    img = Image.open(uploaded_file)

    rotation = st.selectbox("🔁 Rotation ?", [0, 90, 180, 270], index=0)
    img = preprocess_image(img, rotation)
    st.image(img, caption="🖼️ Image préparée", use_container_width=True)

    # Compression JPEG
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG", quality=70)
    img_bytes.seek(0)

    raw_text = ocr_space_api(img_bytes)
    with st.expander("📄 Texte OCR brut"):
        st.text(raw_text)

    results = extract_indexed_values(raw_text, target_fields)

    st.subheader("📊 Champs techniques extraits :")
    for key in target_fields:
        st.write(f"🔹 **{key}** → {results[key]}")
