import logging

logger = logging.getLogger(__name__)

# Basic static dish mapping for Indian dishes -> Ingredients & Macros per serving (~150-200g)
DISH_KNOWLEDGE_BASE = {
    "Aloo Gobi": {
        "ingredients": ["Potatoes (Aloo)", "Cauliflower (Gobi)", "Tomatoes", "Onions", "Turmeric", "Cumin", "Garam Masala", "Mustard Oil"],
        "nutrition": {"calories": 180, "carbohydrates": 24, "protein": 4, "total_fat": 8, "saturated_fat": 1.2, "fiber": 4.5, "sodium": 420}
    },
    "Aloo Matar": {
        "ingredients": ["Potatoes", "Green Peas (Matar)", "Tomatoes", "Onions", "Ginger", "Garlic", "Spices", "Oil"],
        "nutrition": {"calories": 170, "carbohydrates": 26, "protein": 5, "total_fat": 6, "saturated_fat": 1.0, "fiber": 5.0, "sodium": 390}
    },
    "Biryani": {
        "ingredients": ["Basmati Rice", "Spices (Cardamom, Cloves, Cinnamon)", "Ghee/Oil", "Onions", "Yogurt", "Vegetables/Chicken/Mutton"],
        "nutrition": {"calories": 350, "carbohydrates": 45, "protein": 12, "total_fat": 14, "saturated_fat": 4.5, "fiber": 3.0, "sodium": 580}
    },
    "Butter Chicken": {
        "ingredients": ["Chicken", "Butter", "Cream", "Tomatoes", "Garlic", "Ginger", "Garam Masala", "Kasuri Methi"],
        "nutrition": {"calories": 420, "carbohydrates": 10, "protein": 28, "total_fat": 30, "saturated_fat": 14.0, "fiber": 1.5, "sodium": 650}
    },
    "Chapati": {
        "ingredients": ["Whole Wheat Flour (Atta)", "Water", "Salt", "Ghee (optional)"],
        "nutrition": {"calories": 104, "carbohydrates": 15, "protein": 3.1, "total_fat": 3.4, "saturated_fat": 0.7, "fiber": 2.3, "sodium": 110}
    },
    "Chole Bhature": {
        "ingredients": ["Chickpeas (Chole)", "Refined Wheat Flour (Maida)", "Oil", "Onions", "Tomatoes", "Spices", "Baking Soda"],
        "nutrition": {"calories": 450, "carbohydrates": 55, "protein": 12, "total_fat": 20, "saturated_fat": 4.0, "fiber": 7.0, "sodium": 680}
    },
    "Dal Makhani": {
        "ingredients": ["Black Lentils (Urad Dal)", "Kidney Beans (Rajma)", "Butter", "Cream", "Tomatoes", "Garlic", "Spices"],
        "nutrition": {"calories": 310, "carbohydrates": 32, "protein": 11, "total_fat": 16, "saturated_fat": 9.0, "fiber": 6.5, "sodium": 480}
    },
    "Dal Tadka": {
        "ingredients": ["Yellow Lentils (Toor/Moong Dal)", "Ghee", "Cumin Seeds", "Garlic", "Tomatoes", "Turmeric", "Coriander"],
        "nutrition": {"calories": 180, "carbohydrates": 25, "protein": 9, "total_fat": 5, "saturated_fat": 2.2, "fiber": 5.5, "sodium": 400}
    },
    "Dhokla": {
        "ingredients": ["Gram Flour (Besan)", "Fermented Batter", "Mustard Seeds", "Curry Leaves", "Green Chillies", "Lemon Juice", "Sugar"],
        "nutrition": {"calories": 150, "carbohydrates": 22, "protein": 6, "total_fat": 4, "saturated_fat": 0.6, "fiber": 3.0, "sodium": 350}
    },
    "Dosa": {
        "ingredients": ["Fermented Rice & Black Gram Batter", "Oil/Ghee", "Fenugreek Seeds", "Salt"],
        "nutrition": {"calories": 168, "carbohydrates": 29, "protein": 3.9, "total_fat": 3.7, "saturated_fat": 0.9, "fiber": 1.8, "sodium": 220}
    },
    "Gulab Jamun": {
        "ingredients": ["Milk Solids (Khoya/Mawa)", "Refined Wheat Flour (Maida)", "Sugar Syrup", "Cardamom", "Rose Water", "Ghee"],
        "nutrition": {"calories": 175, "carbohydrates": 32, "protein": 2.5, "total_fat": 4.5, "saturated_fat": 2.8, "fiber": 0.2, "sodium": 45}
    },
    "Idli": {
        "ingredients": ["Fermented Rice & Black Gram Batter", "Salt", "Water"],
        "nutrition": {"calories": 58, "carbohydrates": 12, "protein": 2.0, "total_fat": 0.2, "saturated_fat": 0.05, "fiber": 1.0, "sodium": 130}
    },
    "Jalebi": {
        "ingredients": ["Refined Wheat Flour (Maida)", "Sugar Syrup", "Saffron", "Cardamom", "Ghee/Oil"],
        "nutrition": {"calories": 150, "carbohydrates": 30, "protein": 1.0, "total_fat": 3.5, "saturated_fat": 1.8, "fiber": 0.1, "sodium": 25}
    },
    "Kadai Paneer": {
        "ingredients": ["Paneer (Cottage Cheese)", "Capsicum (Bell Pepper)", "Tomatoes", "Onions", "Kadai Masala", "Ghee/Oil"],
        "nutrition": {"calories": 280, "carbohydrates": 12, "protein": 14, "total_fat": 20, "saturated_fat": 11.0, "fiber": 3.0, "sodium": 490}
    },
    "Naan": {
        "ingredients": ["Refined Wheat Flour (Maida)", "Yogurt", "Yeast/Baking Soda", "Butter/Ghee", "Nigella Seeds"],
        "nutrition": {"calories": 260, "carbohydrates": 42, "protein": 7.5, "total_fat": 7.0, "saturated_fat": 3.5, "fiber": 2.0, "sodium": 410}
    },
    "Palak Paneer": {
        "ingredients": ["Spinach (Palak)", "Paneer (Cottage Cheese)", "Garlic", "Ginger", "Onions", "Tomatoes", "Cream", "Spices"],
        "nutrition": {"calories": 240, "carbohydrates": 9, "protein": 12, "total_fat": 18, "saturated_fat": 9.5, "fiber": 3.8, "sodium": 430}
    },
    "Paani Puri": {
        "ingredients": ["Semolina/Wheat Puris", "Flavored Mint-Tamarind Water", "Boiled Potatoes", "Chickpeas", "Chaat Masala"],
        "nutrition": {"calories": 180, "carbohydrates": 30, "protein": 4, "total_fat": 5, "saturated_fat": 1.0, "fiber": 3.2, "sodium": 520}
    },
    "Pakoda": {
        "ingredients": ["Gram Flour (Besan)", "Onions/Potatoes/Spinach", "Spices", "Oil for Deep Frying"],
        "nutrition": {"calories": 220, "carbohydrates": 20, "protein": 5, "total_fat": 14, "saturated_fat": 2.5, "fiber": 3.0, "sodium": 360}
    },
    "Pav Bhaji": {
        "ingredients": ["Mashed Mixed Vegetables (Potatoes, Peas, Cauliflower)", "Butter", "Pav (Bread Rolls)", "Pav Bhaji Masala", "Onions", "Lemon"],
        "nutrition": {"calories": 400, "carbohydrates": 52, "protein": 9, "total_fat": 18, "saturated_fat": 9.0, "fiber": 6.0, "sodium": 620}
    },
    "Poha": {
        "ingredients": ["Flattened Rice (Poha)", "Peanuts", "Onions", "Mustard Seeds", "Curry Leaves", "Turmeric", "Lemon", "Oil"],
        "nutrition": {"calories": 220, "carbohydrates": 36, "protein": 4.5, "total_fat": 7, "saturated_fat": 1.1, "fiber": 2.5, "sodium": 310}
    },
    "Samosa": {
        "ingredients": ["Refined Wheat Flour (Maida)", "Spiced Potato & Pea Filling", "Cumin", "Coriander", "Oil for Deep Frying"],
        "nutrition": {"calories": 260, "carbohydrates": 32, "protein": 4.5, "total_fat": 13, "saturated_fat": 3.0, "fiber": 2.5, "sodium": 380}
    },
    "Vada Pav": {
        "ingredients": ["Deep Fried Potato Patty (Batata Vada)", "Pav (Bread)", "Garlic Chutney", "Green Chillies", "Gram Flour Batter"],
        "nutrition": {"calories": 290, "carbohydrates": 40, "protein": 6.0, "total_fat": 12, "saturated_fat": 2.8, "fiber": 3.5, "sodium": 450}
    }
}

def resolve_food_details(food_name: str) -> dict:
    """
    Look up ingredients and estimated nutritional macros for the identified dish.
    Falls back to intelligent generic estimations if dish isn't in static dictionary.
    """
    # Direct match or partial match search
    clean_name = food_name.strip()
    for dish_key, data in DISH_KNOWLEDGE_BASE.items():
        if dish_key.lower() in clean_name.lower() or clean_name.lower() in dish_key.lower():
            return {
                "dish_name": dish_key,
                "ingredients": data["ingredients"],
                "nutrition": data["nutrition"],
                "source": "knowledge_base"
            }
    
    # Generic fallback if not matched
    logger.info(f"Dish '{food_name}' not found in direct KB, returning generic fallback rules.")
    return {
        "dish_name": clean_name,
        "ingredients": [f"Main ingredients of {clean_name}", "Spices", "Edible Oil", "Salt"],
        "nutrition": {
            "calories": 220,
            "carbohydrates": 30,
            "protein": 6,
            "total_fat": 9,
            "saturated_fat": 2.5,
            "fiber": 3.0,
            "sodium": 400
        },
        "source": "estimated_fallback"
    }
