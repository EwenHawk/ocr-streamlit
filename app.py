# app.py

import time
import io
import re
import requests

import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image, ImageEnhance

import gspread
from google.oauth2.service_account import Credentials

# 1) Paramètres généraux
TARGET_KEYS = ["Voc", "Isc", "Pmax", "Vpm", "Ipm"]
# Remplacement de experimental_get_query_params par st.query_params
id_panneau = st.query_params.get("id_panneau", [""])[0]

st.set_page_config(page_title="✂️ Rognage + OCR", layout="centered")
st.title("📸 Rognage + Retouche + OCR 🔎")

# 2) Helpers

def extract_ordered_fields(text, expected_keys=TARGET_KEYS):
    aliases = {
        "voc":"Voc","v_oc":"Voc",
        "isc":"Isc","lsc":"Isc","i_sc":"Isc","isci":"Isc",
        "pmax":"Pmax","p_max":"Pmax","pmax.":"Pmax",
        "vpm":"Vpm","v_pm":"Vpm","vpm.":"Vpm",
        "ipm":"Ipm","i_pm":"Ipm","ipm.":"Ipm","lpm":"Ipm"
    }
    def norm(s): return re.sub(r'[^a-zA-Z]','', s).lower()
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
    sx, sy = img.width/canvas_w, img.height/canvas_h
    x, y = int(left*sx), int(top*sy)
    w, h = int(width*sx), int(height*sy)
    return img.crop((L+x, T+y, L+x+w, T+y+h))

def autorefresh(interval_ms=1000, key="last_refresh"):
    """
    Relance le script toutes les interval_ms tant que crop_done=False.
    """
    if st.session_state.get("crop_done", False):
        return
    now = time.time()
    if key not in st.session_state:
        st.session_state[key] = now
    if now - st.session_state[key] > interval_ms/1000:
        st.session_state[key] = now
        st.experimental_rerun()

# 3) Upload et préparation
uploaded = st.file_uploader("Téléverse une image (max 200 MB)", type=["jpg","png","jpeg"])
if not uploaded:
    st.info("📤 Téléverse d'abord une image.")
    st.stop()

original = Image.open(uploaded).convert("RGB")
original = original.rotate(-90, expand=True)
w, h = original.size
L, R = int(w*0.05), int(w*0.85)
T, B = int(h*0.3), int(h*0.7)
img = original.crop((L, T, R, B))
st.image(img, use_container_width=True, caption="🖼️ Image optimisée")

# 4) Canvas + debounce
c_w = 300
c_h = int(c_w * img.height / img.width)

# état session
if "last_move" not in st.session_state:
    st.session_state.last_move = 0.0
if "crop_done" not in st.session_state:
    st.session_state.crop_done = False
if "prev_box" not in st.session_state:
    st.session_state.prev_box = None
if "rectangles" not in st.session_state:
    st.session_state.rectangles = [{
        "type": "rect", "left": 30, "top": 30,
        "width": 120, "height": 80,
        "fill": "rgba(0, 0, 255, 0.2)",
        "stroke": "blue", "strokeWidth": 2
    }]

st.subheader("🟦 Ajuste la zone (glisse/redimensionne)")

# relance auto tant que crop pas fait
autorefresh(1000)

c = st_canvas(
    background_image=img,
    width=c_w, height=c_h,
    initial_drawing={"objects": st.session_state.rectangles},
    drawing_mode="transform",
    update_streamlit=True,
    key="crop_canvas",
)

# détecter chaque mouvement
if c.json_data and c.json_data.get("objects"):
    st.session_state.rectangles = c.json_data["objects"]
    o = st.session_state.rectangles[0]
    box = (o["left"], o["top"], o["width"], o["height"])
    now = time.time()
    if box != st.session_state.prev_box:
        st.session_state.last_move = now
        st.session_state.crop_done = False
        st.session_state.prev_box = box

# 5) Crop + OCR après 3 s d’inactivité
if (
    st.session_state.prev_box is not None
    and not st.session_state.crop_done
    and time.time() - st.session_state.last_move > 3
):
    # découpe
    crop = compute_crop_on_original(
        original, st.session_state.prev_box, L, T, c_w, c_h
    ).convert("RGB")
    st.subheader("🔍 Image rognée")
    st.image(crop, caption="📐 Zone sélectionnée")

    # contraste + OCR
    enh = ImageEnhance.Contrast(crop).enhance(1.2)
    buf = io.BytesIO(); enh.save(buf, "JPEG"); buf.seek(0)
    r = requests.post(
        "https://api.ocr.space/parse/image",
        files={"file":("img.jpg", buf, "image/jpeg")},
        data={"apikey":"K81047805588957","language":"eng","OCREngine":2}
    )

    if r.status_code == 200:
        txt = r.json()["ParsedResults"][0]["ParsedText"]
        st.subheader("🔍 Texte brut")
        st.text(txt)

        ext = extract_ordered_fields(txt)
        st.subheader("📋 Résultats extraits")
        for k in TARGET_KEYS:
            st.write(f"{k} : {ext[k]}")

        if st.button("📤 Envoyer dans Google Sheet"):
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
        st.error(f"OCR.space error {r.status_code}")

    # bouton téléchargement
    dl = io.BytesIO()
    enh.save(dl, "JPEG", quality=90, optimize=True)
    st.download_button("📥 Télécharger", dl.getvalue(), "crop.jpg", "image/jpeg")

    st.session_state.crop_done = True

elif c.json_data and st.session_state.prev_box:
    elapsed = time.time() - st.session_state.last_move
    remaining = max(0, 3 - int(elapsed))
    st.info(f"Crop dans {remaining}s…")

else:
    st.info("👆 Ajustez le rectangle pour lancer le crop+OCR.")
