import streamlit as st
import streamlit.components.v1 as components
from streamlit_drawable_canvas import st_canvas
from PIL import Image, ImageEnhance
import io
import requests
import re
import gspread
from google.oauth2.service_account import Credentials

# 0) Patch CSS + JS pour convertir touch → mouse et désactiver le scroll
components.html("""
<style>
  canvas { touch-action: none; }
</style>
<script>
// Greffe sur chaque <canvas> la conversion touch→mouse
function patchCanvas() {
  document.querySelectorAll("canvas").forEach(c => {
    if (c.dataset.patched) return;
    ["touchstart","touchmove","touchend"].forEach(evt => {
      c.addEventListener(evt, e => {
        const t = e.touches[0];
        const map = { touchstart:"mousedown", touchmove:"mousemove", touchend:"mouseup" };
        const me = new MouseEvent(map[evt], {
          clientX: t.clientX, clientY: t.clientY,
          bubbles: true, cancelable: true, view: window
        });
        c.dispatchEvent(me);
        e.preventDefault();
      });
    });
    c.dataset.patched = true;
  });
}
// Réessaie toutes les 300 ms (rechargements Streamlit)
setInterval(patchCanvas, 300);
</script>
""", height=0)

# 1) Setup Streamlit
st.set_page_config(page_title="✂️ Rognage + OCR", layout="centered")
st.title("📸 Rognage + Retouche + OCR 🔎")

TARGET_KEYS = ["Voc", "Isc", "Pmax", "Vpm", "Ipm"]
id_panneau  = st.experimental_get_query_params().get("id_panneau", [""])[0]

# 2) Uploader
uploaded = st.file_uploader("Téléverse une image (jpg/png/jpeg)", type=["jpg","png","jpeg"])
if not uploaded:
    st.info("📤 Choisis une image pour commencer")
    st.stop()

# 3) Ouvre + pivote + recadre un aperçu central
orig = Image.open(uploaded).convert("RGB").rotate(-90, expand=True)
W, H = orig.size
box_general = (int(W*0.05), int(H*0.3), int(W*0.85), int(H*0.7))
preview = orig.crop(box_general)
st.subheader("🖼️ Aperçu optimisé")
st.image(preview, use_container_width=True)

# 4) Canvas en MODE RECT
st.subheader("🟦 Trace un rectangle (début→fin) pour sélectionner")
w_canvas = st.sidebar.slider("Largeur du canvas", 200, 800, 400)
h_canvas = int(w_canvas * preview.height / preview.width)

canvas_data = st_canvas(
    background_image=preview,
    width=w_canvas,
    height=h_canvas,
    drawing_mode="rect",        # ← mode rectangle pur
    stroke_width=2,
    stroke_color="blue",
    key="canvas_crop",
    update_streamlit=True
)

# 5) Si on a tracé un rectangle, calcule le crop
if not (canvas_data.json_data and canvas_data.json_data["objects"]):
    st.info("👆 Trace un rectangle pour continuer")
    st.stop()

obj = canvas_data.json_data["objects"][0]
sx, sy = preview.width / w_canvas, preview.height / h_canvas
x, y   = int(obj["left"] * sx), int(obj["top"] * sy)
w_sel  = int(obj["width"] * sx)
h_sel  = int(obj["height"] * sy)

# 6) Recadrage définitif sur l'image originale
crop_box = (
    box_general[0] + x,
    box_general[1] + y,
    box_general[0] + x + w_sel,
    box_general[1] + y + h_sel
)
cropped = orig.crop(crop_box)
st.subheader("🔍 Image sélectionnée")
st.image(cropped, use_container_width=True)

# 7) Contraste + OCR
enh = ImageEnhance.Contrast(cropped).enhance(1.2)
buf = io.BytesIO()
enh.save(buf, format="JPEG")
buf.seek(0)

st.subheader("🔍 Résultat OCR")
resp = requests.post(
    "https://api.ocr.space/parse/image",
    files={"file": ("image.jpg", buf, "image/jpeg")},
    data={"apikey": "helloworld", "language": "eng", "OCREngine": 2}
)
if resp.status_code != 200:
    st.error(f"❌ OCR.space a renvoyé {resp.status_code}")
    st.stop()

ocr_text = resp.json()["ParsedResults"][0]["ParsedText"]
st.text_area("Texte brut", ocr_text, height=150)

# 8) Extraction intelligente
def extract_fields(text):
    aliases = {
      "voc":"Voc","v_oc":"Voc",
      "isc":"Isc","lsc":"Isc","i_sc":"Isc",
      "pmax":"Pmax","p_max":"Pmax",
      "vpm":"Vpm","v_pm":"Vpm",
      "ipm":"Ipm","i_pm":"Ipm"
    }
    def norm(k): return re.sub(r'[^A-Za-z]','',k).lower()

    lines = [l for l in text.splitlines() if l.strip()]
    keys, vals = [], []
    for l in lines:
        nk = norm(l)
        if nk in aliases:
            keys.append(aliases[nk])
        elif re.match(r"^\d+[.,]?\d*", l):
            vals.append(l.strip())

    out = {}
    for i in range(min(len(keys), len(vals))):
        raw = vals[i]
        num = re.sub(r"[^\d.,-]", "", raw).replace(",",".")
        try: out[keys[i]] = str(round(float(num),1))
        except: out[keys[i]] = raw

    return {k: out.get(k, "Non détecté") for k in TARGET_KEYS}

extracted = extract_fields(ocr_text)
st.subheader("📋 Champs extraits")
for k in TARGET_KEYS:
    st.write(f"{k} : {extracted[k]}")

# 9) Envoi vers Google Sheet
def send_to_sheet(id_panel, row, sheet_id, ws_name):
    creds = Credentials.from_service_account_info(
        st.secrets["gspread_auth"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    client = gspread.authorize(creds)
    ws = client.open_by_key(sheet_id).worksheet(ws_name)
    ws.append_row([id_panel] + row)

if st.button("📤 Enregistrer dans Google Sheet"):
    try:
        send_to_sheet(
            id_panneau,
            [extracted[k] for k in TARGET_KEYS],
            "1yhIVYOqibFnhKKCnbhw8v0f4n1MbfY_4uZhSotK44gc",
            "Tests_Panneaux"
        )
        st.success("✅ Données envoyées.")
    except Exception as e:
        st.error(f"❌ {e}")

# 10) Téléchargement final
final_buf = io.BytesIO()
enh.save(final_buf, format="JPEG", quality=90, optimize=True)
st.download_button(
    "📥 Télécharger l'image rognée",
    final_buf.getvalue(),
    file_name="image_rognée.jpg",
    mime="image/jpeg"
)
