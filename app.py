import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image, ImageEnhance
import io, requests, re, gspread
from google.oauth2.service_account import Credentials

id_panneau = st.query_params.get("id_panneau", "")
TARGET_KEYS = ["Voc", "Isc", "Pmax", "Vpm", "Ipm"]

st.set_page_config(page_title="✂️ Rognage + OCR", layout="centered")
st.title("📸 Rognage + Retouche + OCR 🔎")

uploaded_file = st.file_uploader("Téléverse une image (max 200 MB)", type=["jpg","png","jpeg"])

# On garde un seul rectangle en session_state
if "rectangles" not in st.session_state:
    st.session_state.rectangles = [{
        "type": "rect",
        "left": 30,
        "top": 30,
        "width": 120,
        "height": 80,
        "fill": "rgba(0, 0, 255, 0.2)",
        "stroke": "blue",
        "strokeWidth": 2
    }]

def extract_ordered_fields(text, expected_keys=TARGET_KEYS):
    aliases = {
      "voc":"Voc","v_oc":"Voc",
      "isc":"Isc","lsc":"Isc","i_sc":"Isc","isci":"Isc",
      "pmax":"Pmax","p_max":"Pmax","pmax.":"Pmax",
      "vpm":"Vpm","v_pm":"Vpm","vpm.":"Vpm",
      "ipm":"Ipm","i_pm":"Ipm","ipm.":"Ipm","lpm":"Ipm"
    }
    def norm(k): return re.sub(r'[^a-zA-Z]','',k).lower()
    lines=[l.strip() for l in text.splitlines() if l.strip()]
    keys, vals = [], []
    for l in lines:
        k = norm(l)
        if k in aliases: keys.append(aliases[k])
        elif re.match(r"^\d+[.,]?\d*\s*[a-z%ΩVWAm]*$", l, re.I): vals.append(l)
    out={}
    for i in range(min(len(keys),len(vals))):
        raw=vals[i]
        num=re.sub(r"[^\d.,\-]","",raw).replace(",",".")
        try: out[keys[i]] = str(round(float(num),1))
        except: out[keys[i]] = raw
    return {k: out.get(k,"Non détecté") for k in expected_keys}

def send_to_sheet(id_panneau, row, sheet_id, ws_name):
    creds = Credentials.from_service_account_info(st.secrets["gspread_auth"],
                                                  scopes=["https://www.googleapis.com/auth/spreadsheets"])
    client = gspread.authorize(creds)
    ws = client.open_by_key(sheet_id).worksheet(ws_name)
    ws.append_row([id_panneau]+row)

if uploaded_file:
    original = Image.open(uploaded_file).convert("RGB")
    original = original.rotate(-90,expand=True)
    w,h = original.size
    L,R = int(w*0.05), int(w*0.85)
    T,B = int(h*0.3), int(h*0.7)
    img = original.crop((L,T,R,B))
    st.image(img, use_container_width=True, caption="🖼️ Image optimisée")

    # Dimensions canevas
    c_w = 300
    c_h = int(c_w * img.height / img.width)
    st.subheader("🟦 Ajuste la zone (glisse/redimensionne)")

    # --> ICI : initial_drawing doit être un DICT avec "objects"
    canvas_result = st_canvas(
        background_image=img,
        height=c_h,
        width=c_w,
        initial_drawing={"objects": st.session_state.rectangles},
        drawing_mode="transform",
        update_streamlit=True,
        key="crop_canvas"
    )

    if canvas_result.json_data and canvas_result.json_data.get("objects"):
        # Mise à jour du rectangle
        st.session_state.rectangles = canvas_result.json_data["objects"]
        obj = st.session_state.rectangles[0]

        # Passage en coordonnées réelles
        sx, sy = img.width/c_w, img.height/c_h
        x = int(obj["left"]*sx)
        y = int(obj["top"]*sy)
        w_sel = int(obj["width"]*sx)
        h_sel = int(obj["height"]*sy)

        cropped = original.crop((L+x, T+y, L+x+w_sel, T+y+h_sel)).convert("RGB")
        st.subheader("🔍 Image rognée")
        st.image(cropped, caption="📐 Zone sélectionnée")

        # OCR
        enhanced = ImageEnhance.Contrast(cropped).enhance(1.2)
        buf = io.BytesIO()
        enhanced.save(buf, format="JPEG"); buf.seek(0)
        resp = requests.post(
            "https://api.ocr.space/parse/image",
            files={"file":("img.jpg",buf,"image/jpeg")},
            data={"apikey":"K81047805588957","language":"eng","OCREngine":2}
        )

        if resp.status_code==200:
            txt = resp.json()["ParsedResults"][0]["ParsedText"]
            st.subheader("🔍 Texte brut")
            st.text(txt)
            ext = extract_ordered_fields(txt)
            st.subheader("📋 Résultats extraits")
            for k in TARGET_KEYS: st.write(f"{k} : {ext[k]}")
            if st.button("📤 Enregistrer dans Google Sheet"):
                try:
                    send_to_sheet(id_panneau,
                                  [ext[k] for k in TARGET_KEYS],
                                  sheet_id="1yhIVYOqibFnhKKCnbhw8v0f4n1MbfY_4uZhSotK44gc",
                                  ws_name="Tests_Panneaux")
                    st.success("✅ Envoyé")
                except Exception as e:
                    st.error(f"Erreur Sheets : {e}")
        else:
            st.error(f"OCR.space error {resp.status_code}")

        # Téléchargement
        dl = io.BytesIO()
        enhanced.save(dl, format="JPEG", quality=90, optimize=True)
        st.download_button("📥 Télécharger", dl.getvalue(), "crop.jpg", "image/jpeg")
    else:
        st.info("👆 Déplace ou redimensionne le rectangle pour lancer le crop+OCR.")
else:
    st.info("📤 Téléverse d'abord une image.")
