import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image

st.set_page_config(page_title="🖌️ Mon appli de dessin", layout="centered")

st.title("🎨 Application de dessin sur image croppée")

# 📂 Upload image
uploaded_file = st.file_uploader("Choisis une image", type=["jpg", "png", "jpeg"])
if uploaded_file:
    img = Image.open(uploaded_file).convert("RGB")
    img = img.rotate(-90, expand=True)
    img_width, img_height = img.size

    st.subheader("✂️ Paramètres du crop")
    x1 = st.slider("x1 (gauche)", 0, img_width, 0)
    x2 = st.slider("x2 (droite)", x1 + 1, img_width, img_width)
    y1 = st.slider("y1 (haut)", 0, img_height, 0)
    y2 = st.slider("y2 (bas)", y1 + 1, img_height, img_height)

    # ✂️ Crop image selon les sliders
    cropped_img = img.crop((x1, y1, x2, y2)).convert("RGB")
    canvas_width, canvas_height = cropped_img.size

    st.subheader("🖼️ Aperçu croppé")
    st.image(cropped_img, width=canvas_width)

    st.subheader("🎨 Dessine sur l’image")
    canvas_result = st_canvas(
        fill_color="rgba(0, 0, 255, 0.3)",  # couleur du pinceau
        stroke_width=4,
        background_image=cropped_img,
        update_streamlit=True,
        height=canvas_height,
        width=canvas_width,
        drawing_mode="freedraw",
        key="canvas",
    )

    # 🧪 Retour sur les objets dessinés
    if canvas_result.json_data and canvas_result.json_data["objects"]:
        st.write("✅ Objets dessinés :", canvas_result.json_data["objects"])
    else:
        st.write("😶 Aucun dessin pour le moment.")

    # 📤 Option d'enregistrement
    if canvas_result.image_data is not None:
        st.subheader("📥 Enregistrer ton dessin")
        from PIL import Image as PILImage
        import numpy as np

        result_img = PILImage.fromarray((canvas_result.image_data).astype(np.uint8))
        st.image(result_img, caption="🖼️ Image finale", use_column_width=True)
        if st.button("💾 Télécharger en PNG"):
            result_img.save("dessin_exporté.png")
            st.success("Dessin sauvegardé en `dessin_exporté.png` ✅")

else:
    st.info("📤 Téléverse une image pour commencer.")
