import streamlit as st
import requests
from PIL import Image
import io
import re

st.set_page_config(page_title="OCR Ligne Technique", page_icon="📏", layout="centered")
st.title("🧠 Analyse OCR par lignes – Lecture humaine")

target_fields = ["Pmax", "Vpm", "Ipm", "Voc", "Isc"]

def preprocess_image(img):
    max_width = 1024
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.Resampling.LANCZOS)
    return img

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

def extract_from_lines(parsed_result, field_keys):
    lines = parsed_result.get("TextOverlay", {}).get("Lines", [])
    result = {}
    found_fields = set()

    for line in lines:
        content = line.get("LineText", "")
        for field in field_keys:
            if re.search(fr"\b{field}\b", content, re.IGNORECASE):
                value_match = re.search(r"(\d+[.,]?\d*\s*[A-Za-z%Ω]*)", content)
                result[field] = value_match.group(1) if value_match else "Non détecté"
                found_fields.add(field)
                break
        if len(found_fields) == len(field_keys):
            break
    return result

uploaded_file = st.file_uploader("📤 Image contenant des champs techniques", type=["jpg", "jpeg", "png"])
if uploaded_file:
    img = Image.open(uploaded_file)

    rotation = st.selectbox("Rotation de l’image", [0, 90, 180, 270], index=0)
    if rotation:
        img = img.rotate(-rotation, expand=True)

    img = preprocess_image(img)
    st.image(img, caption="🖼️ Image préparée", use_container_width=True)

    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG", quality=70)
    img_bytes.seek(0)

    parsed = ocr_space_with_overlay(img_bytes)
    text = parsed.get("ParsedText", "❌ Texte non disponible")
    with st.expander("📄 Texte OCR brut"):
        st.text(text)

    st.subheader("📊 Valeurs extraites (lecture ligne par ligne) :")
    results = extract_from_lines(parsed, target_fields)
    for key in target_fields:
        val = results.get(key, "Non détecté")
        st.write(f"🔹 **{key}** : {val}")
