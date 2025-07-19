import pytesseract
from PIL import Image
import re

# 📌 Liste des champs à rechercher (insensible à la casse)
TARGET_FIELDS = ["pmax", "voc", "isc", "vpm", "imp"]

# 🧹 Fonction de nettoyage du texte
def clean(text):
    return re.sub(r"\s+", " ", text.strip().lower())

# 🧠 Fonction principale
def extract_spec_fields(image_path):
    # Chargement de l'image
    img = Image.open(image_path)

    # OCR avec Tesseract
    raw_text = pytesseract.image_to_string(img, lang='eng')

    results = {}

    # Balayage ligne par ligne
    for line in raw_text.split('\n'):
        line_clean = clean(line)
        for field in TARGET_FIELDS:
            # Regex: cherche "champ : valeur"
            match = re.search(rf"{field}\s*:\s*([\w\.\-]+)", line_clean, re.IGNORECASE)
            if match:
                results[field.upper()] = match.group(1)

    return results

# 🔍 Exemple d’utilisation
if __name__ == "__main__":
    image_file = "path/to/your/image.jpg"  # Remplace avec ton chemin local
    specs = extract_spec_fields(image_file)
    print("🔧 Champs détectés :", specs)
