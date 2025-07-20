import streamlit as st
import requests
from PIL import Image
import io
import re
from streamlit_drawable_canvas import st_canvas
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Configuration de la page
st.set_page_config(page_title="OCR ToolJet", page_icon="📄", layout="centered")
st.title("📤 OCR interactif + validation vers Google Sheet")

# Champs à extraire
target_fields = ["Voc", "Isc", "Pmax", "Vpm", "Ipm"]
field_aliases = {
    "voc": "Voc", "isc": "Isc", "pmax": "Pmax",
    "vpm": "Vpm", "ipm": "Ipm", "lpm": "Ipm"
}

# 📐 Prétraitement image
def preprocess_image(img, rotation):
    if rotation:
        img = img.rotate(-rotation, expand=True)
    max_width = 1024
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.Resampling.LANCZOS)
    return img

# 🔍 OCR via API OCR.Space
def ocr_space_api(img_bytes, api_key="helloworld"):
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

# 🔠 Analyse du texte OCR
def index_and_match_fields_with_alias(text, field_keys, aliases):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    raw_fields, raw_values = [], []
    for line in lines:
        if line.endswith(":"):
            key = line.rstrip(":").lower().strip()
            if key in aliases:
                raw_fields.append(aliases[key])
    for line in lines:
        match = re.match(r"^\d+[.,]?\d*\s*[A-Za-z%ΩVWAm]*$", line)
        if match:
            raw_values.append(match.group(0).strip())
    result = {raw_fields[i]: raw_values[i] for i in range(min(len(raw_fields), len(raw_values)))}
    return {key: result.get(key, "Non détecté") for key in field_keys}

# 🔗 Connexion à Google Sheets
def connect_to_tooljet_sheet(json_path, sheet_url, worksheet_title):
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(json_path, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(sheet_url).worksheet(worksheet_title)
    return sheet

# 📥 Chargement de l’image
uploaded_file = st.file_uploader("📸 Importer une image technique", type=["jpg", "jpeg", "png"])
if uploaded_file:
    img = Image.open(uploaded_file)
    rotation = st.selectbox("🔁 Rotation ?", [0, 90, 180, 270], index=0)
    img = preprocess_image(img, rotation)
    canvas_width, canvas_height = img.size
    st.image(img, caption="🖼️ Image affichée", use_container_width=False)

    st.markdown("### 🟧 Déplace ou ajuste le rectangle de sélection")

    # Rectangle initial
    initial_rect = {
        "objects": [{
            "type": "rect",
            "left": canvas_width // 4,
            "top": canvas_height // 4,
            "width": canvas_width // 2,
            "height": canvas_height // 3,
            "fill": "rgba(255,165,0,0.3)",
            "stroke": "orange",
            "strokeWidth": 2
        }]
    }

    canvas_result = st_canvas(
        background_image=img,
        initial_drawing=initial_rect,
        drawing_mode="transform",
        update_streamlit=True,
        height=canvas_height,
        width=canvas_width,
        key="canvas"
    )

    if canvas_result.json_data and canvas_result.json_data["objects"]:
        rect = canvas_result.json_data["objects"][0]
        x, y = rect["left"], rect["top"]
        w, h = rect["width"], rect["height"]
        cropped_img = img.crop((x, y, x + w, y + h))
        st.image(cropped_img, caption="📌 Zone sélectionnée", use_container_width=False)

        img_bytes = io.BytesIO()
        cropped_img.save(img_bytes, format="JPEG", quality=70)
        img_bytes.seek(0)
        raw_text = ocr_space_api(img_bytes)

        with st.expander("📄 Texte OCR brut"):
            st.text(raw_text)

        results = index_and_match_fields_with_alias(raw_text, target_fields, field_aliases)
        st.subheader("📊 Champs extraits :")
        for key in target_fields:
            st.write(f"🔹 **{key}** → {results.get(key)}")

        # 📤 Bouton de validation
        st.markdown("---")
        if st.button("✅ Je valide les données"):
            try:
                # Paramètres de ta Google Sheet
                sheet_url = "https://docs.google.com/spreadsheets/d/1yhIVYOqibFnhKKCnbhw8v0f4n1MbfY_4uZhSotK44gc/edit"
                worksheet_name = "Feuille 1"  # adapte si nécessaire
                json_path = "config/tooljet-ocr.json"  # à adapter selon emplacement réel

                sheet = connect_to_tooljet_sheet(json_path, sheet_url, worksheet_name)
                row = [results.get(key, "") for key in target_fields]
                sheet.append_row(row)
                st.success("✅ Résultats envoyés dans ton Google Sheet ToolJet !")
            except Exception as e:
                st.error(f"❌ Échec de l'envoi : {e}")
    else:
        st.info("🖱️ Ajuste le rectangle pour définir la zone d'analyse.")
