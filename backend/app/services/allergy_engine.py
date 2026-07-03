"""
Allergy Engine Service
Compares detected ingredients against allergy_rules.csv.
Generates allergy alerts based on user's stored health conditions.
"""
from . import dataset_loader as dl


# Common ingredient name aliases for fuzzy matching
ALLERGEN_KEYWORDS = {
    "milk": ["milk", "dairy", "lactose", "casein", "whey", "milk solids", "milk powder",
             "butter", "cream", "cheese", "curd", "ghee"],
    "gluten": ["wheat", "gluten", "barley", "rye", "semolina", "maida", "atta",
               "wheat flour", "refined flour"],
    "peanut": ["peanut", "groundnut", "arachis"],
    "tree nuts": ["almond", "cashew", "walnut", "pistachio", "hazelnut", "pecan", "nut"],
    "egg": ["egg", "albumin", "lysozyme", "lecithin"],
    "soy": ["soy", "soya", "tofu", "edamame", "soy protein"],
    "fish": ["fish", "tuna", "salmon", "cod", "anchovy", "fish sauce"],
    "shellfish": ["shrimp", "prawn", "crab", "lobster", "shellfish"],
    "sesame": ["sesame", "tahini", "til", "sesame oil"],
    "corn": ["corn", "maize", "corn starch", "corn syrup", "corn flour"],
    "sulphites": ["sulphite", "sulfite", "e220", "e221", "e222", "e223", "so2"],
    "artificial colors": ["e102", "e110", "e120", "tartrazine", "sunset yellow",
                          "artificial colour", "artificial color", "food color"],
    "artificial preservatives": ["sodium benzoate", "e211", "bha", "bht", "potassium sorbate"],
    "artificial sweeteners": ["aspartame", "saccharin", "sucralose", "stevia", "acesulfame"],
    "histamine": ["vinegar", "fermented", "aged cheese", "soy sauce", "fish sauce"],
    "fructose": ["fructose", "hfcs", "high fructose corn syrup", "fruit sugar"],
}

# Health conditions that may indicate sensitivities
CONDITION_TO_ALLERGEN = {
    "lactose": "milk",
    "milk_allergy": "milk",
    "gluten": "gluten",
    "celiac": "gluten",
    "peanut_allergy": "peanut",
    "nut_allergy": "tree nuts",
    "egg_allergy": "egg",
    "soy_allergy": "soy",
}


def _normalize(text: str) -> str:
    return str(text).lower().strip()


def check_allergies(
    ingredients: list[str],
    user_conditions: list[str],
) -> list[dict]:
    """
    Check detected ingredients against potential allergens.

    Args:
        ingredients: list of ingredient names from OCR
        user_conditions: list of user health conditions from their profile

    Returns:
        list of allergy alert dicts with: allergen, matched_ingredient,
        severity, recommendation, symptoms
    """
    alerts = []
    seen_allergens = set()

    # Normalize ingredients for matching
    norm_ingredients = [_normalize(i) for i in ingredients]

    # Check each allergen group
    for allergen, keywords in ALLERGEN_KEYWORDS.items():
        matched_ingredient = None
        for keyword in keywords:
            for ingredient in norm_ingredients:
                if keyword in ingredient or ingredient in keyword:
                    matched_ingredient = ingredient
                    break
            if matched_ingredient:
                break

        if matched_ingredient and allergen not in seen_allergens:
            # Look up severity from allergy rules CSV
            df = dl.allergy_rules
            if df.empty:
                severity = "Moderate"
                recommendation = "Avoid"
                symptoms = "Possible allergic reaction"
            else:
                # Find matching row
                mask = df["Allergen"].str.lower().str.contains(allergen.lower(), na=False)
                matches = df[mask]
                if not matches.empty:
                    row = matches.iloc[0]
                    severity = row.get("Severity", "Moderate")
                    recommendation = row.get("Recommendation", "Avoid")
                    symptoms = row.get("Symptoms", "Allergic reaction")
                    risk_weight = int(row.get("RiskWeight", 5))
                else:
                    severity = "Moderate"
                    recommendation = "Avoid"
                    symptoms = "Possible allergic reaction"
                    risk_weight = 5

            alerts.append({
                "allergen":           allergen.title(),
                "matched_ingredient": matched_ingredient.title(),
                "severity":           severity,
                "recommendation":     recommendation,
                "symptoms":           symptoms,
                "risk_weight":        risk_weight,
            })
            seen_allergens.add(allergen)

    # Sort by severity (most severe first)
    severity_order = {"Severe": 0, "Moderate": 1, "Mild": 2}
    alerts.sort(key=lambda x: severity_order.get(x.get("severity", "Mild"), 3))

    return alerts


def get_allergy_risk_score(alerts: list[dict]) -> int:
    """Calculate total allergy-based risk contribution (0-30 extra points)."""
    if not alerts:
        return 0
    total = sum(a.get("risk_weight", 5) for a in alerts)
    return min(int(total * 2), 30)  # cap at 30 bonus points
