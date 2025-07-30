import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image, ImageEnhance
import io
import requests
import re
import gspread
from google.oauth2.service_account import Credentials

# 🆔 Récupération de l'ID_Panneau depuis l'URL
st.write("🔍 ID brut récupéré :", st.query_params)
id_panneau = str(st.query_params.get("id_panneau", [""]))
st.info(f"🆔 ID détecté : `{id_panneau}`")
TARGET_KEYS = ["Voc", "Isc", "Pmax", "Vpm", "Ipm"]

# États Streamlit
for key, default in [
    ("selection_mode", False),
    ("sheet_saved", False),
    ("results", {}),
]:
    if key not in st.session_state:
        st.session_state[key] = default

st.set_page_config(page_title="✂️ Rognage + OCR", layout="centered")
st.title("📸 Rognage + Retouche + OCR 🔎")

uploaded_file = st.file_uploader("Téléverse une image (max 200 MB)", type=["jpg", "png", "jpeg"])

# Désactive le scroll sur le canvas pour améliorer le tactile
st.markdown("""
<style>
  canvas {
    touch-action: none;
  }
</style>
""", unsafe_allow_html=True)

# 📄 Fonction extraction intelligente
def extract_ordered_fields(text, expected_keys=TARGET_KEYS):
    aliases = {
        "voc": "Voc", "v_oc": "Voc",
        "isc": "Isc", "lsc": "Isc", "i_sc": "Isc", "isci": "Isc", "Isci": "Isc",
        "pmax": "Pmax", "p_max": "Pmax", "pmax.": "Pmax",
        "vpm": "Vpm", "v_pm": "Vpm", "vpm.": "Vpm",
        "ipm": "Ipm", "i_pm": "Ipm", "ipm.": "Ipm", "lpm": "Ipm",
        "Iom": "Ipm", "iom": "Ipm", "lom": "Ipm", "Lom": "Ipm",
    }

    def normalize_key(raw_key):
        return re.sub(r'[^a-zA-Z]', '', raw_key).lower()

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    keys_found, values_found = [], []

    for line in lines:
        nk = normalize_key(line)
        if nk in aliases:
            keys_found.append(aliases[nk])
        elif re.match(r"^\d+[.,]?\d*\s*[a-z%ΩVWAm]*$", line, re.IGNORECASE):
            values_found.append(line.strip())

    result = {}
    for i in range(min(len(keys_found), len(values_found))):
        raw = values_found[i]
        clean = re.sub(r"[^\d.,\-]", "", raw).replace(",", ".")
        try:
            result[keys_found[i]] = str(round(float(clean), 1))
        except:
            result[keys_found[i]] = raw

    return {k: result.get(k, "Non détecté") for k in expected_keys}

# 📤 Fonction envoi vers Google Sheet
def send_to_sheet(id_p, row_data, sheet_id, worksheet_name):
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(
        st.secrets["gspread_auth"], scopes=scope
    )
    client = gspread.authorize(creds)
    ws = client.open_by_key(sheet_id).worksheet(worksheet_name)
    ws.append_row([id_p] + row_data)
    return True

if uploaded_file:
    # Préparation
    original_img = Image.open(uploaded_file).convert("RGB")
    original_img = original_img.rotate(-90, expand=True)

    w, h = original_img.size
    left, right = int(w * 0.05), int(w * 0.85)
    top, bottom = int(h * 0.3), int(h * 0.7)
    img = original_img.crop((left, top, right, bottom))

    st.subheader("🖼️ Image optimisée")
    st.image(img, use_container_width=True)

    # Choix dynamique du mode et de la taille du canvas
    st.sidebar.subheader("🔧 Options de sélection")
    canvas_width = st.sidebar.slider("Largeur du canvas", 200, 800, 400)
    drawing_mode = st.sidebar.radio(
        "Mode de dessin (Freehand recommandé sur mobile)",
        ("rect", "freedraw"),
        index=1
    )
    canvas_height = int(canvas_width * img.height / img.width)

    st.subheader("🟦 Sélectionne une zone")
    canvas_result = st_canvas(
        background_image=img,
        height=canvas_height,
        width=canvas_width,
        drawing_mode=drawing_mode,
        stroke_width=2,
        stroke_color="blue",
        update_streamlit=True,
        key="canvas_crop"
    )

    # Traitement de la sélection
    if canvas_result.json_data and canvas_result.json_data["objects"]:
        obj = canvas_result.json_data["objects"][0]
        scale_x = img.width / canvas_width
        scale_y = img.height / canvas_height

        if drawing_mode == "rect":
            x = int(obj["left"] * scale_x)
            y = int(obj["top"] * scale_y)
            w_sel = int(obj["width"] * scale_x)
            h_sel = int(obj["height"] * scale_y)
        else:  # freedraw → on en déduit la bounding-box
            path = obj.get("path", [])
            xs = [seg[1] for seg in path]
            ys = [seg[2] for seg in path]
            x0, y0 = min(xs), min(ys)
            x1, y1 = max(xs), max(ys)
            x = int(x0 * scale_x)
            y = int(y0 * scale_y)
            w_sel = int((x1 - x0) * scale_x)
            h_sel = int((y1 - y0) * scale_y)

        crop_box = (
            left + x,
            top + y,
            left + x + w_sel,
            top + y + h_sel
        )
        cropped = original_img.crop(crop_box).convert("RGB")

        st.subheader("🔍 Image rognée")
        st.image(cropped, caption="📐 Zone sélectionnée")

        # Contraste + OCR
        enhanced = ImageEnhance.Contrast(cropped).enhance(1.2)
        buf = io.BytesIO()
        enhanced.save(buf, format="JPEG")
        buf.seek(0)

        ocr_url = "https://api.ocr.space/parse/image"
        api_key = "helloworld"
        resp = requests.post(
            ocr_url,
            files={"file": ("image.jpg", buf, "image/jpeg")},
            data={"apikey": api_key, "language": "eng", "OCREngine": 2}
        )

        if resp.status_code == 200:
            ocr_text = resp.json()["ParsedResults"][0]["ParsedText"]
            st.subheader("🔍 Texte OCR brut")
            st.text(ocr_text)

            extracted = extract_ordered_fields(ocr_text)
            st.subheader("📋 Champs extraits")
            for k in TARGET_KEYS:
                st.text(f"{k} : {extracted.get(k)}")

            if st.button("📤 Enregistrer dans Google Sheet"):
                try:
                    sheet_id = "1yhIVYOqibFnhKKCnbhw8v0f4n1MbfY_4uZhSotK44gc"
                    ws_name = "Tests_Panneaux"
                    row = [extracted.get(k) for k in TARGET_KEYS]
                    send_to_sheet(id_panneau, row, sheet_id, ws_name)
                    st.success("✅ Données envoyées.")
                except Exception as e:
                    st.error(f"❌ Erreur : {e}")
        else:
            st.error(f"❌ OCR.space a renvoyé {resp.status_code}")

        # Bouton de téléchargement
        final_buf = io.BytesIO()
        enhanced.save(final_buf, format="JPEG", quality=90, optimize=True)
        st.download_button(
            label="📥 Télécharger l'image finale",
            data=final_buf.getvalue(),
            file_name="image_rognée.jpg",
            mime="image/jpeg"
        )

    else:
        st.info("👆 Dessine une zone pour lancer le traitement.")
else:
    st.info("📤 Choisis une image à traiter.")
