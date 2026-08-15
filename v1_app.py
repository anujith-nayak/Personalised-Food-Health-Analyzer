import os
# Force Hugging Face to download the model into the D: drive project folder
os.environ["HF_HOME"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache", "huggingface")

import streamlit as st
from transformers import pipeline
from PIL import Image
import pandas as pd

# Set page configuration for a clean, modern look
st.set_page_config(
    page_title="BiteCheck V1 - Indian Food Identifier",
    page_icon="🍲",
    layout="centered"
)

# App Title & Description
st.title("🍲 BiteCheck V1")
st.subheader("AI-Powered Indian Food Identification")
st.write(
    "Upload an image of an Indian dish, and the selected pre-trained Vision Transformer model will identify it."
)

# Model selection dropdown in the sidebar
st.sidebar.subheader("Model Configuration")
model_option = st.sidebar.selectbox(
    "Select Model Variant:",
    [
        "21-Class Core Model (with Idli & Dosa)",
        "80-Class Sweets & Curries Model"
    ]
)

model_mapping = {
    "80-Class Sweets & Curries Model": "dima806/indian_food_image_detection",
    "21-Class Core Model (with Idli & Dosa)": "Zodex/my-final-food-model-v29"
}

selected_model = model_mapping[model_option]

# Cache the model so it only loads once per model configuration
@st.cache_resource
def load_classifier(model_name):
    return pipeline("image-classification", model=model_name)

# Load model (shows spinner on first load)
try:
    with st.spinner("Loading AI Model (this will download model weights on first select)..."):
        classifier = load_classifier(selected_model)
    st.success(f"Active Model: {selected_model}")
except Exception as e:
    st.error(f"Error loading the model: {e}")
    st.stop()


# File Uploader
uploaded_file = st.file_uploader(
    "Choose an image of a dish...", 
    type=["jpg", "jpeg", "png"]
)

if uploaded_file is not None:
    # Load and display the image
    image = Image.open(uploaded_file)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Uploaded Image")
        st.image(image, use_container_width=True)
        
    with col2:
        st.subheader("Identification Results")
        with st.spinner("Identifying food item..."):
            try:
                # Run the image classifier
                predictions = classifier(image)
                
                # Format predictions into a clean dataframe
                results = []
                for pred in predictions:
                    # Clean up the label name (e.g. "aloo_gobi" -> "Aloo Gobi")
                    clean_label = pred["label"].replace("_", " ").title()
                    results.append({
                        "Dish": clean_label,
                        "Confidence": pred["score"]
                    })
                
                df = pd.DataFrame(results)
                
                # Display the top prediction as a highlighted callout
                top_dish = df.iloc[0]["Dish"]
                top_conf = df.iloc[0]["Confidence"]
                st.metric(label="Top Prediction", value=top_dish, delta=f"{top_conf:.1%}")
                
                # Display bar chart of confidence scores
                st.write("**Top Match Confidence Breakdown:**")
                chart_df = df.set_index("Dish")
                st.bar_chart(chart_df["Confidence"])
                
                # Display exact table
                st.dataframe(
                    df.style.format({"Confidence": "{:.2%}"}),
                    hide_index=True,
                    use_container_width=True
                )
                
            except Exception as e:
                st.error(f"Failed to process image: {e}")
else:
    st.info("Please upload an image file (JPG, JPEG, PNG) to begin.")

# Footer info about the classes depending on selected model
if model_option == "21-Class Core Model (with Idli & Dosa)":
    with st.expander("Show all 21 supported classes"):
        st.write(
            "Aloo Matar, Besan Cheela, Biryani, Chapathi, Chole Bature, Dahl (Dal), Dhokla, Dosa, Gulab Jamun, "
            "Idli, Jalebi, Kadai Paneer, Naan, Paani Puri, Pakoda, Pav Bhaji, Poha, Rolls, Samosa, Vada Pav, "
            "and a 'Not Food' filter class."
        )
else:
    with st.expander("Show all 80 supported dishes"):
        st.write(
            "Adhirasam, Aloo Gobi, Aloo Matar, Aloo Methi, Aloo Shimla Mirch, Aloo Tikki, Anarsa, Ariselu, "
            "Bandar Laddu, Basundi, Bhatura, Bhindi Masala, Biryani, Boondi, Butter Chicken, Chak Hao Kheer, "
            "Cham Cham, Chana Masala, Chapati, Chhena Kheeri, Chicken Razala, Chicken Tikka, Chicken Tikka Masala, "
            "Chikki, Daal Baati Churma, Daal Puri, Dal Makhani, Dal Tadka, Dharwad Pedha, Doodhpak, Double Ka Meetha, "
            "Dum Aloo, Gajar Ka Halwa, Gavvalu, Ghevar, Gulab Jamun, Imarti, Jalebi, Kachori, Kadai Paneer, "
            "Kadhi Pakoda, Kajjikaya, Kakinada Khaja, Kalakand, Karela Bharta, Kofta, Kuzhi Paniyaram, Lassi, "
            "Ledikeni, Litti Chokha, Lyangcha, Maach Jhol, Makki Di Roti Sarson Da Saag, Malapua, Misi Roti, "
            "Misti Doi, Modak, Mysore Pak, Naan, Navrattan Korma, Palak Paneer, Paneer Butter Masala, Phirni, "
            "Pithe, Poha, Poornalu, Pootharekulu, Qubani Ka Meetha, Rabri, Ras Malai, Rasgulla, Sandesh, "
            "Shankarpali, Sheer Korma, Sheera, Shrikhand, Sohan Halwa, Sohan Papdi, Sutar Feni, Unni Appam."
        )
