import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io

st.set_page_config(page_title="✂️ Rognage par cadre", layout="centered")
st.title("📸 Rognage d'image visuel")

# 📤 Téléversement
uploaded_file = st.file_uploader("Téléverse une image", type=["jpg", "png", "jpeg"])
if uploaded_file:
    img = Image.open(uploaded_file).convert("RGB")
    img = img.rotate(-90, expand=True)  # rotation automatique si nécessaire

    width, height = img.size

    # 🧰 Canvas avec mode rectangle
    st.subheader("🟦 Dessine un cadre de sélection")
    canvas_result = st_canvas(
        background_image=img,
        height=height,
        width=width,
        drawing_mode="rect",
        stroke_width=2,
        stroke_color="blue",
        update_streamlit=True,
        key="canvas_crop"
    )

    # ✂️ Si un rectangle est dessiné : on rogne l’image selon ce cadre
    if canvas_result.json_data and canvas_result.json_data["objects"]:
        obj = canvas_result.json_data["objects"][0]
        x, y = int(obj["left"]), int(obj["top"])
        w, h = int(obj["width"]), int(obj["height"])
        cropped = img.crop((x, y, x + w, y + h)).convert("RGB")

        st.subheader("🔍 Résultat rogné")
        st.image(cropped, caption="📐 Image rognée automatiquement")

        # 💾 Téléchargement
        buffer = io.BytesIO()
        cropped.save(buffer, format="JPEG", quality=90, optimize=True)
        st.download_button(
            label="📥 Télécharger l'image rognée",
            data=buffer.getvalue(),
            file_name="image_rognee.jpg",
            mime="image/jpeg"
        )
    else:
        st.info("👆 Dessine un rectangle sur l'image pour sélectionner une zone.")
else:
    st.info("📤 Choisis une image à traiter.")
