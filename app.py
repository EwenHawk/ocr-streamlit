import streamlit as st
import requests
from PIL import Image
import io

st.set_page_config(page_title="OCR Technique", page_icon="🔍", layout="centered")
st.title("📸 Analyseur OCR Technique")

# 🔗 Associe les libellés et valeurs par ordre d’apparition
def pair_fields_by_order(text, field_keys):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    labels = [line for line in lines if any(field.lower() in line.lower() for field in field_keys)]
    values = [line for line in lines if not any(field.lower() in line.lower() for field in field_keys)]
    result = {}
    for i in range(min(len(labels), len(values))):
        label = labels[i].split(":")[0].strip()
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
uploaded_file = st.file_uploader("Importer une image (JPG, PNG)", type=["jpg", "jpeg", "png"])
if uploaded_file:
    img = Image.open(uploaded_file)

    # 🔁 Rotation (sélection utilisateur)
    rotation = st.selectbox("Rotation de l’image (en degrés)", [0, 90, 180, 270], index=0)
    if rotation != 0:
        img = img.rotate(-rotation, expand=True)

    # 📉 Redimensionnement si image trop large
    max_width = 1024
    if img.width > max_width:
        ratio = max_width / float(img.width)
        new_height = int(float(img.height) * ratio)
        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

    st.image(img, caption="Image redressée", use_container_width=True)

    # 💾 Compression JPEG pour réduire la taille
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG", quality=70)
    img_bytes.seek(0)

    # 🔍 Lecture OCR
    raw_text = ocr_space_api(img_bytes)
    with st.expander("📄 Texte OCR brut"):
        st.text(raw_text)

    # 📊 Extraction par ordre
    field_keys = ["Pmax", "Vpm", "Ipm", "Voc", "Isc"]
    results = pair_fields_by_order(raw_text, field_keys)

    st.subheader("📊 Valeurs extraites par alignement :")
    for k in field_keys:
        val = results.get(k, "Non détecté")
        st.write(f"🔹 **{k}** : {val}")
