import streamlit as st
from PIL import Image
from streamlit_drawable_canvas import st_canvas
import io

# 📌 Initialisation de l'état de sélection
if "selection_mode" not in st.session_state:
    st.session_state.selection_mode = False

# ⚙️ Configuration de la page
st.set_page_config(page_title="OCR ToolJet", page_icon="📤", layout="centered")
st.title("🎯 Sélection de zone OCR")

# 📥 Upload image
uploaded_file = st.file_uploader("📸 Importer une image", type=["jpg", "jpeg", "png"])
if uploaded_file:
    img = Image.open(uploaded_file)
    rotation = st.selectbox("🔁 Rotation", [0, 90, 180, 270], index=0)
    img = img.rotate(-rotation, expand=True)

    # 🖼️ Compression si image trop large
    max_width = 800
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.Resampling.LANCZOS)

    st.image(img, caption="🖼️ Aperçu de l'image", use_container_width=False)

    # 🎯 Bouton pour déclencher la sélection
    if not st.session_state.selection_mode:
        if st.button("🎯 Je sélectionne une zone à analyser"):
            st.session_state.selection_mode = True

    # 🟧 Zone de sélection active
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

        # 📌 Découpe et affichage de la zone sélectionnée
        if canvas_result.json_data and canvas_result.json_data["objects"]:
            rect = canvas_result.json_data["objects"][0]
            x, y = rect["left"], rect["top"]
            w, h = rect["width"], rect["height"]

            cropped_img = img.crop((x, y, x + w, y + h))
            st.image(cropped_img, caption="📌 Zone sélectionnée", use_container_width=False)

            # 📤 Bouton de traitement
            if st.button("📤 Lancer le traitement OCR sur cette zone"):
                st.success("✨ Traitement lancé sur la zone sélectionnée.")
                # Ici tu peux appeler ta fonction OCR, extraire le texte, etc.
