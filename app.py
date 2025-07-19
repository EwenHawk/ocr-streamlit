import streamlit as st
import requests
from PIL import Image
import io

st.set_page_config(page_title="OCR Technique", page_icon="🔍", layout="centered")
st.title("📸 Analyseur OCR Technique")

# 🧠 Correspondance des noms OCRisés avec les vrais noms de champs
field_map = {
    "irr meas": "Irr Meas",
    "irr corr": "Irr Corr",
    "voc": "Voc",
    "isc": "Isc",
    "pmax": "Pmax",
    "vpm": "Vpm",
    "ipm": "Ipm",
    "lpm": "Ipm",       # variante OCR fréquente
    "eff,c": "Eff,c",
    "eff,m": "Eff,m",
    "rsh": "Rsh"
}

# 🔗 Fonction qui aligne les champs et les valeurs
def extract_ordered_pairs(text, field_map):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    detected_fields = []

    # Collecte les lignes correspondant aux clés de field_map
    for line in lines:
        key = line.lower().rstrip(":")
        if key in field_map:
            detected_fields.append(field_map[key])

    # Recherche bloc de valeurs après le dernier champ détecté
    if detected_fields:
        last_label_index = next(i for i, line in enumerate(lines) if line.lower().startswith(list(field_map.keys())[-1]))
        values = lines[last_label_index + 1 : last_label_index + 1 + len(detected_fields)]

        result = {}
        for i in range(len(detected_fields)):
            label = detected_fields[i]
            value = values[i].strip() if i < len(values) else "Non détecté"
            result[label] = value
        return result
    else:
        return {"Erreur": "Aucun champ reconnu."}

# 🔌 Appel OCR.space
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
        return "⚠️ Erreur : réponse non JSON."
    if not isinstance(result, dict):
        return f"⚠️ Réponse inattendue : {result}"
    if result.get("IsErroredOnProcessing"):
        return "⚠️ Erreur API : " + result.get("ErrorMessage", ["Erreur inconnue"])[0]
    try:
        return result["ParsedResults"][0]["ParsedText"]
    except (KeyError, IndexError):
        return "⚠️ Résultat OCR introuvable."

# 📥 Interface utilisateur
uploaded_file = st.file_uploader("Importer une image (JPG ou PNG)", type=["jpg", "jpeg", "png"])
if uploaded_file:
    img = Image.open(uploaded_file)

    # 🔁 Rotation
    rotation = st.selectbox("Rotation de l’image", [0, 90, 180, 270], index=0)
    if rotation:
        img = img.rotate(-rotation, expand=True)

    # 📉 Compression pour respecter la limite de 1 Mo
    max_width = 1024
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.Resampling.LANCZOS)

    st.image(img, caption="Image préparée", use_container_width=True)

    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG", quality=70)
    img_bytes.seek(0)

    # 🔍 Lecture OCR
    raw_text = ocr_space_api(img_bytes)
    with st.expander("📄 Texte OCR brut"):
        st.text(raw_text)

    # 📊 Extraction intelligente par correspondance
    results = extract_ordered_pairs(raw_text, field_map)

    st.subheader("📊 Valeurs extraites :")
    for k in field_map.values():
        val = results.get(k, "Non détecté")
        st.write(f"🔹 **{k}** : {val}")
