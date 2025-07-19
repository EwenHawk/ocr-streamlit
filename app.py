import streamlit as st
import requests
from PIL import Image
import io
import re

st.set_page_config(page_title="OCR Technique", page_icon="🔍", layout="centered")
st.title("📸 Analyseur OCR Technique")

uploaded_file = st.file_uploader("Importer une image (JPG, PNG)", type=["jpg", "jpeg", "png"])

# Fonction API OCR.space
def ocr_space_api(img_bytes, api_key="helloworld"):
    response = requests.post(
        "https://api.ocr.space/parse/image",
        files={"filename": ("image.png", img_bytes, "image/png")},
        data={
            "apikey": api_key,
            "language": "eng",
            "isOverlayRequired": False
        }
    )
    result = response.json()

    if result.get("IsErroredOnProcessing"):
        return "⚠️ Erreur API : " + result.get("ErrorMessage", ["Erreur inconnue"])[0]

    try:
        return result["ParsedResults"][0]["ParsedText"]
    except (KeyError, IndexError):
        return "⚠️ Résultat introuvable dans la réponse de l'API."

# Fonction d’extraction des champs techniques
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

# Traitement si fichier importé
if uploaded_file:
    img = Image.open(uploaded_file)

    # 🧭 Sélecteur de rotation pour redresser l’image si besoin
    rotation = st.selectbox("Rotation de l’image (en degrés)", [0, 90, 180, 270], index=0)
    if rotation != 0:
        img = img.rotate(-rotation, expand=True)

    st.image(img, caption="Image redressée", use_container_width=True)

    # 🔄 Conversion en bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    # 🔍 OCR via l’API
    text = ocr_space_api(img_bytes)

    # 📄 Affichage du texte brut
    with st.expander("📄 Texte OCR brut"):
        st.text(text)

    # 📊 Extraction des champs
    st.subheader("📊 Champs techniques extraits")
    results = extract_fields(text)
    for k, v in results.items():
        st.write(f"✅ **{k}** : {v}")
