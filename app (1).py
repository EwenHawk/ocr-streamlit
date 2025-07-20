import streamlit as st
import requests
from PIL import Image
import io
import re

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

# 🔍 Lecture OCR brut
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

# 🧠 Indexation champs et valeurs, puis correspondance avec alias
def index_and_match_fields_with_alias(text, field_keys, aliases):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    raw_fields = []
    raw_values = []

    # Étape 1 : indexer les libellés reconnus
    for line in lines:
        if line.endswith(":"):
            clean = line.rstrip(":").strip().lower()
            if clean in aliases:
                raw_fields.append(aliases[clean])

    # Étape 2 : collecter les valeurs chiffrées
    for line in lines:
        match = re.match(r"^\d+[.,]?\d*\s*[A-Za-z%ΩVWAm]*$", line)
        if match:
            raw_values.append(match.group(0).strip())

    # Étape 3 : associer par position
    result = {}
    for i in range(min(len(raw_fields), len(raw_values))):
        result[raw_fields[i]] = raw_values[i]

    # Étape 4 : filtrer uniquement les champs cibles
    final = {key: result.get(key, "Non détecté") for key in field_keys}
    return final

# 📥 Interface utilisateur Streamlit
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

    # OCR brut
    raw_text = ocr_space_api(img_bytes)
    with st.expander("📄 Texte OCR brut"):
        st.text(raw_text)

    # Extraction finale par indexation + alias
    results = index_and_match_fields_with_alias(raw_text, target_fields, field_aliases)

    st.subheader("📊 Champs techniques extraits :")
    for key in target_fields:
        st.write(f"🔹 **{key}** → {results.get(key)}")
