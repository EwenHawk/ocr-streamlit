import streamlit as st
import requests
from PIL import Image
import io
import re

st.set_page_config(page_title="OCR Technique ciblée", page_icon="🔍", layout="centered")
st.title("🧠 OCR ciblé – Lecture humaine ligne par ligne")

# ✅ Champs d'intérêt
target_fields = ["Pmax", "Vpm", "Ipm", "Voc", "Isc"]

# 🧠 Correspondances souples pour variations OCR
field_aliases = {
    "pmax": "Pmax",
    "vpm": "Vpm",
    "ipm": "Ipm",
    "lpm": "Ipm",  # variante OCR
    "voc": "Voc",
    "isc": "Isc",
}

# 📉 Prétraitement image
def preprocess_image(img):
    max_width = 1024
    if img.width > max_width:
        ratio = max_width / img.width
        new_height = int(img.height * ratio)
        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
    return img

# 📤 Appel OCR avec overlay
def ocr_space_with_overlay(img_bytes, api_key="helloworld"):
    try:
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
    except Exception as e:
        return {"Error": str(e)}

# 🔍 Lecture ligne par ligne souple et ciblée
def extract_target_fields(parsed_result, target_fields, aliases):
    lines = parsed_result.get("TextOverlay", {}).get("Lines", [])
    results = {}
    found = set()

    for line in lines:
        content = line.get("LineText", "")
        # Nettoyage & normalisation
        lower_line = content.lower()
        for raw_key in aliases:
            if raw_key in lower_line and aliases[raw_key] in target_fields:
                # Extrait la première valeur numérique raisonnable
                match = re.search(r"(\d+[.,]?\d*\s*[A-Za-z%Ω]*)", content)
                if match:
                    results[aliases[raw_key]] = match.group(1)
                    found.add(aliases[raw_key])
                    break
        if len(found) == len(target_fields):
            break
    return results

# 📥 Interface utilisateur
uploaded_file = st.file_uploader("📤 Image contenant des champs techniques", type=["jpg", "jpeg", "png"])
if uploaded_file:
    img = Image.open(uploaded_file)

    rotation = st.selectbox("Rotation ?", [0, 90, 180, 270], index=0)
    if rotation:
        img = img.rotate(-rotation, expand=True)

    img = preprocess_image(img)
    st.image(img, caption="🖼️ Image traitée", use_container_width=True)

    # Compression
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG", quality=70)
    img_bytes.seek(0)

    # OCR
    parsed = ocr_space_with_overlay(img_bytes)
    raw_text = parsed.get("ParsedText", "❌ Texte non disponible")

    with st.expander("📄 Texte OCR brut"):
        st.text(raw_text)

    # Extraction ciblée
    results = extract_target_fields(parsed, target_fields, field_aliases)

    st.subheader("📊 Valeurs extraites ciblées :")
    for field in target_fields:
        value = results.get(field, "Non détecté")
        st.write(f"🔹 **{field}** : {value}")
