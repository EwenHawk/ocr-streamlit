import streamlit as st
import requests
from PIL import Image
import io
import re
from streamlit_drawable_canvas import st_canvas

# 🎯 Champs techniques à extraire
target_fields = ["Voc", "Isc", "Pmax", "Vpm", "Ipm"]
field_aliases = {
    "voc": "Voc", "isc": "Isc", "pmax": "Pmax",
    "vpm": "Vpm", "ipm": "Ipm", "lpm": "Ipm"
}

# ⚙️ Config page Streamlit
st.set_page_config(page_title="OCR intelligent", page_icon="🔎", layout="centered")
st.title("🧠 OCR Indexé + Zone interactive")

# 🧼 Prétraitement de l’image
def preprocess_image(img, rotation):
    if rotation:
        img = img.rotate(-rotation, expand=True)
    max_width = 1024
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.Resampling.LANCZOS)
    return img

# 🔍 Appel API OCR.Space
def ocr_space_api(img_bytes, api_key="helloworld"):  # ← Remplace par ta clé API
    try:
        response = requests.post(
            "https://api.ocr.space/parse/image",
            files={"filename": ("image.jpg", img_bytes, "image/jpeg")},
            data={"apikey": api_key, "language": "eng", "isOverlayRequired": False}
        )
        result = response.json()
        return result.get("ParsedResults", [{}])[0].get("ParsedText", "")
    except Exception as e:
        return f"[Erreur OCR] {e}"

# 🧠 Indexation du texte OCR
def index_and_match_fields_with_alias(text, field_keys, aliases):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    raw_fields, raw_values = [], []
    for line in lines:
        if line.endswith(":"):
            clean = line.rstrip(":").lower().strip()
            if clean in aliases:
                raw_fields.append(aliases[clean])
    for line in lines:
        match = re.match(r"^\d+[.,]?\d*\s*[A-Za-z%ΩVWAm]*$", line)
        if match:
            raw_values.append(match.group(0).strip())
    result = {raw_fields[i]: raw_values[i] for i in range(min(len(raw_fields), len(raw_values)))}
    return {key: result.get(key, "Non détecté") for key in field_keys}

# 📥 Upload de l’image
uploaded_file = st.file_uploader("📤 Importer une image technique", type=["jpg", "jpeg", "png"])
if uploaded_file:
    img = Image.open(uploaded_file)
    rotation = st.selectbox("🔁 Rotation ?", [0, 90, 180, 270], index=0)
    img = preprocess_image(img, rotation)
    st.image(img, caption="🖼️ Image traitée", use_container_width=True)

    # 🟧 Rectangle initial à déplacer/redimensionner
    st.markdown("### 🔲 Sélectionne la zone d’analyse avec le rectangle")
    initial_rect = [{
        "type": "rect",
        "left": img.width // 4,
        "top": img.height // 4,
        "width": img.width // 2,
        "height": img.height // 3,
        "fill": "rgba(255,165,0,0.3)",
        "stroke": "orange",
        "strokeWidth": 2
    }]

    canvas_result = st_canvas(
        background_image=img,
        initial_drawing=initial_rect,
        drawing_mode="transform",  # ← Permet déplacement + resize
        update_streamlit=True,
        height=img.height,
        width=img.width,
        key="canvas"
    )

    # 📌 Rognage de la zone sélectionnée
    if canvas_result.json_data and canvas_result.json_data["objects"]:
        rect = canvas_result.json_data["objects"][0]
        x, y = rect["left"], rect["top"]
        w, h = rect["width"], rect["height"]
        cropped_img = img.crop((x, y, x + w, y + h))
        st.image(cropped_img, caption="📌 Zone sélectionnée", use_container_width=True)

        # 🔍 OCR sur la zone rognée
        img_bytes = io.BytesIO()
        cropped_img.save(img_bytes, format="JPEG", quality=70)
        img_bytes.seek(0)

        raw_text = ocr_space_api(img_bytes)
        with st.expander("📄 Texte OCR brut"):
            st.text(raw_text)

        results = index_and_match_fields_with_alias(raw_text, target_fields, field_aliases)
        st.subheader("📊 Résultats extraits :")
        for key in target_fields:
            st.write(f"🔹 **{key}** → {results.get(key)}")
    else:
        st.info("🖱️ Déplace le rectangle et relâche pour lancer l’analyse.")
