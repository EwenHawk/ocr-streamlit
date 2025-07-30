import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image, ImageEnhance
import io
import requests
import re
import gspread
from google.oauth2.service_account import Credentials

# 🆔 Récupération de l'ID_Panneau depuis l'URL
id_panneau = st.experimental_get_query_params().get("id_panneau", [""])[0]
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

# Désactive le scroll sur le canvas pour améliorer le tactile
st.markdown("""
<style>
  canvas { touch-action: none; }
</style>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader("Téléverse une image (max 200 MB)", type=["jpg", "png", "jpeg"])

# 📄 Fonction d’extraction des champs OCR
def extract_ordered_fields(text, expected_keys=TARGET_KEYS):
    aliases = {
        "voc": "Voc", "v_oc": "Voc",
        "isc": "Isc", "lsc": "Isc", "i_sc": "Isc", "isci": "Isc",
        "pmax": "Pmax", "p_max": "Pmax",
        "vpm": "Vpm", "v_pm": "Vpm",
        "ipm": "Ipm", "i_pm": "Ipm",
    }
    def normalize_key(raw):
        return re.sub(r'[^a-zA-Z]', '', raw).lower()

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    keys, vals = [], []
    for line in lines:
        nk = normalize_key(line)
        if nk in aliases:
            keys.append(aliases[nk])
        elif re.match(r"^\d+[.,]?\d*\s*[a-z%ΩVWAm]*$", line, re.IGNORECASE):
            vals.append(line)

    result = {}
    for i in range(min(len(keys), len(vals))):
        raw = vals[i]
        num = re.sub(r"[^\d.,\-]", "", raw).replace(",", ".")
        try:
            result[keys[i]] = str(round(float(num), 1))
        except:
            result[keys[i]] = raw

    return {k: result.get(k, "Non détecté") for k in expected_keys}

# 📤 Fonction d’envoi vers Google Sheet
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
    # 1. Chargement et rotation
    original = Image.open(uploaded_file).convert("RGB")
    original = original.rotate(-90, expand=True)

    # 2. Découpage « général »
    w, h = original.size
    left, right = int(w * 0.05), int(w * 0.85)
    top, bottom = int(h * 0.3), int(h * 0.7)
    preview = original.crop((left, top, right, bottom))
    st.subheader("🖼️ Image optimisée")
    st.image(preview, use_container_width=True)

    # 3. Options Canvas
    st.sidebar.subheader("🔧 Options de sélection")
    canvas_width = st.sidebar.slider("Largeur du canvas", 200, 800, 400)
    drawing_mode = st.sidebar.radio("Mode de dessin", ("rect", "line"), index=1)
    canvas_height = int(canvas_width * preview.height / preview.width)

    st.subheader("🟦 Sélectionne une zone")
    canvas_result = st_canvas(
        background_image=preview,
        width=canvas_width,
        height=canvas_height,
        drawing_mode=drawing_mode,
        stroke_width=2,
        stroke_color="blue",
        update_streamlit=True,
        key="canvas_crop"
    )

    # 4. Traitement de la sélection
    if canvas_result.json_data and canvas_result.json_data["objects"]:
        obj = canvas_result.json_data["objects"][0]
        scale_x = preview.width  / canvas_width
        scale_y = preview.height / canvas_height

        if drawing_mode == "rect":
            x = int(obj["left"]   * scale_x)
            y = int(obj["top"]    * scale_y)
            w_sel = int(obj["width"]  * scale_x)
            h_sel = int(obj["height"] * scale_y)

        elif drawing_mode == "line":
            # obj.x1, y1, x2, y2 sont en coord canvas
            x1 = int(obj["x1"] * scale_x)
            y1 = int(obj["y1"] * scale_y)
            x2 = int(obj["x2"] * scale_x)
            y2 = int(obj["y2"] * scale_y)
            x, y = min(x1, x2), min(y1, y2)
            w_sel = abs(x2 - x1)
            h_sel = abs(y2 - y1)

        # recadrage final sur l’original
        box = (left + x, top + y, left + x + w_sel, top + y + h_sel)
        cropped = original.crop(box).convert("RGB")
        st.subheader("🔍 Image rognée")
        st.image(cropped, use_container_width=True)

        # 5. Amélioration + OCR
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
            st.text_area("", ocr_text, height=150)

            extracted = extract_ordered_fields(ocr_text)
            st.subheader("📋 Champs extraits")
            for k in TARGET_KEYS:
                st.write(f"{k} : {extracted[k]}")

            # 6. Envoi Google Sheet
            if st.button("📤 Enregistrer dans Google Sheet"):
                try:
                    sheet_id = "1yhIVYOqibFnhKKCnbhw8v0f4n1MbfY_4uZhSotK44gc"
                    ws_name  = "Tests_Panneaux"
                    row = [extracted[k] for k in TARGET_KEYS]
                    send_to_sheet(id_panneau, row, sheet_id, ws_name)
                    st.success("✅ Données envoyées.")
                except Exception as e:
                    st.error(f"❌ Erreur : {e}")
        else:
            st.error(f"❌ OCR.space a renvoyé {resp.status_code}")

        # 7. Téléchargement final
        final_buf = io.BytesIO()
        enhanced.save(final_buf, format="JPEG", quality=90, optimize=True)
        st.download_button(
            label="📥 Télécharger l'image finale",
            data=final_buf.getvalue(),
            file_name="image_rognée.jpg",
            mime="image/jpeg"
        )
    else:
        st.info("👆 Trace un rectangle ou une ligne pour lancer le traitement.")
else:
    st.info("📤 Choisis une image à traiter.")
