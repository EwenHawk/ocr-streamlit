import streamlit as st
import requests
from PIL import Image
import io
import re
import gspread
from google.oauth2.service_account import Credentials
from streamlit_drawable_canvas import st_canvas

# 🆔 Récupération de l'ID_Panneau depuis l'URL
id_panneau = st.query_params.get("id_panneau", "")

TARGET_KEYS = ["Voc", "Isc", "Pmax", "Vpm", "Ipm"]

# États Streamlit
if "selection_mode" not in st.session_state:
    st.session_state.selection_mode = False
if "sheet_saved" not in st.session_state:
    st.session_state.sheet_saved = False
if "results" not in st.session_state:
    st.session_state.results = {}

# Extraction OCR propre
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

# API OCR.Space
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

# Enregistrement Google Sheet
def send_to_sheet(id_panneau, row_data, sheet_id, worksheet_name):
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["gspread_auth"], scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(sheet_id).worksheet(worksheet_name)

    # ✅ Ajoute l'ID_Panneau en première colonne
    full_row = [id_panneau] + row_data
    sheet.append_row(full_row)

    return True

# Interface Streamlit
st.set_page_config(page_title="OCR ToolJet", page_icon="📤", layout="centered")
st.title("🔍 OCR technique avec capture et traitement intelligent")

# 👁️ Afficher l'ID_Panneau reçu
if id_panneau:
    st.info(f"🆔 ID_Panneau reçu : `{id_panneau}`")
else:
    st.warning("⚠️ Aucun ID_Panneau détecté dans l’URL")

# Choix de la source image
source = st.radio("📷 Source de l’image :", ["Téléverser un fichier", "Prendre une photo"])
img = None
if source == "Téléverser un fichier":
    uploaded_file = st.file_uploader("📁 Importer un fichier", type=["jpg", "jpeg", "png"])
    if uploaded_file:
        img = Image.open(uploaded_file)
elif source == "Prendre une photo":
    photo = st.camera_input("📸 Capture via caméra")
    if photo:
        img = Image.open(photo)

if img:
    rotation = st.selectbox("🔁 Rotation", [0, 90, 180, 270], index=0)
    img = img.rotate(-rotation, expand=True)
    # ✂️ Rognage asymétrique : moins à gauche, plus à droite
    w, h = img.size
    left = int(w * 1/6)
    right = int(w * 2/3)
    top = int(h * 1/4)
    bottom = int(h * 3/4)
    img = img.crop((left, top, right, bottom))

    st.image(img, caption="🖼️ Image rognée", use_container_width=False)
    
    max_width = 800
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.Resampling.LANCZOS)

    if not st.session_state.selection_mode:
        if st.button("🎯 Je sélectionne une zone à analyser"):
            st.session_state.selection_mode = True

    if st.session_state.selection_mode:
        canvas_width, canvas_height = img.size

        # 📱 Zone dynamique selon largeur
        if canvas_width < 500:
            rect_left = int(canvas_width * 0.1)
            rect_top = int(canvas_height * 0.2)
            rect_width = int(canvas_width * 1)
            rect_height = int(canvas_height * 0.5)
        else:
            rect_left = canvas_width // 4
            rect_top = canvas_height // 4
            rect_width = canvas_width // 1
            rect_height = canvas_height // 3

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
            
            # 🧼 Prétraitement : binarisation (garder le noir, supprimer le fond)
            gray = cropped_img.convert("L")  # convertit en niveaux de gris
            
            # 🔲 Seuil — ajustable selon contraste
            threshold = 60  # plus bas = plus strict
            bw = gray.point(lambda p: 0 if p < threshold else 255, mode="1")  # noir ou blanc
            
            # ✅ Appliquer fond blanc et texte noir
            cleaned = Image.new("RGB", bw.size, (255, 255, 255))
            cleaned.paste(bw.convert("RGB"))
            
            cropped_img = cleaned
            st.image(cropped_img, caption="📌 Zone sélectionnée", use_container_width=False)

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

# ✅ Le bouton d'enregistrement s’affiche seulement après OCR
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
