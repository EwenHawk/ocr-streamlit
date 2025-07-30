import streamlit as st
import requests
from PIL import Image, ImageEnhance
import io
import re
import gspread
from google.oauth2.service_account import Credentials
from streamlit_drawable_canvas import st_canvas

# 🆔 URL paramètre
id_panneau = st.query_params.get("id_panneau", "")
TARGET_KEYS = ["Voc", "Isc", "Pmax", "Vpm", "Ipm"]

# 🎛️ État
if "sheet_saved" not in st.session_state:
    st.session_state.sheet_saved = False
if "results" not in st.session_state:
    st.session_state.results = {}

# 📄 OCR API
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

# 🔍 Extraction champs
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

# 📝 Google Sheet
def send_to_sheet(id_panneau, row_data, sheet_id, worksheet_name):
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["gspread_auth"], scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(sheet_id).worksheet(worksheet_name)
    full_row = [id_panneau] + row_data
    sheet.append_row(full_row)
    return True

# 🧭 Configuration
st.set_page_config(page_title="OCR ToolJet", page_icon="📤", layout="centered")
st.title("🖍️ OCR avec sélection dessinée et image responsive")

if id_panneau:
    st.info(f"🆔 ID_Panneau : `{id_panneau}`")

# 📷 Source image
source = st.radio("📷 Source de l’image :", ["Téléverser un fichier", "Prendre une photo"])
img = None
img_original = None

if source == "Téléverser un fichier":
    uploaded = st.file_uploader("📁 Importer une image", type=["jpg", "jpeg", "png"])
    if uploaded:
        img = Image.open(uploaded)
        img_original = img.copy()
elif source == "Prendre une photo":
    photo = st.camera_input("📸 Prendre une photo")
    if photo:
        img = Image.open(photo)
        img_original = img.copy()

# 🖼️ Affichage + sélection
if img:
    rotation = st.selectbox("🔁 Rotation", [0, 90, 180, 270], index=0)
    rotated = img.rotate(-rotation, expand=True)

    # 📏 Récupération des dimensions
    canvas_width, canvas_height = rotated.size

    # ✅ Image responsive
    st.image(rotated, caption="🖼️ Image affichée avec rotation", use_container_width=True)

    st.subheader("✏️ Dessinez une zone à OCR (pression souris)")
    canvas_result = st_canvas(
        background_image=rotated,
        height=canvas_height,
        width=canvas_width,
        drawing_mode="freedraw",
        stroke_color="red",
        stroke_width=2,
        update_streamlit=True,
        key="freedraw"
    )

    if canvas_result.json_data and canvas_result.json_data["objects"]:
        obj = canvas_result.json_data["objects"][-1]
        x, y = obj["left"], obj["top"]
        w, h = obj["width"], obj["height"]

        # 🔁 Conversion vers image originale
        scale_x = img_original.width / canvas_width
        scale_y = img_original.height / canvas_height
        x_orig = int(x * scale_x)
        y_orig = int(y * scale_y)
        w_orig = int(w * scale_x)
        h_orig = int(h * scale_y)

        cropped = img_original.crop((x_orig, y_orig, x_orig + w_orig, y_orig + h_orig))
        cropped = cropped.rotate(-rotation, expand=True)

        # 🧼 Prétraitement doux
        gray = cropped.convert("L")
        bright = ImageEnhance.Brightness(gray).enhance(1.2)
        white_soft = bright.point(lambda p: 255 if p > 230 else p)
        final = ImageEnhance.Contrast(white_soft).enhance(1.1)
        cleaned = Image.new("RGB", final.size, (255, 255, 255))
        cleaned.paste(final.convert("RGB"))
        cropped = cleaned

        st.image(cropped, caption="📌 Zone sélectionnée", use_container_width=True)

        if st.button("📤 Lancer OCR"):
            buffer = io.BytesIO()
            cropped.save(buffer, format="JPEG", quality=100)
            buffer.seek(0)
            result = ocr_space_api(buffer)
            parsed = result.get("ParsedResults", [])
            if parsed and "ParsedText" in parsed[0]:
                raw = parsed[0]["ParsedText"]
                st.subheader("📄 Texte OCR brut")
                st.code(raw[:3000])
                st.session_state.results = extract_ordered_fields(raw)

                st.subheader("📊 Champs extraits")
                for k, v in st.session_state.results.items():
                    st.write(f"🔹 **{k}** → {v}")
                missing = [k for k, v in st.session_state.results.items() if v == "Non détecté"]
                if missing:
                    st.warning(f"⚠️ Champs manquants : {', '.join(missing)}")
                else:
                    st.success("✅ Tous les champs détectés")
            else:
                st.warning("🚫 Aucun texte détecté")

# ✅ Google Sheet
if st.session_state.results:
    if st.button("✅ Enregistrer dans Google Sheet"):
        try:
            sheet_id = "1yhIVYOqibFnhKKCnbhw8v0f4n1MbfY_4uZhSotK44gc"
            worksheet_name = "Tests_Panneaux"
            row = [st.session_state.results.get(k, "Non détecté") for k in TARGET_KEYS]
            send_to_sheet(id_panneau, row, sheet_id, worksheet_name)
            st.session_state.sheet_saved = True
        except Exception as e:
            st.error(f"❌ Enregistrement échoué : {e}")

if st.session_state.sheet_saved:
    st.success("📡 Données envoyées dans Google Sheet")
