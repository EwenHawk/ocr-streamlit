import streamlit as st
import requests
from PIL import Image
import io
import re

st.set_page_config(page_title="OCR Associatif", page_icon="🔗", layout="centered")
st.title("🔗 Lecture OCR par détection libre")

target_fields = ["Voc", "Isc", "Pmax", "Vpm", "Ipm"]

# 📉 Compression & rotation
def preprocess_image(img, rotation):
    if rotation:
        img = img.rotate(-rotation, expand=True)
    max_width = 1024
    if img.width > max_width:
        ratio = max_width / img.width
        new_height = int(img.height * ratio)
        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
    return img

# 🔍 Appel OCR brut
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

# 🧠 Association champ + première valeur chiffrée ensuite
def find_fields_and_values(text, field_keys):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    result = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        for field in field_keys:
            if field.lower() in line.lower() and field not in result:
                # Cherche la première valeur plus loin
                for j in range(i + 1, len(lines)):
                    match = re.search(r"\d+[.,]?\d*\s*[A-Za-z%ΩVAmW]*", lines[j])
                    if match:
                        result[field] = match.group(0).strip()
                        break
        i += 1
    return result

uploaded_file = st.file_uploader("📤 Importer une image", type=["jpg", "jpeg", "png"])
if uploaded_file:
    img = Image.open(uploaded_file)
    rotation = st.selectbox("🔁 Rotation ?", [0, 90, 180, 270], index=0)
    img = preprocess_image(img, rotation)
    st.image(img, caption="🖼️ Image préparée", use_container_width=True)

    # Compression
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG", quality=70)
    img_bytes.seek(0)

    raw_text = ocr_space_api(img_bytes)
    with st.expander("📄 Texte OCR brut"):
        st.text(raw_text)

    results = find_fields_and_values(raw_text, target_fields)
    st.subheader("📊 Valeurs associées automatiquement :")
    for field in target_fields:
        value = results.get(field, "Non détecté")
        st.write(f"🔹 **{field}** → {value}")
