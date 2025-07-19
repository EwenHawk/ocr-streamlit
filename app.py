import streamlit as st
import requests
from PIL import Image
import io

st.set_page_config(page_title="OCR Technique", page_icon="🔍", layout="centered")
st.title("📸 Analyseur OCR Technique")

# 🔗 Détection de bloc de champs suivi de valeurs
def extract_ordered_pairs(text, field_keys):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    result = {}
    label_indices = []

    # Trouve les lignes contenant les champs attendus
    for i, line in enumerate(lines):
        label = line.lower().rstrip(":")
        if label in [f.lower() for f in field_keys]:
            label_indices.append((i, line.strip()))

    # S’il y a assez de valeurs après les libellés
    if label_indices and len(lines) >= label_indices[-1][0] + len(label_indices) + 1:
        start_val = label_indices[-1][0] + 1
        values = lines[start_val : start_val + len(label_indices)]
        for idx, (i, label) in enumerate(label_indices):
            result[label.rstrip(":")] = values[idx].strip()
    else:
        result = {"Erreur": "Bloc de champs ou valeurs incomplet"}

    return result

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

# 📥 Chargement de l’image
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

    # 🧠 Extraction par structure ordonnée
    field_keys = ["Irr Meas", "Irr Corr", "Voc", "Isc", "Pmax", "Vpm", "Ipm", "Eff,c", "Eff,m", "Rsh"]
    extracted = extract_ordered_pairs(raw_text, field_keys)

    # 📊 Affichage des résultats
    st.subheader("📊 Valeurs extraites :")
    for k in field_keys:
        val = extracted.get(k, "Non détecté")
        st.write(f"🔹 **{k}** : {val}")
