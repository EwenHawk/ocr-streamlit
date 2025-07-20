import streamlit as st
import requests
from PIL import Image
import io
import re
from streamlit_drawable_canvas import st_canvas

# ⚙️ Config de la page
st.set_page_config(page_title="OCR Indexé Intelligent", page_icon="🧠", layout="centered")
st.title("🔗 Lecture OCR par indexation + alias + rognage visuel")

# 🎯 Champs à extraire
target_fields = ["Voc", "Isc", "Pmax", "Vpm", "Ipm"]

# 🧠 Alias OCR tolérants
field_aliases = {
    "voc": "Voc",
    "isc": "Isc",
    "pmax": "Pmax",
    "vpm": "Vpm",
    "ipm": "Ipm",
    "lpm": "Ipm"
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

# 🔍 Appel OCR.Space
def ocr_space_api(img_bytes, api_key="helloworld"):
    try:
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
        return result.get("ParsedResults", [{}])[0].get("ParsedText", "")
    except Exception as e:
        return f"[Erreur OCR] {e}"

# 🔢 Indexation texte OCR
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
    return {key: result.get(key, "Non détecté") for key in field_keys}

# 📥 UI : upload image
uploaded_file = st.file_uploader("📤 Importer une image technique", type=["jpg", "jpeg", "png"])
if uploaded_file:
    img = Image.open(uploaded_file)
    rotation = st.selectbox("🔁 Rotation ?", [0, 90, 180, 270], index=0)
    img = preprocess_image(img, rotation)
    st.image(img, caption="🖼️ Image traitée", use_container_width=True)

    # 🖋️ Canvas de sélection
    st.markdown("### ✏️ Dessine la zone à analyser")
    canvas_result = st_canvas(
        fill_color="rgba(255, 165, 0, 0.3)",
        stroke_width=2,
        background_image=img,
        update_streamlit=True,
        height=img.height,
        width=img.width,
        drawing_mode="rect",
        key="canvas",
    )

    # ✂️ Rognage de la zone dessinée
    if canvas_result.json_data and canvas_result.json_data["objects"]:
        rect = canvas_result.json_data["objects"][0]
        x, y, w, h = rect["left"], rect["top"], rect["width"], rect["height"]
        cropped_img = img.crop((x, y, x + w, y + h))
        st.image(cropped_img, caption="📌 Zone sélectionnée", use_container_width=True)

        # 🧃 OCR sur zone rognée
        img_bytes = io.BytesIO()
        cropped_img.save(img_bytes, format="JPEG", quality=70)
        img_bytes.seek(0)

        raw_text = ocr_space_api(img_bytes)
        with st.expander("📄 Texte OCR brut"):
            st.text(raw_text)

        # 📊 Indexation intelligente
        results = index_and_match_fields_with_alias(raw_text, target_fields, field_aliases)
        st.subheader("📊 Champs techniques extraits :")
        for key in target_fields:
            st.write(f"🔹 **{key}** → {results.get(key)}")
    else:
        st.info("➡️ Dessine un rectangle sur l’image pour lancer l’analyse OCR.")
