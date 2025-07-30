import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io

st.set_page_config(page_title="✂️ Rognage par cadre", layout="centered")
st.title("📸 Rognage d'image avec compression & optimisation")

# 📤 Téléversement
uploaded_file = st.file_uploader("Téléverse une image (max 200 MB)", type=["jpg", "png", "jpeg"])
if uploaded_file:
    # 🧮 Limite strictement 200 MB en octets
    max_size_bytes = 200 * 1024 * 1024  # 200 MB
    quality = 90

    # 📥 Ouverture image
    img = Image.open(uploaded_file).convert("RGB")

    # 🖼️ Réduction résolution avant tout affichage
    max_canvas_size = (2000, 2000)
    img.thumbnail(max_canvas_size, Image.Resampling.LANCZOS)

    # 🗜️ Compression dynamique
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=quality, optimize=True)
    size = buffer.tell()

    while size > max_size_bytes and quality > 10:
        buffer = io.BytesIO()
        quality -= 5
        img.save(buffer, format="JPEG", quality=quality, optimize=True)
        size = buffer.tell()

    compressed_img = Image.open(buffer)
    width, height = compressed_img.size

    # 🟦 Canvas avec mode rectangle
    st.subheader("🟦 Dessine un cadre de sélection")
    canvas_result = st_canvas(
        background_image=compressed_img,
        height=height,
        width=width,
        drawing_mode="rect",
        stroke_width=2,
        stroke_color="blue",
        update_streamlit=True,
        key="canvas_crop"
    )

    # ✂️ Rognage si sélection existante
    if canvas_result.json_data and canvas_result.json_data["objects"]:
        obj = canvas_result.json_data["objects"][0]
        x, y = int(obj["left"]), int(obj["top"])
        w, h = int(obj["width"]), int(obj["height"])
        cropped = compressed_img.crop((x, y, x + w, y + h)).convert("RGB")

        st.subheader("🔍 Résultat rogné")
        st.image(cropped, caption="📐 Image rognée et compressée")

        # 📥 Téléchargement final
        final_buffer = io.BytesIO()
        cropped.save(final_buffer, format="JPEG", quality=quality, optimize=True)
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
