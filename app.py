import streamlit as st
import requests
from PIL import Image
import io
import re
from streamlit_drawable_canvas import st_canvas

TARGET_KEYS = ["Voc", "Isc", "Pmax", "Vpm", "Ipm"]

if "selection_mode" not in st.session_state:
    st.session_state.selection_mode = False

def extract_ordered_fields(text, expected_keys=TARGET_KEYS):
    aliases = {
        "voc": "Voc", "v_oc": "Voc",
        "isc": "Isc", "lsc": "Isc", "i_sc": "Isc",
        "pmax": "Pmax", "p_max": "Pmax", "pmax.": "Pmax",
        "vpm": "Vpm", "v_pm": "Vpm", "vpm.": "Vpm",
        "ipm": "Ipm", "i_pm": "Ipm", "ipm.": "Ipm", "lpm": "Ipm"
    }

    lines = [line.strip().lower() for line in text.splitlines() if line.strip()]
    keys_found, values_found = [], []

    for line in lines:
        if line.endswith(":"):
            key = line.rstrip(":").strip()
            if key in aliases:
                keys_found.append(aliases[key])
        else:
            match = re.match(r"^\d+[.,]?\d*\s*[a-z%ΩVWAm]*$", line, re.IGNORECASE)
            if match:
                values_found.append(match.group(0).strip())

    result = {}
    for i in range(min(len(keys_found), len(values_found))):
        raw = values_found[i]
        clean = re.sub(r"[^\d.,\-]", "", raw).replace(",", ".")
        try:
            result[keys_found[i]] = str(round(float(clean), 1))
        except:
            result[keys_found[i]] = raw

    return {key: result.get(key, "Non détecté") for key in expected_keys}

def ocr_space_api(img_bytes, api_key="helloworld"):
    try:
        response = requests.post(
            "https://api.ocr.space/parse/image",
            files={"filename": ("image.jpg", img_bytes, "image/jpeg")},
            data={"apikey": api_key, "language": "eng", "isOverlayRequired": False}
        )
        return response.json()
    except Exception as e:
        return {"error": str(e)}

st.set_page_config(page_title="OCR ToolJet", page_icon="📤", layout="centered")
st.title("🔍 OCR technique avec extraction intelligente")

uploaded_file = st.file_uploader("📸 Importer une image", type=["jpg", "jpeg", "png"])
if uploaded_file:
    img = Image.open(uploaded_file)
    rotation = st.selectbox("🔁 Rotation", [0, 90, 180, 270], index=0)
    img = img.rotate(-rotation, expand=True)

    max_width = 800
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.Resampling.LANCZOS)

    st.image(img, caption="🖼️ Aperçu", use_container_width=False)

    if not st.session_state.selection_mode:
        if st.button("🎯 Je sélectionne une zone à analyser"):
            st.session_state.selection_mode = True

    if st.session_state.selection_mode:
        canvas_width, canvas_height = img.size
        initial_rect = {
            "objects": [{
                "type": "rect",
                "left": canvas_width // 4,
                "top": canvas_height // 4,
                "width": canvas_width // 2,
                "height": canvas_height // 6,  # ✅ Hauteur réduite
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

            if st.button("📤 Lancer le traitement OCR"):
                img_bytes = io.BytesIO()
                cropped_img.save(img_bytes, format="JPEG", quality=70)
                img_bytes.seek(0)

                ocr_result = ocr_space_api(img_bytes)
                if "error" in ocr_result:
                    st.error(f"❌ Erreur OCR : {ocr_result['error']}")
                else:
                    raw_text = ocr_result.get("ParsedResults", [{}])[0].get("ParsedText", "")
                    st.subheader("📄 Texte OCR brut")
                    st.code(raw_text[:3000], language="text")

                    results = extract_ordered_fields(raw_text)
                    st.subheader("📊 Champs extraits et arrondis :")
                    for key, value in results.items():
                        st.write(f"🔹 **{key}** → {value}")

                    missing = [k for k, v in results.items() if v == "Non détecté"]
                    if missing:
                        st.warning(f"⚠️ Champs non détectés : {', '.join(missing)}")
                    else:
                        st.success("✅ Tous les champs détectés avec succès.")

import gspread
from google.oauth2.service_account import Credentials

def send_to_sheet(row_data, sheet_url, worksheet_name):
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(st.secrets["gspread_auth"], scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(sheet_url).worksheet(worksheet_name)
    sheet.append_row(row_data)

    return True

# 📥 Bouton d'enregistrement dans Google Sheet
if st.button("✅ Enregistrer les données dans Google Sheet"):
    try:
        sheet_url = "https://docs.google.com/spreadsheets/d/TON_ID/edit"  # 🔁 Remplace avec ton URL
        worksheet_name = "Tests_Panneaux"  # 🔁 Remplace avec ton nom d’onglet
        row = [results[key] for key in TARGET_KEYS]
        send_to_sheet(row, sheet_url, worksheet_name)
        st.success("📡 Données enregistrées avec succès dans ton Google Sheet.")
    except Exception as e:
        st.error(f"❌ Échec d’enregistrement : {e}")

