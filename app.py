import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io

st.set_page_config(page_title="✂️ Rognage par cadre", layout="centered")
st.title("📸 Rognage d'image avec compression & optimisation")

# 📤 Téléversement
uploaded_file = st.file_uploader("Téléverse une image (max 200 MB)", type=["jpg", "png", "jpeg"])
if uploaded_file:
    max_size_bytes = 200 * 1024 * 1024  # 200 MB
    quality = 90

    # 🧩 Image originale
    original_img = Image.open(uploaded_file).convert("RGB")
    original_img = original_img.rotate(-90, expand=True)

    # 🧮 Crop pour version réduite
    w, h = original_img.size
    left = int(w * 0.05)
    right = int(w * 0.85)
    top = int(h * 0.3)
    bottom = int(h * 0.7)
    img = original_img.crop((left, top, right, bottom))

    # 🖼️ Affichage image réduite
    st.image(img, caption="🖼️ Image affichée avec rotation", use_container_width=True)

    # 📏 Taille canvas choisie
    canvas_width = 300
    canvas_height = int(canvas_width * img.height / img.width)  # conserve ratio

    st.subheader("🟦 Dessine un cadre de sélection")
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
        # 🎯 Mise à l’échelle
        scale_x = img.width / canvas_width
        scale_y = img.height / canvas_height

        # 🧮 Coordonnées dans l'image affichée
        x = int(obj["left"] * scale_x)
        y = int(obj["top"] * scale_y)
        w_sel = int(obj["width"] * scale_x)
        h_sel = int(obj["height"] * scale_y)

        # 🔁 Ajuster pour image d'origine
        crop_left = left + x
        crop_top = top + y
        crop_right = crop_left + w_sel
        crop_bottom = crop_top + h_sel

        cropped = original_img.crop((crop_left, crop_top, crop_right, crop_bottom)).convert("RGB")

        st.subheader("🔍 Résultat rogné")
        st.image(cropped, caption="📐 Image rognée et compressée")

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
