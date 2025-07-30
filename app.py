import streamlit as st
import requests
from PIL import Image, ImageEnhance
import io
import re
import gspread
from google.oauth2.service_account import Credentials
from streamlit_drawable_canvas import st_canvas

# 🆔 ID depuis URL
id_panneau = st.query_params.get("id_panneau", "")
TARGET_KEYS = ["Voc", "Isc", "Pmax", "Vpm", "Ipm"]

# 🎛️ États
if "selection_mode" not in st.session_state:
    st.session_state.selection_mode = False
if "sheet_saved" not in st.session_state:
    st.session_state.sheet_saved = False
if "results" not in st.session_state:
    st.session_state.results = {}

# 📄 OCR : extraction champs
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

# 🧠 API OCR
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

# 📝 Google Sheet
def send_to_sheet(id_panneau, row_data, sheet_id, worksheet_name):
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["gspread_auth"], scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(sheet_id).worksheet(worksheet_name)
    full_row = [id_panneau] + row_data
    sheet.append_row(full_row)
    return True

# 🎨 Interface
st.set_page_config(page_title="OCR ToolJet", page_icon="📤", layout="centered")
st.title("🔍 OCR technique avec traitement intelligent")

if id_panneau:
    st.info(f"🆔 ID_Panneau reçu : `{id_panneau}`")
else:
    st.warning("⚠️ Aucun ID_Panneau détecté dans l’URL")

# 📷 Import ou Caméra
source = st.radio("📷 Source de l’image :", ["Téléverser un fichier", "Prendre une photo"])
img = None

# ... après import de l'image (upload ou caméra)
if uploaded_file:
    img = Image.open(uploaded_file)
    img_original = img.copy()
elif photo:
    img = Image.open(photo)
    img_original = img.copy()

# 🎛️ Rotation (mais sans l'appliquer immédiatement)
rotation = st.selectbox("🔁 Rotation", [0, 90, 180, 270], index=0)

# ✂️ Rognage adouci (~1/3 de moins)
w, h = img.size
left = int(w * 1/12)
right = int(w * 11/12)
top = int(h * 1/5)
bottom = int(h * 4/5)
cropped_preview = img.crop((left, top, right, bottom))

# 🖼️ Image affichée pivotée (mais image source conservée)
rotated_preview = cropped_preview.rotate(-rotation, expand=True)
canvas_width, canvas_height = rotated_preview.size

# 📐 Redimensionnement pour affichage
max_width = 360
if rotated_preview.width > max_width:
    ratio = max_width / rotated_preview.width
    rotated_preview = rotated_preview.resize((max_width, int(rotated_preview.height * ratio)), Image.Resampling.LANCZOS)

st.image(rotated_preview, caption="🖼️ Image rognée (rotation appliquée)", use_container_width=True)

# 🎨 Canvas avec rotation affichée
if st.session_state.selection_mode:
    initial_rect = {...}
    canvas_result = st_canvas(
        background_image=rotated_preview,
        ...
        height=rotated_preview.height,
        width=rotated_preview.width,
        key="canvas"
    )

    # 🔁 Coordonnées recalculées avec ratios
    if canvas_result.json_data and canvas_result.json_data["objects"]:
        rect = canvas_result.json_data["objects"][-1]
        x, y = rect["left"], rect["top"]
        w, h = rect["width"], rect["height"]

        scale_x = img_original.width / canvas_width
        scale_y = img_original.height / canvas_height

        x_orig = int(x * scale_x)
        y_orig = int(y * scale_y)
        w_orig = int(w * scale_x)
        h_orig = int(h * scale_y)

        cropped_zone = img_original.crop((x_orig, y_orig, x_orig + w_orig, y_orig + h_orig))

        # Appliquer la rotation sélectionnée sur la zone extraite
        cropped_zone = cropped_zone.rotate(-rotation, expand=True)

    # 📐 Redimensionnement
    max_width = 360
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.Resampling.LANCZOS)
    canvas_width, canvas_height = img.size  # 📏 Dimensions canvas

    st.image(img, caption="🖼️ Image rognée", use_container_width=True)

    if not st.session_state.selection_mode:
        if st.button("🎯 Je sélectionne une zone à analyser"):
            st.session_state.selection_mode = True

    if st.session_state.selection_mode:
        initial_rect = {
            "objects": [{
                "type": "rect",
                "left": int(canvas_width * 0.1),
                "top": int(canvas_height * 0.2),
                "width": int(canvas_width * 0.9),
                "height": int(canvas_height * 0.5),
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
            rect = canvas_result.json_data["objects"][-1]  # 🆕 Prend la dernière modif
            x, y = rect["left"], rect["top"]
            w, h = rect["width"], rect["height"]

            # 🧮 Correction des coordonnées
            scale_x = img_original.width / canvas_width
            scale_y = img_original.height / canvas_height
            x_orig = int(x * scale_x)
            y_orig = int(y * scale_y)
            w_orig = int(w * scale_x)
            h_orig = int(h * scale_y)

            cropped_img = img_original.crop((x_orig, y_orig, x_orig + w_orig, y_orig + h_orig))

            if cropped_img.width > max_width:
                ratio = max_width / cropped_img.width
                cropped_img = cropped_img.resize((max_width, int(cropped_img.height * ratio)), Image.Resampling.LANCZOS)

            # 🧼 Prétraitement
            gray = cropped_img.convert("L")
            bright = ImageEnhance.Brightness(gray).enhance(1.2)
            soft_white = bright.point(lambda p: 255 if p > 230 else p)
            final = ImageEnhance.Contrast(soft_white).enhance(1.1)
            cleaned = Image.new("RGB", final.size, (255, 255, 255))
            cleaned.paste(final.convert("RGB"))
            cropped_img = cleaned

            st.image(cropped_img, caption="📌 Zone sélectionnée (prétraitée)", use_container_width=True)

            if st.button("📤 Lancer le traitement OCR"):
                img_bytes = io.BytesIO()
                cropped_img.save(img_bytes, format="JPEG", quality=100)
                img_bytes.seek(0)

                ocr_result = ocr_space_api(img_bytes)
                parsed = ocr_result.get("ParsedResults", [])
                if parsed and "ParsedText" in parsed[0]:
                    raw_text = parsed[0]["ParsedText"]
                    st.subheader("📄 Texte OCR brut")
                    st.code(raw_text[:3000], language="text")
                    st.session_state.results = extract_ordered_fields(raw_text)

                    st.subheader("📊 Champs extraits :")
                    for key, value in st.session_state.results.items():
                        st.write(f"🔹 **{key}** → {value}")
                    missing = [k for k, v in st.session_state.results.items() if v == "Non détecté"]
                    if missing:
                        st.warning(f"⚠️ Champs non détectés : {', '.join(missing)}")
                    else:
                        st.success("✅ Tous les champs détectés avec succès.")
                else:
                    st.warning("⚠ Aucun texte détecté.")
                    st.session_state.results = {}

# ✅ Enregistrement si données disponibles
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
    st.info("📎 Faîtes retour sur le navigateur pour revenir sur ToolJet.")
