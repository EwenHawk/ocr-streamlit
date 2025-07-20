import streamlit as st
import requests
from PIL import Image
import io
import re
from streamlit_drawable_canvas import st_canvas
import gspread
from google.oauth2.service_account import Credentials

# Config
st.set_page_config(page_title="OCR ToolJet", page_icon="📄", layout="centered")
st.title("📤 OCR technique + validation ToolJet")

target_fields = ["Voc", "Isc", "Pmax", "Vpm", "Ipm"]
field_aliases = {
    "voc": "Voc", "isc": "Isc", "pmax": "Pmax",
    "vpm": "Vpm", "ipm": "Ipm", "lpm": "Ipm"
}

# OCR function
def ocr_space_api(img_bytes, api_key="helloworld"):
    try:
        response = requests.post(
            "https://api.ocr.space/parse/image",
            files={"filename": ("image.jpg", img_bytes, "image/jpeg")},
            data={"apikey": api_key, "language": "eng", "isOverlayRequired": False}
        )
        result = response.json()
        return result
    except Exception as e:
        return {"error": str(e)}

# Indexing function
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

# Connexion sécurisée à Google Sheets
def connect_to_tooljet_sheet_from_secrets(sheet_url, worksheet_title):
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(st.secrets["gspread_auth"], scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(sheet_url).worksheet(worksheet_title)
    return sheet

# Interface
uploaded_file = st.file_uploader("📸 Importer une image technique", type=["jpg", "jpeg", "png"])
if uploaded_file:
    img = Image.open(uploaded_file)
    rotation = st.selectbox("🔁 Rotation ?", [0, 90, 180, 270], index=0)
    img = img.rotate(-rotation, expand=True)
    st.image(img, caption="🖼️ Aperçu brut", use_container_width=False)

    if st.button("🖼️ Je veux sélectionner une zone"):
        canvas_width, canvas_height = img.size

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
            ocr_result = ocr_space_api(img_bytes)

            if "error" in ocr_result:
                st.error(f"❌ Erreur OCR : {ocr_result['error']}")
            else:
                raw_text = ocr_result.get("ParsedResults", [{}])[0].get("ParsedText", "")
                with st.expander("📄 Texte OCR brut"):
                    st.text(raw_text)

                results = index_and_match_fields_with_alias(raw_text, target_fields, field_aliases)
                st.subheader("📊 Champs extraits :")
                for key in target_fields:
                    st.write(f"🔹 **{key}** → {results.get(key)}")

                if st.button("✅ Je valide les données"):
                    try:
                        sheet_url = "https://docs.google.com/spreadsheets/d/1yhIVYOqibFnhKKCnbhw8v0f4n1MbfY_4uZhSotK44gc/edit"
                        worksheet_name = "Tests_Panneaux"
                        sheet = connect_to_tooljet_sheet_from_secrets(sheet_url, worksheet_name)
                        row = [results.get(field, "") for field in target_fields]
                        sheet.append_row(row)
                        st.success("✅ Résultats enregistrés dans le Google Sheet ToolJet.")
                    except Exception as e:
                        st.error(f"❌ Envoi impossible : {e}")
