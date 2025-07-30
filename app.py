import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image, ImageEnhance
import io
import requests
import re
import gspread
from google.oauth2.service_account import Credentials

# 1) Configuration de la page et constantes
st.set_page_config(page_title="✂️ Rognage + OCR", layout="centered")
st.title("📸 Rognage + Retouche + OCR 🔎")

TARGET_KEYS = ["Voc", "Isc", "Pmax", "Vpm", "Ipm"]

# 2) Patch CSS + JS pour activer le dessin rect sur tactile
st.markdown("""
<style>
  canvas {
    touch-action: none;
  }
</style>
<script>
// On cherche tous les <canvas> et on y greffe la conversion touch→mouse
function patchCanvas() {
  const canvases = document.querySelectorAll('canvas');
  canvases.forEach(canvas => {
    if (canvas.dataset.patched) return;
    ['touchstart','touchmove','touchend'].forEach(evtType => {
      canvas.addEventListener(evtType, function(e) {
        const t = e.touches[0];
        const map = { touchstart:'mousedown', touchmove:'mousemove', touchend:'mouseup' };
        const me = new MouseEvent(map[evtType], {
          clientX: t.clientX,
          clientY: t.clientY,
          bubbles: true,
          cancelable: true,
          view: window
        });
        canvas.dispatchEvent(me);
        e.preventDefault();
      });
    });
    canvas.dataset.patched = true;
  });
}
// On réessaie fréquemment (cover reloads de Streamlit)
setInterval(patchCanvas, 500);
</script>
""", unsafe_allow_html=True)

# 3) Uploader + lecture
uploaded = st.file_uploader("Téléverse une image (jpg, png, jpeg)", type=["jpg","png","jpeg"])
if not uploaded:
    st.info("📤 Choisis une image pour commencer")
    st.stop()

# 4) Ouvrir + pivoter + recadrer la zone générale
orig = Image.open(uploaded).convert("RGB")
orig = orig.rotate(-90, expand=True)
w, h = orig.size
crop_box_general = (
    int(w*0.05), int(h*0.3),
    int(w*0.85), int(h*0.7)
)
preview = orig.crop(crop_box_general)
st.subheader("🖼️ Aperçu recadré")
st.image(preview, use_container_width=True)

# 5) Affichage du canvas en mode RECT
st.subheader("🟦 Trace un rectangle (début→fin) pour sélectionner")
canvas_w = st.sidebar.slider("Largeur canvas", 200, 800, 300)
canvas_h = int(canvas_w * preview.height / preview.width)

canvas_data = st_canvas(
    background_image=preview,
    width=canvas_w,
    height=canvas_h,
    drawing_mode="rect",      # ← forçage en mode rectangle
    stroke_width=2,
    stroke_color="blue",
    key="select_rect",
    update_streamlit=True,
)

# 6) Si un objet a été dessiné, on récupère le rectangle
if not (canvas_data.json_data and canvas_data.json_data["objects"]):
    st.info("👆 Trace un rectangle pour continuer")
    st.stop()

obj = canvas_data.json_data["objects"][0]
scale_x = preview.width  / canvas_w
scale_y = preview.height / canvas_h

x0 = int(obj["left" ] * scale_x)
y0 = int(obj["top"  ] * scale_y)
w0 = int(obj["width"] * scale_x)
h0 = int(obj["height"]* scale_y)

# 7) Recadrage définitif sur l'image d'origine
final_box = (
    crop_box_general[0] + x0,
    crop_box_general[1] + y0,
    crop_box_general[0] + x0 + w0,
    crop_box_general[1] + y0 + h0
)
crop = orig.crop(final_box)
st.subheader("🔍 Zone sélectionnée")
st.image(crop, use_container_width=True)

# 8) Contraste + OCR
enh = ImageEnhance.Contrast(crop).enhance(1.2)
buf = io.BytesIO()
enh.save(buf, format="JPEG")
buf.seek(0)

st.subheader("🔍 Résultat OCR")
resp = requests.post(
    "https://api.ocr.space/parse/image",
    files={"file": ("img.jpg", buf, "image/jpeg")},
    data={"apikey": "K81047805588957", "language": "eng", "OCREngine": 2}
)

if resp.status_code != 200:
    st.error(f"Erreur OCR.space {resp.status_code}")
    st.stop()

ocr_text = resp.json()["ParsedResults"][0]["ParsedText"]
st.text_area("Texte brut", ocr_text, height=150)

# 9) Extraction des champs
def extract_fields(text):
    aliases = {
      "voc":"Voc","v_oc":"Voc",
      "isc":"Isc","lsc":"Isc","i_sc":"Isc",
      "pmax":"Pmax","p_max":"Pmax",
      "vpm":"Vpm","v_pm":"Vpm",
      "ipm":"Ipm","i_pm":"Ipm"
    }
    def norm(k): return re.sub(r'[^a-zA-Z]','',k).lower()
    lines = [l for l in text.splitlines() if l.strip()]
    found_k, found_v = [], []
    for line in lines:
        nk = norm(line)
        if nk in aliases:
            found_k.append(aliases[nk])
        elif re.match(r"^\\d+[.,]?\\d*", line):
            found_v.append(line.strip())
    res = {}
    for i in range(min(len(found_k), len(found_v))):
        v = found_v[i]
        num = re.sub(r"[^\d.,-]","",v).replace(",",".")
        try: res[found_k[i]] = str(round(float(num),1))
        except: res[found_k[i]] = v
    return {k: res.get(k, "Non détecté") for k in TARGET_KEYS}

fields = extract_fields(ocr_text)
st.subheader("📋 Valeurs extraites")
for k in TARGET_KEYS:
    st.write(f"{k} : {fields[k]}")

# 10) Envoi vers Google Sheets
def send_sheet(id_panel, row, sheet_key, ws):
    creds = Credentials.from_service_account_info(st.secrets["gspread_auth"],
                        scopes=["https://www.googleapis.com/auth/spreadsheets"])
    client = gspread.authorize(creds)
    client.open_by_key(sheet_key).worksheet(ws).append_row([id_panel] + row)

if st.button("📤 Envoyer dans Google Sheet"):
    try:
        send_sheet(
            st.experimental_get_query_params().get("id_panneau", [""])[0],
            [fields[k] for k in TARGET_KEYS],
            "1yhIVYOqibFnhKKCnbhw8v0f4n1MbfY_4uZhSotK44gc",
            "Tests_Panneaux"
        )
        st.success("✅ Enregistré !")
    except Exception as e:
        st.error(f"❌ {e}")

# 11) Téléchargement final
final_buf = io.BytesIO()
enh.save(final_buf, format="JPEG", quality=90, optimize=True)
st.download_button(
    "📥 Télécharger l'image rognée",
    final_buf.getvalue(),
    file_name="image_rognée.jpg",
    mime="image/jpeg"
)
