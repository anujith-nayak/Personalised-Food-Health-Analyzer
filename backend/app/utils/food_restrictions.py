"""
Rule-based food restriction engine.
No AI/ML needed — restrictions are generated from health conditions.
Easy to extend: just add more entries to RULES.
"""
from app.models.user import HealthProfile

# Map condition → restricted food items
RULES: dict[str, list[str]] = {
    "hypertension": [
        "Chips", "Pickles", "Processed Foods",
        "High Sodium Foods", "Canned Soups", "Salted Snacks",
    ],
    "diabetes": [
        "Sugary Drinks", "Chocolates", "Candy",
        "High Sugar Foods", "White Bread", "Sweetened Cereals",
    ],
    "pcos": [
        "Sugary Foods", "Deep Fried Foods",
        "Processed Foods", "Refined Carbohydrates",
    ],
    "pcod": [
        "Sugary Foods", "Junk Food",
        "Processed Foods", "Trans Fats",
    ],
    "kidney_disease": [
        "High Sodium Foods", "High Potassium Foods",
        "Processed Meats", "Dark Colas",
    ],
    "heart_disease": [
        "Fried Foods", "High Fat Foods",
        "Trans Fats", "Excess Red Meat",
    ],
    "thyroid": [
        "Excess Processed Foods",
        "Excess Soy Products",
        "Raw Cruciferous Vegetables in Excess",
    ],
    "obesity": [
        "High Calorie Snacks", "Sugary Beverages",
        "Fast Food", "Deep Fried Foods",
    ],
}


def generate_restrictions(profile: HealthProfile) -> list[str]:
    """Return a sorted, deduplicated list of food restrictions."""
    restrictions: set[str] = set()

    checks = {
        "hypertension": profile.hypertension,
        "diabetes":     profile.diabetes,
        "pcos":         profile.pcos,
        "pcod":         profile.pcod,
        "kidney_disease": profile.kidney_disease,
        "heart_disease":  profile.heart_disease,
        "thyroid":      profile.thyroid,
        "obesity":      profile.obesity,
    }

    for condition, is_active in checks.items():
        if is_active:
            restrictions.update(RULES.get(condition, []))

    return sorted(restrictions)
