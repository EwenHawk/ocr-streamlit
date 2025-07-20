import streamlit as st
import requests
from PIL import Image
import io
import re

# ⚙️ Config de la page Streamlit
st.set_page_config(page_title="OCR Indexé Intelligent", page_icon="🧠", layout="centered")
st.title("🔗 Lecture OCR par indexation + alias")

# 🎯 Champs à extraire (noms canoniques)
target_fields = ["Voc", "Isc", "Pmax", "Vpm", "Ipm"]

# 🧠 Alias pour tolérer les erreurs OCR
field_aliases = {
    "voc": "Voc",
    "isc": "Isc",
    "pmax": "Pmax",
    "vpm": "Vpm",
    "ipm": "Ipm",
    "lpm": "Ipm",  # alias commun OCR
}

# 📉 Prétraitement image
def preprocess_image(img, rotation):
    if rotation:
        img = img.rotate(-rotation, expand=True)
    max_width = 1024
    if img.width > max_width:
        ratio = max_width / float(img.width)
        img = img.resize((max_width, int(img.height * ratio)), Image.Resampling.LANCZOS)
    return img

# 🔍 Lecture OCR brut via OCR.Space
def ocr_space_api(img_bytes, api_key="helloworld"):  # Remplace "helloworld" par ta clé API perso
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

# 🧠 Indexation champs et valeurs
def index_and_match_fields_with_alias(text, field_keys, aliases):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    raw_fields = []
    raw_values = []

    for line in lines:
        if line.endswith(":"):
            clean = line.rstrip(":").strip().lower()
            if clean in aliases:
                raw_fields.append(aliases[clean])

    for line in lines:
        match = re.match(r"^\d+[.,]?\d*\s*[A-Za-z%ΩVWAm]*$", line)
        if match:
            raw_values.append(match.group(0).strip())

    result = {}
    for i in range(min(len(raw_fields), len(raw_values))):
        result[raw_fields[i]] = raw_values[i]

    final = {key: result.get(key, "Non détecté") for key in field_keys}
    return final

# 📥 Interface utilisateur
uploaded_file = st.file_uploader("📤 Importer une image technique", type=["jpg", "jpeg", "png"])
if uploaded_file:
    img = Image.open(uploaded_file)
    rotation = st.selectbox("🔁 Rotation ?", [0, 90, 180, 270], index=0)
    img = preprocess_image(img, rotation)
    st.image(img, caption="🖼️ Image traitée", use_container_width=True)

    st.markdown("### ✂️ Sélection de la zone à rogner")
    crop_x = st.slider("Position X (gauche)", 0, img.width, int(img.width * 0.1))
    crop_y = st.slider("Position Y (haut)", 0, img.height, int(img.height * 0.1))
    crop_w = st.slider("Largeur", 1, img.width - crop_x, int(img.width * 0.8))
    crop_h = st.slider("Hauteur", 1, img.height - crop_y, int(img.height * 0.8))

    cropped_img = img.crop((crop_x, crop_y, crop_x + crop_w, crop_y + crop_h))
    st.image(cropped_img, caption="🔍 Zone rognée sélectionnée", use_container_width=True)

    img_bytes = io.BytesIO()
    cropped_img.save(img_bytes, format="JPEG", quality=70)
    img_bytes.seek(0)

    raw_text = ocr_space_api(img_bytes)
    with st.expander("📄 Texte OCR brut"):
        st.text(raw_text)

    results = index_and_match_fields_with_alias(raw_text, target_fields, field_aliases)

    st.subheader("📊 Champs techniques extraits :")
    for key in target_fields:
        st.write(f"🔹 **{key}** → {results.get(key)}")
