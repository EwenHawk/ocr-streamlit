import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image, ImageEnhance
import io
import requests
import re
import gspread
from google.oauth2.service_account import Credentials

# 🆔 Récupération de l'ID_Panneau depuis l'URL
id_panneau = st.query_params.get("id_panneau", "")
TARGET_KEYS = ["Voc", "Isc", "Pmax", "Vpm", "Ipm"]

st.set_page_config(page_title="✂️ Rognage + OCR", layout="centered")
st.title("📸 Rognage + Retouche + OCR 🔎")

# 1) Upload de l’image
uploaded_file = st.file_uploader("Téléverse une image (max 200 MB)", type=["jpg", "png", "jpeg"])

# 2) Initialisation d’un rectangle en session_state
if "rectangles" not in st.session_state:
    st.session_state.rectangles = [{
        "type": "rect",
        "left": 30,
        "top": 30,
        "width": 120,
        "height": 80,
        "fillStyle": "rgba(0, 0, 255, 0.2)",
        "strokeStyle": "blue",
        "strokeWidth": 2
    }]

# 3) Fonction d’extraction OCR
def extract_ordered_fields(text, expected_keys=TARGET_KEYS):
    aliases = {
        "voc": "Voc", "v_oc": "Voc",
        "isc": "Isc", "lsc": "Isc", "i_sc": "Isc", "isci": "Isc",
        "pmax": "Pmax", "p_max": "Pmax", "pmax.": "Pmax",
        "vpm": "Vpm", "v_pm": "Vpm", "vpm.": "Vpm",
        "ipm": "Ipm", "i_pm": "Ipm", "ipm.": "Ipm", "lpm": "Ipm",
    }
    def normalize_key(k):
        return re.sub(r'[^a-zA-Z]', '', k).lower()

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    keys_found, vals_found = [], []

    for l in lines:
        k = normalize_key(l)
        if k in aliases:
            keys_found.append(aliases[k])
        elif re.match(r"^\d+[.,]?\d*\s*[a-z%ΩVWAm]*$", l, re.IGNORECASE):
            vals_found.append(l)

    out = {}
    for i in range(min(len(keys_found), len(vals_found))):
        raw = vals_found[i]
        num = re.sub(r"[^\d.,\-]", "", raw).replace(",", ".")
        try:
            out[keys_found[i]] = str(round(float(num), 1))
        except:
            out[keys_found[i]] = raw

    return {k: out.get(k, "Non détecté") for k in expected_keys}

# 4) Fonction d’envoi vers Google Sheets
def send_to_sheet(id_panneau, row, sheet_id, ws_name):
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["gspread_auth"], scopes=scope)
    client = gspread.authorize(creds)
    ws = client.open_by_key(sheet_id).worksheet(ws_name)
    ws.append_row([id_panneau] + row)

# 5) Si image uploadée, on affiche + canevas
if uploaded_file:
    original = Image.open(uploaded_file).convert("RGB")
    original = original.rotate(-90, expand=True)

    # Crop initial
    w, h = original.size
    L, R = int(w * 0.05), int(w * 0.85)
    T, B = int(h * 0.3), int(h * 0.7)
    img = original.crop((L, T, R, B))

    st.image(img, caption="🖼️ Image optimisée", use_container_width=True)

    # Dimensions du canevas
    c_w = 300
    c_h = int(c_w * img.height / img.width)

    st.subheader("🟦 Ajuste la zone (glisse/redimensionne)")

    # 🔲 Canevas avec initial_drawing sous forme de dict
    canvas_result = st_canvas(
        background_image=img,
        height=c_h,
        width=c_w,
        initial_drawing={"objects": st.session_state.rectangles},
        drawing_mode="none",    # Pas de dessin libre
        update_streamlit=True,
        key="crop_canvas"
    )

    # 6) Si l’utilisateur déplace ou redimensionne, on récupère le rectangle
    if canvas_result.json_data and canvas_result.json_data.get("objects"):
        # Met à jour la session_state
        st.session_state.rectangles = canvas_result.json_data["objects"]
        obj = st.session_state.rectangles[0]

        # Conversion en coordonnées réelles
        scale_x = img.width / c_w
        scale_y = img.height / c_h
        x = int(obj["left"] * scale_x)
        y = int(obj["top"] * scale_y)
        w_sel = int(obj["width"] * scale_x)
        h_sel = int(obj["height"] * scale_y)

        # Crop final sur l’image originale
        crop_box = (L + x, T + y, L + x + w_sel, T + y + h_sel)
        cropped = original.crop(crop_box).convert("RGB")

        st.subheader("🔍 Image rognée")
        st.image(cropped, caption="📐 Zone finale")

        # 7) OCR
        enhanced = ImageEnhance.Contrast(cropped).enhance(1.2)
        buf = io.BytesIO()
        enhanced.save(buf, format="JPEG")
        buf.seek(0)

        resp = requests.post(
            "https://api.ocr.space/parse/image",
            files={"file": ("img.jpg", buf, "image/jpeg")},
            data={"apikey": "K81047805588957", "language": "eng", "OCREngine": 2}
        )

        if resp.status_code == 200:
            text = resp.json()["ParsedResults"][0]["ParsedText"]
            st.subheader("🔍 Texte OCR brut")
            st.text(text)

            extracted = extract_ordered_fields(text)
            st.subheader("📋 Résultats extraits")
            for k in TARGET_KEYS:
                st.write(f"{k} : {extracted[k]}")

            if st.button("📤 Enregistrer dans Google Sheet"):
                row = [extracted[k] for k in TARGET_KEYS]
                try:
                    send_to_sheet(
                        id_panneau, row,
                        sheet_id="1yhIVYOqibFnhKKCnbhw8v0f4n1MbfY_4uZhSotK44gc",
                        ws_name="Tests_Panneaux"
                    )
                    st.success("✅ Enregistré dans Google Sheet")
                except Exception as e:
                    st.error(f"Erreur Google Sheet : {e}")
        else:
            st.error(f"OCR.space error {resp.status_code}")

        # 8) Téléchargement
        dl_buf = io.BytesIO()
        enhanced.save(dl_buf, format="JPEG", quality=90, optimize=True)
        st.download_button(
            "📥 Télécharger le résultat",
            data=dl_buf.getvalue(),
            file_name="cropped.jpg",
            mime="image/jpeg"
        )
    else:
        st.info("👆 Glisse ou redimensionne le rectangle pour lancer le crop + OCR.")
else:
    st.info("📤 Téléverse d'abord une image.")
