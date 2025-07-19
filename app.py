import pytesseract
from PIL import Image
import requests
import re
from io import BytesIO

# 📌 Champs à extraire
TARGET_FIELDS = ["pmax", "voc", "isc", "vpm", "imp"]

# 🧹 Nettoyage du texte
def clean(text):
    return re.sub(r"\s+", " ", text.strip().lower())

# 🔍 Fonction principale
def extract_fields_from_url(image_url):
    response = requests.get(image_url)
    img = Image.open(BytesIO(response.content))

    raw_text = pytesseract.image_to_string(img, lang='eng')
    results = {}

    for line in raw_text.split('\n'):
        line_clean = clean(line)
        for field in TARGET_FIELDS:
            match = re.search(rf"{field}\s*:\s*([\w\.\-]+)", line_clean, re.IGNORECASE)
            if match:
                results[field.upper()] = match.group(1)

    return results

# 🧪 Exemple d’utilisation
if __name__ == "__main__":
    image_url = "https://raw.githubusercontent.com/EwenHawk/ocr-streamlit/main/.devcontainer/1000079278.jpg"
    specs = extract_fields_from_url(image_url)
    print("🔧 Champs détectés :", specs)
