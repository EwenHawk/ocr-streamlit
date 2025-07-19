import streamlit as st
import requests
from PIL import Image
import io
import re

st.set_page_config(page_title="OCR Technique", page_icon="🔍", layout="centered")
st.title("📸 Analyseur OCR Technique")

# 🔧 Corrige les libellés suivis de valeurs sur une ligne différente
def fix_text_alignment(text):
    lines = text.splitlines()
    fixed_lines = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if re.match(r"^(Voc|Isc|Pmax|Vpm|Ipm)\s*[:=]?\s*$", line, re.IGNORECASE):
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                fixed_lines.append(f"{line} {next_line}")
                i += 2
            else:
                fixed_lines.append(line)
                i += 1
        else:
            fixed_lines.append(line)
            i += 1
    return "\n".join(fixed_lines)

# 🔗 Associe les libellés et valeurs par position si séparés
def pair_fields_by_order(text, field_keys):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    labels = [line for line in lines if any(field.lower() in line.lower() for field in field_keys)]
    values = [line for line in lines if not any(field.lower() in line.lower() for field in field_keys)]
    result = {}
    for i in range(min(len(labels), len(values))):
        label = labels[i].split(":")[0].strip().capitalize()
        value = values[i].strip()
        result[label] = value
    return result

# 🔌 Appel sécurisé à OCR.space
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
    except ValueError:
        return "⚠️ Erreur : Réponse non JSON reçue."

    if not isinstance(result, dict):
        return f"⚠️ Réponse inattendue : {result}"

    if result.get("IsErroredOnProcessing"):
        return "⚠️ Erreur API : " + result.get("ErrorMessage", ["Erreur inconnue"])[0]

    try:
        return result["ParsedResults"][0]["ParsedText"]
    except (KeyError, IndexError):
        return "⚠️ Résultat OCR introuvable."

# 🔍 Extraction technique avec Regex
def extract_fields(text):
    def get(rx):
        m = re.search(rx, text, re.IGNORECASE)
        return m.group(1) if m else "Non détecté"
    convert = lambda v: round(float(v.replace(",", ".")), 2) if v not in ["", "Non détecté"] else v
    return {
        "Pmax": convert(get(r"Pmax\s*[:=]?\s*(\d+[.,]?\d*)")),
        "Vpm":  convert(get(r"Vpm\s*[:=]?\s*(\d+[.,]?\d*)")),
        "Ipm":  convert(get(r"Ipm\s*[:=]?\s*(\d+[.,]?\d*)")),
        "Voc":  convert(get(r"Voc\s*[:=]?\s*(\d+[.,]?\d*)")),
        "Isc":  convert(get(r"Isc\s*[:=]?\s*(\d+[.,]?\d*)")),
    }

# 📥 Interface utilisateur
uploaded_file = st.file_uploader("Importer une image (JPG, PNG)", type=["jpg", "jpeg", "png"])
if uploaded_file:
    img = Image.open(uploaded_file)

    # 🔁 Rotation
    rotation = st.selectbox("Rotation de l’image (en degrés)", [0, 90, 180, 270], index=0)
    if rotation != 0:
        img = img.rotate(-rotation, expand=True)

    # 📉 Redimensionnement si image trop large
    max_width = 1024
    if img.width > max_width:
        ratio = max_width / float(img.width)
        new_height = int(float(img.height) * ratio)
        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

    st.image(img, caption="Image traitée", use_container_width=True)

    # 💾 Compression JPEG avec qualité réduite
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG", quality=70)
    img_bytes.seek(0)

    # 🔍 OCR via API
    raw_text = ocr_space_api(img_bytes)
    with st.expander("📄 Texte OCR brut"):
        st.text(raw_text)

    # 🧠 Reconstruction du texte
    fixed_text = fix_text_alignment(raw_text)

    # 📊 Extraction des valeurs par position
    field_keys = ["Pmax", "Vpm", "Ipm", "Voc", "Isc"]
    paired = pair_fields_by_order(fixed_text, field_keys)

    # 📊 Extraction par regex
    regexed = extract_fields(fixed_text)

    st.subheader("🔗 Extraction par position (alignement)")
    for k in field_keys:
        val = paired.get(k.capitalize(), "Non détecté")
        st.write(f"🔹 **{k}** : {val}")

    st.subheader("✅ Extraction par regex")
    for k, v in regexed.items():
        st.write(f"✅ **{k}** : {v}")
