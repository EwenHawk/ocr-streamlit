import time
import io
import re
import requests

import streamlit as st
from streamlit import experimental as st_ex
from streamlit_drawable_canvas import st_canvas
from PIL import Image, ImageEnhance

import gspread
from google.oauth2.service_account import Credentials

# paramètres
TARGET_KEYS = ["Voc", "Isc", "Pmax", "Vpm", "Ipm"]
id_panneau = st.experimental_get_query_params().get("id_panneau", [""])[0]

st.set_page_config(page_title="✂️ Rognage + OCR", layout="centered")
st.title("📸 Rognage + Retouche + OCR 🔎")

# fonctions utilitaires
def extract_ordered_fields(text, expected_keys=TARGET_KEYS):
    aliases = {
        "voc":"Voc","v_oc":"Voc",
        "isc":"Isc","lsc":"Isc","i_sc":"Isc","isci":"Isc",
        "pmax":"Pmax","p_max":"Pmax","pmax.":"Pmax",
        "vpm":"Vpm","v_pm":"Vpm","vpm.":"Vpm",
        "ipm":"Ipm","i_pm":"Ipm","ipm.":"Ipm","lpm":"Ipm"
    }
    def norm(k): return re.sub(r'[^a-zA-Z]','',k).lower()
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    keys, vals = [], []
    for l in lines:
        k = norm(l)
        if k in aliases:
            keys.append(aliases[k])
        elif re.match(r"^\d+[.,]?\d*\s*[a-z%ΩVWAm]*$", l, re.I):
            vals.append(l)
    out = {}
    for i in range(min(len(keys), len(vals))):
        raw = vals[i]
        num = re.sub(r"[^\d.,\-]","", raw).replace(",",".")
        try:
            out[keys[i]] = str(round(float(num),1))
        except:
            out[keys[i]] = raw
    return {k: out.get(k, "Non détecté") for k in expected_keys}

def send_to_sheet(id_panneau, row, sheet_id, ws_name):
    creds = Credentials.from_service_account_info(
        st.secrets["gspread_auth"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    client = gspread.authorize(creds)
    ws = client.open_by_key(sheet_id).worksheet(ws_name)
    ws.append_row([id_panneau] + row)

def compute_crop_on_original(img, bbox, L, T, canvas_w, canvas_h):
    left, top, width, height = bbox
    scale_x = img.width / canvas_w
    scale_y = img.height / canvas_h
    x = int(left * scale_x)
    y = int(top * scale_y)
    w = int(width * scale_x)
    h = int(height * scale_y)
    return img.crop((L + x, T + y, L + x + w, T + y + h))

# interface
uploaded_file = st.file_uploader("Téléverse une image (max 200 MB)", type=["jpg","png","jpeg"])

if not uploaded_file:
    st.info("📤 Téléverse d'abord une image.")
    st.stop()

# préparation de l'image
original = Image.open(uploaded_file).convert("RGB")
original = original.rotate(-90, expand=True)
w, h = original.size
L, R = int(w * 0.05), int(w * 0.85)
T, B = int(h * 0.3), int(h * 0.7)
img = original.crop((L, T, R, B))
st.image(img, use_container_width=True, caption="🖼️ Image optimisée")

# dimension du canevas
c_w = 300
c_h = int(c_w * img.height / img.width)

# debounce setup
st_ex.st_autorefresh(interval=1000, key="auto_refresh")

if "last_move" not in st.session_state:
    st.session_state.last_move = 0.0
if "crop_done" not in st.session_state:
    st.session_state.crop_done = False
if "prev_box" not in st.session_state:
    st.session_state.prev_box = None
if "rectangles" not in st.session_state:
    st.session_state.rectangles = [{
        "type": "rect",
        "left": 30, "top": 30,
        "width": 120, "height": 80,
        "fill": "rgba(0, 0, 255, 0.2)",
        "stroke": "blue", "strokeWidth": 2
    }]

st.subheader("🟦 Ajuste la zone (glisse/redimensionne)")

canvas_result = st_canvas(
    background_image=img,
    width=c_w,
    height=c_h,
    initial_drawing={"objects": st.session_state.rectangles},
    drawing_mode="transform",
    update_streamlit=True,
    key="crop_canvas"
)

# on détecte un mouvement de la boîte
if canvas_result.json_data and canvas_result.json_data.get("objects"):
    st.session_state.rectangles = canvas_result.json_data["objects"]
    obj = st.session_state.rectangles[0]
    current_box = (obj["left"], obj["top"], obj["width"], obj["height"])
    now = time.time()
    if current_box != st.session_state.prev_box:
        st.session_state.last_move = now
        st.session_state.crop_done = False
        st.session_state.prev_box = current_box

# on crop + OCR après 3 s d'inactivité
if (
    st.session_state.prev_box is not None
    and not st.session_state.crop_done
    and time.time() - st.session_state.last_move > 3
):
    # découpe
    cropped = compute_crop_on_original(
        original, st.session_state.prev_box, L, T, c_w, c_h
    ).convert("RGB")
    st.subheader("🔍 Image rognée")
    st.image(cropped, caption="📐 Zone sélectionnée")

    # amélioration contraste + OCR
    enhanced = ImageEnhance.Contrast(cropped).enhance(1.2)
    buf = io.BytesIO()
    enhanced.save(buf, format="JPEG")
    buf.seek(0)
    resp = requests.post(
        "https://api.ocr.space/parse/image",
        files={"file":("img.jpg", buf, "image/jpeg")},
        data={"apikey":"K81047805588957","language":"eng","OCREngine":2}
    )

    if resp.status_code == 200:
        txt = resp.json()["ParsedResults"][0]["ParsedText"]
        st.subheader("🔍 Texte brut")
        st.text(txt)

        ext = extract_ordered_fields(txt)
        st.subheader("📋 Résultats extraits")
        for k in TARGET_KEYS:
            st.write(f"{k} : {ext[k]}")

        if st.button("📤 Enregistrer dans Google Sheet"):
            try:
                send_to_sheet(
                    id_panneau,
                    [ext[k] for k in TARGET_KEYS],
                    sheet_id="1yhIVYOqibFnhKKCnbhw8v0f4n1MbfY_4uZhSotK44gc",
                    ws_name="Tests_Panneaux"
                )
                st.success("✅ Envoyé")
            except Exception as e:
                st.error(f"Erreur Sheets : {e}")
    else:
        st.error(f"OCR.space error {resp.status_code}")

    # téléchargement
    dl = io.BytesIO()
    enhanced.save(dl, format="JPEG", quality=90, optimize=True)
    st.download_button("📥 Télécharger", dl.getvalue(), "crop.jpg", "image/jpeg")

    st.session_state.crop_done = True

elif canvas_result.json_data and st.session_state.prev_box:
    # retour visuel sur le debounce
    elapsed = time.time() - st.session_state.last_move
    remaining = max(0, 3 - int(elapsed))
    st.info(f"Crop dans {remaining} s si pas de mouvement…")

else:
    st.info("👆 Déplace ou redimensionne le rectangle pour lancer le crop+OCR.")
