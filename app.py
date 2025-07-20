import streamlit as st
import requests
from PIL import Image
import io
import re
from streamlit_drawable_canvas import st_canvas

# 📌 Initialisation de l'état
if "selection_mode" not in st.session_state:
    st.session_state.selection_mode = False

# 🧠 Fonction de correspondance robuste champ → valeur
def extract_ordered_fields(text, expected_keys=["Voc", "Isc", "Pmax", "Vpm", "Ipm"]):
    aliases = {
        "voc": "Voc", "v_oc": "Voc",
        "isc": "Isc", "lsc": "Isc", "i_sc": "Isc",
        "pmax": "Pmax", "p_max": "Pmax", "pmax.": "Pmax",
        "vpm": "Vpm", "vpm.": "Vpm", "v_pm": "Vpm",
        "ipm": "Ipm", "ipm.": "Ipm", "i_pm": "Ipm"
    }

    lines = [line.strip().lower() for line in text.splitlines() if line.strip()]
    keys_found = []
    values_found = []

    for line in lines:
        if line.endswith(":"):
            raw_key = line.rstrip(":").strip()
            if raw_key in aliases:
                keys_found.append(aliases[raw_key])
        else:
            match = re.match(r"^\d+[.,]?\d*\s*[a-z%ΩVWAm]*$", line, re.IGNORECASE)
            if match:
                values_found.append(match.group(0).strip())

    result = {}
    for i in range(min(len(keys_found), len(values_found))):
        result[keys_found[i]] = values_found[i]

    final_result = {key: result.get(key, "Non détecté") for key in expected_keys}
    return final_result

# 🔧 API OCR.Space
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

# 🛠️ Configuration Streamlit
st.set_page_config(page_title="OCR ToolJet", page_icon="📤", layout="centered")
st.title("🔍 OCR ordonné + extraction technique")

# 📥 Upload image
uploaded_file = st.file_uploader("📸 Importer une image technique", type=["jpg", "jpeg", "png"])
if uploaded_file:
    img = Image.open(uploaded_file)
    rotation = st.selectbox("🔁 Rotation", [0, 90, 180, 270], index=0)
    img = img.rotate(-rotation, expand=True)

    # 🖼️ Compression
    max_width = 800
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.Resampling.LANCZOS)

    st.image(img, caption="🖼️ Aperçu", use_container_width=False)

    # 🎯 Bouton pour activer la sélection
    if not st.session_state.selection_mode:
        if st.button("🎯 Je sélectionne une zone à analyser"):
            st.session_state.selection_mode = True

    # 🟧 Canvas actif
    if st.session_state.selection_mode:
        canvas_width, canvas_height = img.size
        initial_rect = {
            "objects": [{
                "type": "rect",
                "left": canvas_width // 4,
                "top": canvas_height // 4,
                "width": canvas_width // 2,
                "height": canvas_height // 3,
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

        # ✂️ Découpe + OCR
        if canvas_result.json_data and canvas_result.json_data["objects"]:
            rect = canvas_result.json_data["objects"][0]
            x, y = rect["left"], rect["top"]
            w, h = rect["width"], rect["height"]
            cropped_img = img.crop((x, y, x + w, y + h))
            st.image(cropped_img, caption="📌 Zone sélectionnée", use_container_width=False)

            if st.button("📤 Lancer le traitement OCR"):
                img_bytes = io.BytesIO()
                cropped_img.save(img_bytes, format="JPEG", quality=70)
                img_bytes.seek(0)
                ocr_result = ocr_space_api(img_bytes)

                if "error" in ocr_result:
                    st.error(f"❌ Erreur OCR : {ocr_result['error']}")
                else:
                    raw_text = ocr_result.get("ParsedResults", [{}])[0].get("ParsedText", "")
                    st.subheader("📄 Texte OCR brut")
                    st.code(raw_text[:3000], language="text")

                    # 💡 Extraction ordonnée + alias
                    results = extract_ordered_fields(raw_text)
                    st.subheader("📊 Champs extraits avec robustesse :")
                    for key, value in results.items():
                        st.write(f"🔹 **{key}** → {value}")

                    # 🔔 Vérification
                    missing = [k for k, v in results.items() if v == "Non détecté"]
                    if missing:
                        st.warning(f"⚠️ Champs non détectés : {', '.join(missing)}")
                    else:
                        st.success("✅ Tous les champs sont détectés !")
