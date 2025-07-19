import streamlit as st
import requests
from PIL import Image
import io
import re

st.set_page_config(page_title="OCR Technique Ciblée", page_icon="🔍", layout="centered")
st.title("🔍 Lecture technique ciblée – Tous les champs doivent être détectés")

# ✅ Champs d'intérêt
target_fields = ["Pmax", "Vpm", "Ipm", "Voc", "Isc"]

# 🧠 Correspondance souple des libellés OCR
field_aliases = {
    "pmax": "Pmax",
    "vpm": "Vpm",
    "ipm": "Ipm",
    "lpm": "Ipm",   # Variante OCR
    "voc": "Voc",
    "isc": "Isc",
    "isc.": "Isc"
}

# 📉 Prétraitement image
def preprocess_image(img):
    max_width = 1024
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.Resampling.LANCZOS)
    return img

# 🔍 OCR avec overlay spatial
def ocr_space_with_overlay(img_bytes, api_key="helloworld"):
    response = requests.post(
        "https://api.ocr.space/parse/image",
        files={"filename": ("image.jpg", img_bytes, "image/jpeg")},
        data={
            "apikey": api_key,
            "language": "eng",
            "isOverlayRequired": True
        }
    )
    result = response.json()
    return result.get("ParsedResults", [])[0]

# 🧠 Lecture ligne par ligne + association champ/valeur
def extract_target_fields(parsed_result, target_fields, aliases):
    lines = parsed_result.get("TextOverlay", {}).get("Lines", [])
    results = {}

    for line in lines:
        content = line.get("LineText", "")
        lower_line = content.lower()

        for raw_key, true_key in aliases.items():
            if raw_key in lower_line and true_key in target_fields and true_key not in results:
                match = re.search(r"(\d+[.,]?\d*\s*[A-Za-z%Ω]*)", content)
                if match:
                    results[true_key] = match.group(1)
                else:
                    results[true_key] = "Non détecté"

        if len(results) == len(target_fields):
            break

    return results

# 📥 Interface Streamlit
uploaded_file = st.file_uploader("📤 Importer une image technique", type=["jpg", "jpeg", "png"])
if uploaded_file:
    img = Image.open(uploaded_file)

    rotation = st.selectbox("Rotation de l’image ?", [0, 90, 180, 270], index=0)
    if rotation:
        img = img.rotate(-rotation, expand=True)

    img = preprocess_image(img)
    st.image(img, caption="🖼️ Image traitée", use_container_width=True)

    # Compression
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG", quality=70)
    img_bytes.seek(0)

    # 🔍 OCR
    parsed = ocr_space_with_overlay(img_bytes)
    raw_text = parsed.get("ParsedText", "")
    with st.expander("📄 Texte OCR brut"):
        st.text(raw_text)

    # 🧠 Extraction ciblée stricte
    results = extract_target_fields(parsed, target_fields, field_aliases)

    st.subheader("📊 Résultats extraits")
    if len(results) == len(target_fields):
        for field in target_fields:
            st.write(f"✅ **{field}** : {results[field]}")
    else:
        st.warning("⚠️ Tous les champs n’ont pas été détectés correctement. Essayez une image plus lisible.")
