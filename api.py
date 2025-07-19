from fastapi import FastAPI
from pydantic import BaseModel
from PIL import Image, ImageEnhance
import pytesseract
import base64
import io
import re

app = FastAPI()

# 🎯 Champs d’intérêt
TARGET_FIELDS = ["Voc", "Isc", "Pmax", "Vpm", "Ipm"]

# 🔁 Aliases pour corriger erreurs OCR
FIELD_ALIASES = {
    "voc": "Voc",
    "isc": "Isc",
    "pmax": "Pmax",
    "vpm": "Vpm",
    "ipm": "Ipm",
    "lpm": "Ipm"  # erreur fréquente OCR
}

class ImageInput(BaseModel):
    base64: str

# 🖼️ Prétraitement image
def preprocess_image(base64_str):
    img_data = base64.b64decode(base64_str)
    img = Image.open(io.BytesIO(img_data))
    img = img.convert("L")  # grayscale
    img = img.resize((img.width // 2, img.height // 2))  # compression
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.1)
    return img

# 🧠 OCR + indexation + matching
def extract_values(img):
    text = pytesseract.image_to_string(img, lang='eng')
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    fields = []
    values = []

    for line in lines:
        raw = line.lower().rstrip(":")
        if raw in FIELD_ALIASES:
            fields.append(FIELD_ALIASES[raw])

    for line in lines:
        match = re.match(r"^\d+[.,]?\d*\s*[A-Za-z%ΩVWAm]*$", line)
        if match:
            values.append(match.group(0).strip())
        if len(values) >= len(fields):
            break

    result = {}
    for i in range(min(len(fields), len(values))):
        result[fields[i]] = values[i]

    return {f: result.get(f, None) for f in TARGET_FIELDS}

# 🚀 Endpoint API
@app.post("/extract")
def extract_ocr(data: ImageInput):
    try:
        image = preprocess_image(data.base64)
        extracted = extract_values(image)
        return { "fields": extracted }
    except Exception as e:
        return { "error": str(e) }