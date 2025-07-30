import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import numpy as np
import io

st.set_page_config(page_title="✂️ Crop interactif compressé", layout="centered")
st.title("🖼️ Rogne et compresse ton image")

uploaded_file = st.file_uploader("📤 Téléverse une image", type=["jpg", "png", "jpeg"])
if uploaded_file:
    img = Image.open(uploaded_file).convert("RGB")
    img_width, img_height = img.size
    img = img.rotate(-90, expand=True)

    # ✂️ Rognage automatique proportionnel
    w, h = img.size
    left = int(w * 0.05)
    right = int(w * 0.85)
    top = int(h * 0.3)
    bottom = int(h * 0.7)
    img = img.crop((left, top, right, bottom))
    st.image(img, caption="📸 Image originale", use_container_width=True)

    st.subheader("🎯 Dessine un rectangle de sélection")
    canvas_result = st_canvas(
        fill_color="rgba(255, 0, 0, 0.3)",
        stroke_width=2,
        background_image=img,
        update_streamlit=True,
        height=img_height,
        width=img_width,
        drawing_mode="rect",
        key="canvas_crop",
    )

    if canvas_result.json_data and canvas_result.json_data["objects"]:
        obj = canvas_result.json_data["objects"][0]
        left = int(obj["left"])
        top = int(obj["top"])
        width = int(obj["width"])
        height = int(obj["height"])
        right = left + width
        bottom = top + height

        cropped_img = img.crop((left, top, right, bottom)).convert("RGB")
        st.subheader("🔍 Aperçu de l’image croppée")
        st.image(cropped_img, caption="✂️ Image rognée")

        st.subheader("🧪 Options de compression")
        format_choice = st.selectbox("Format de sortie", ["JPEG", "WebP"])
        quality = st.slider("Qualité de compression (%)", 80, 100, 95)

        buffer = io.BytesIO()
        cropped_img.save(
            buffer,
            format=format_choice,
            quality=quality,
            optimize=True
        )
        buffer.seek(0)

        st.download_button(
            label="📥 Télécharger l’image compressée",
            data=buffer.getvalue(),
            file_name=f"image_compressée.{format_choice.lower()}",
            mime=f"image/{format_choice.lower()}"
        )
else:
    st.info("🪄 Téléverse une image pour commencer.")
