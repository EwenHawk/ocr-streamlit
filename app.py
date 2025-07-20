import streamlit as st
import requests
from PIL import Image, ImageEnhance, ImageOps
import io
import re
import gspread
from google.oauth2.service_account import Credentials
from streamlit_drawable_canvas import st_canvas
# 🔖 ID_Panneau transmis via URL
id_panneau = st.query_params.get("id_panneau", "")

TARGET_KEYS = ["Voc", "Isc", "Pmax", "Vpm", "Ipm"]

# États Streamlit
if "selection_mode" not in st.session_state:
    st.session_state.selection_mode = False
if "sheet_saved" not in st.session_state:
    st.session_state.sheet_saved = False
if "results" not in st.session_state:
    st.session_state.results = {}

# 🧪 Extraction OCR
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

# 🔍 API OCR
def ocr_space_api(img_bytes, api_key="K81047805588957"):
    try:
        response = requests.post(
            "https://api.ocr.space/parse/image",
            files={"filename": ("image.jpg", img_bytes, "image/jpeg")},
            data={"apikey": api_key, "language": "eng", "isOverlayRequired": False}
        )
        return response.json()
    except Exception as e:
        return {"error": str(e)}

# 📤 Enregistrement dans Google Sheets
def send_to_sheet(id_panneau, row_data, sheet_id, worksheet_name):
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["gspread_auth"], scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(sheet_id).worksheet(worksheet_name)
    full_row = [id_panneau] + row_data
    sheet.append_row(full_row)
    return True

# 🎨 Interface principale
st.set_page_config(page_title="OCR ToolJet", page_icon="📤", layout="centered")
st.title("🔍 OCR technique avec capture et traitement intelligent")

# 🔖 Affichage ID
if id_panneau:
    st.info(f"🆔 ID_Panneau reçu : `{id_panneau}`")
else:
    st.warning("⚠️ Aucun ID_Panneau détecté dans l’URL")

# 📷 Source image
source = st.radio("📷 Source de l’image :", ["Téléverser un fichier", "Prendre une photo"])
img, original_img = None, None

if source == "Téléverser un fichier":
    uploaded_file = st.file_uploader("📁 Importer un fichier", type=["jpg", "jpeg", "png"])
    if uploaded_file:
        img = Image.open(uploaded_file)
        original_img = img.copy()
elif source == "Prendre une photo":
    photo = st.camera_input("📸 Capture via caméra")
    if photo:
        img = Image.open(photo)
        original_img = img.copy()

if img:
    rotation = st.selectbox("🔁 Rotation", [0, 90, 180, 270], index=0)
    img = img.rotate(-rotation, expand=True)
    original_img = original_img.rotate(-rotation, expand=True)

    screen_max_width = 360
    if img.width > screen_max_width:
        ratio = screen_max_width / img.width
        img = img.resize((screen_max_width, int(img.height * ratio)), Image.Resampling.LANCZOS)

    st.image(img, caption="🖼️ Aperçu", use_container_width=False)

    if not st.session_state.selection_mode:
        if st.button("🎯 Je sélectionne une zone à analyser"):
            st.session_state.selection_mode = True

    if st.session_state.selection_mode:
        canvas_width, canvas_height = img.size
        rect_left = int(canvas_width * 0.1)
        rect_top = int(canvas_height * 0.2)
        rect_width = int(canvas_width * 0.8)
        rect_height = int(canvas_height * 0.25)

        initial_rect = {
            "objects": [{
                "type": "rect",
                "left": rect_left,
                "top": rect_top,
                "width": rect_width,
                "height": rect_height,
                "fill": "rgba(255,165,0,0.3)",
                "stroke": "orange",
                "strokeWidth": 2
            }]
        }

        st.markdown("<div style='max-width:100%; overflow-x:auto;'>", unsafe_allow_html=True)
        canvas_result = st_canvas(
            background_image=img,
            initial_drawing=initial_rect,
            drawing_mode="transform",
            update_streamlit=True,
            height=min(canvas_height, 500),
            width=min(canvas_width, 360),
            key="canvas"
        )
        st.markdown("</div>", unsafe_allow_html=True)

        if canvas_result.json_data and canvas_result.json_data["objects"]:
            rect = canvas_result.json_data["objects"][0]
            x, y = rect["left"], rect["top"]
            w, h = rect["width"], rect["height"]

            # 📐 Recalcul pour image originale
            scale_x = original_img.width / img.width
            scale_y = original_img.height / img.height

            x_orig = int(x * scale_x)
            y_orig = int(y * scale_y)
            w_orig = int(w * scale_x)
            h_orig = int(h * scale_y)

            cropped_img = original_img.crop((x_orig, y_orig, x_orig + w_orig, y_orig + h_orig))

            # ✨ Filtrage doux si crop assez grand
            if cropped_img.width > 300 and cropped_img.height > 300:
                cropped_img = ImageEnhance.Sharpness(cropped_img).enhance(1.2)
                cropped_img = ImageEnhance.Contrast(cropped_img).enhance(1.05)
                cropped_img = ImageEnhance.Brightness(cropped_img).enhance(1.05)

            bordered_img = ImageOps.expand(cropped_img, border=4, fill='gray')
            st.image(bordered_img, caption="🎯 Zone sélectionnée - optimisée", use_container_width=False)

            if st.button("📤 Lancer le traitement OCR"):
                img_bytes = io.BytesIO()
                bordered_img.save(img_bytes, format="JPEG", quality=95)
                img_bytes.seek(0)

                ocr_result = ocr_space_api(img_bytes)
                st.write("📡 Réponse brute OCR:", ocr_result)
                parsed = ocr_result.get("ParsedResults", [])
                if parsed and "ParsedText" in parsed[0]:
                    raw_text = parsed[0]["ParsedText"]
                    st.subheader("📄 Texte OCR brut")
                    st.code(raw_text[:3000], language="text")

                    st.session_state.results = extract_ordered_fields(raw_text)

                    st.subheader("📊 Champs extraits et arrondis :")
                    for key, value in st.session_state.results.items():
                        st.write(f"🔹 **{key}** → {value}")

                    missing = [k for k, v in st.session_state.results.items() if v == "Non détecté"]
                    if missing:
                        st.warning(f"⚠️ Champs non détectés : {', '.join(missing)}")
                    else:
                        st.success("✅ Tous les champs détectés avec succès.")
                else:
                    st.warning("⚠️ Aucun texte détecté dans cette zone OCR.")
                    st.session_state.results = {}

# 💾 Enregistrement
if st.session_state.results:
    if st.button("✅ Enregistrer les données dans Google Sheet"):
        try:
            sheet_id = "1yhIVYOqibFnhKKCnbhw8v0f4n1MbfY_4uZhSotK44gc"
            worksheet_name = "Tests_Panneaux"
            row = [st.session_state.results.get(k, "Non détecté") for k in TARGET_KEYS]
            send_to_sheet(id_panneau, row, sheet_id, worksheet_name)
            st.session_state.sheet_saved = True
        except Exception as e:
            st.error(f"❌ Erreur lors de l'enregistrement : {e}")

if st.session_state.sheet_saved:
    st.success("📡 Données bien enregistrées dans Google Sheet.")
    st.info("📎 Faîtes retour sur le navigateur pour revenir.")
