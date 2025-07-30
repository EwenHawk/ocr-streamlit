import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import numpy as np

st.set_page_config(page_title="✂️ Crop interactif", layout="centered")
st.title("🖼️ Sélectionne une zone à rogner")

uploaded_file = st.file_uploader("📤 Téléverse une image", type=["jpg", "png", "jpeg"])
if uploaded_file:
    img = Image.open(uploaded_file).convert("RGB")
    img_width, img_height = img.size
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
        st.subheader("🔎 Aperçu de l’image croppée")
        st.image(cropped_img, caption="✂️ Image rognée")

        # 📥 Télécharger
        if st.button("💾 Télécharger le crop"):
            cropped_img.save("image_crop.png")
            st.success("✅ Image enregistrée sous `image_crop.png`")

else:
    st.info("📌 Attends que l’image soit téléversée pour dessiner.")
