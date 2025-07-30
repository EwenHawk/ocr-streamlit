import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image, ImageEnhance
import io
import requests

st.set_page_config(page_title="✂️ Rognage + OCR", layout="centered")
st.title("📸 Rognage + Retouche + OCR 🔎")

uploaded_file = st.file_uploader("Téléverse une image (max 200 MB)", type=["jpg", "png", "jpeg"])

if uploaded_file:
    quality = 90
    api_key = "K81047805588957"
    ocr_url = "https://api.ocr.space/parse/image"

    original_img = Image.open(uploaded_file).convert("RGB")
    original_img = original_img.rotate(-90, expand=True)

    w, h = original_img.size
    left = int(w * 0.05)
    right = int(w * 0.85)
    top = int(h * 0.3)
    bottom = int(h * 0.7)
    img = original_img.crop((left, top, right, bottom))

    st.image(img, caption="🖼️ Image affichée (optimisée)", use_container_width=True)

    canvas_width = 300
    canvas_height = int(canvas_width * img.height / img.width)
    st.subheader("🟦 Sélectionne une zone")
    canvas_result = st_canvas(
        background_image=img,
        height=canvas_height,
        width=canvas_width,
        drawing_mode="rect",
        stroke_width=2,
        stroke_color="blue",
        update_streamlit=True,
        key="canvas_crop"
    )

    if canvas_result.json_data and canvas_result.json_data["objects"]:
        obj = canvas_result.json_data["objects"][0]

        scale_x = img.width / canvas_width
        scale_y = img.height / canvas_height
        x = int(obj["left"] * scale_x)
        y = int(obj["top"] * scale_y)
        w_sel = int(obj["width"] * scale_x)
        h_sel = int(obj["height"] * scale_y)

        crop_left = left + x
        crop_top = top + y
        crop_right = crop_left + w_sel
        crop_bottom = crop_top + h_sel

        cropped = original_img.crop((crop_left, crop_top, crop_right, crop_bottom)).convert("RGB")
        st.subheader("🔍 Image rognée")
        st.image(cropped, caption="📐 Zone sélectionnée")

        enhancer = ImageEnhance.Contrast(cropped)
        enhanced = enhancer.enhance(1.2)

        img_bytes = io.BytesIO()
        enhanced.save(img_bytes, format="JPEG")
        img_bytes.seek(0)

        response = requests.post(
            ocr_url,
            files={"file": ("image.jpg", img_bytes, "image/jpeg")},
            data={"apikey": api_key, "language": "eng", "OCREngine": 2}
        )

        if response.status_code == 200:
            result_json = response.json()
            ocr_text = result_json["ParsedResults"][0]["ParsedText"]

            st.subheader("🔍 Texte OCR brut")
            st.text(ocr_text)

            TARGET_KEYS = ["Voc", "Isc", "Pmax", "Vpm", "Ipm"]

            def extract_by_alias(text):
                aliases = {
                    "voc": "Voc", "v_oc": "Voc",
                    "isc": "Isc", "lsc": "Isc", "i_sc": "Isc",
                    "pmax": "Pmax", "p_max": "Pmax", "pmax.": "Pmax",
                    "vpm": "Vpm", "v_pm": "Vpm", "vpm.": "Vpm",
                    "ipm": "Ipm", "i_pm": "Ipm", "ipm.": "Ipm", "lpm": "Ipm"
                }
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                fields = {}
                for i, line in enumerate(lines):
                    for alias, key in aliases.items():
                        if alias.lower() in line.lower():
                            if any(unit in line for unit in ["V", "A", "W"]):
                                fields[key] = line
                            elif i + 1 < len(lines) and any(u in lines[i+1] for u in ["V", "A", "W"]):
                                fields[key] = lines[i+1]
                return fields

            def extract_ordered_by_position(text, expected_keys):
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                values_only = [
                    line for line in lines
                    if not line.endswith(":") and any(unit in line for unit in ["V", "A", "W"])
                ]
                fields = {}
                for key, value in zip(expected_keys, values_only):
                    fields[key] = value
                return fields

            extracted = extract_by_alias(ocr_text)
            if len(extracted) < len(TARGET_KEYS):
                extracted = extract_ordered_by_position(ocr_text, TARGET_KEYS)

            st.subheader("📋 Champs extraits OCR")
            for key in TARGET_KEYS:
                val = extracted.get(key, "non détecté")
                st.text(f"{key} : {val}")
        else:
            st.error(f"❌ Erreur OCR.space ({response.status_code}) : {response.text}")

        final_buffer = io.BytesIO()
        enhanced.save(final_buffer, format="JPEG", quality=quality, optimize=True)
        st.download_button(
            label=f"📥 Télécharger (qualité {quality}, taille ~{round(final_buffer.tell() / 1024 / 1024, 2)} MB)",
            data=final_buffer.getvalue(),
            file_name="image_rognee.jpg",
            mime="image/jpeg"
        )
    else:
        st.info("👆 Dessine un rectangle sur l'image pour sélectionner une zone.")
else:
    st.info("📤 Choisis une image à traiter.")
