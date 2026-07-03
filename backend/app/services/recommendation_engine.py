"""
Recommendation Engine Service
Generates personalized food recommendations using recommended_foods.csv.
Matches user conditions to foods to avoid and better alternatives.
"""
from . import dataset_loader as dl


def get_recommendations(
    conditions: list[str],
    ingredients: list[str],
    risk_score: int,
) -> dict:
    """
    Generate personalized recommendations based on:
    - User's health conditions
    - Detected ingredients in the food
    - Overall risk score

    Returns dict with:
        foods_to_avoid, better_alternatives, recommended_foods, serving_advice
    """
    df = dl.recommended_foods
    foods_to_avoid     = []
    better_alternatives = []
    serving_advice_list = []

    if df.empty:
        return _fallback(risk_score)

    # Normalize ingredients for matching
    norm_ingredients = [i.lower().strip() for i in ingredients]

    # Collect condition-specific recommendations
    for condition in conditions + ["General"]:
        cond_lower = condition.lower()
        mask = df["Condition"].str.lower().apply(
            lambda x: cond_lower in x or x in cond_lower
        )
        cond_rows = df[mask]

        for _, row in cond_rows.iterrows():
            food_to_avoid = str(row.get("FoodToAvoid", "")).strip()
            alternative   = str(row.get("BetterAlternative", "")).strip()
            advice        = str(row.get("ServingAdvice", "")).strip()

            # Only include if the food to avoid is in detected ingredients
            # OR always include for the user's conditions
            food_lower = food_to_avoid.lower()
            ingredient_match = any(
                food_lower in ing or ing in food_lower
                for ing in norm_ingredients
            )

            if ingredient_match or condition != "General":
                if food_to_avoid and food_to_avoid not in foods_to_avoid:
                    foods_to_avoid.append(food_to_avoid)
                if alternative and alternative not in better_alternatives:
                    better_alternatives.append(alternative)
                if advice and advice not in serving_advice_list:
                    serving_advice_list.append(advice)

    # Serving advice based on risk level
    if risk_score >= 81:
        serving_advice_list.insert(0, "Avoid this product entirely.")
    elif risk_score >= 61:
        serving_advice_list.insert(0, "Not recommended. Avoid if possible.")
    elif risk_score >= 41:
        serving_advice_list.insert(0, "Consume very rarely — once a month at most.")
    elif risk_score >= 21:
        serving_advice_list.insert(0, "Consume in small portions occasionally.")
    else:
        serving_advice_list.insert(0, "Safe for occasional consumption in moderation.")

    # Recommended healthy foods (generic healthy snacks as baseline)
    recommended = [
        "Fresh fruits (apple, pear, banana)",
        "Roasted makhana (fox nuts)",
        "Unsalted nuts (almonds, walnuts)",
        "Greek yogurt",
        "Fresh vegetables with hummus",
        "Whole grain crackers",
    ]
    # Remove recommended foods that are in foods to avoid
    avoid_lower = [f.lower() for f in foods_to_avoid]
    recommended = [r for r in recommended
                   if not any(a in r.lower() for a in avoid_lower)]

    return {
        "foods_to_avoid":     foods_to_avoid[:8],
        "better_alternatives": better_alternatives[:6],
        "recommended_foods":  recommended[:6],
        "serving_advice":     serving_advice_list[:5],
    }


def _fallback(risk_score: int) -> dict:
    """Default recommendations when CSV is unavailable."""
    advice = "Consume in moderation." if risk_score < 40 else "Avoid this product."
    return {
        "foods_to_avoid":     [],
        "better_alternatives": ["Fresh fruits", "Unsalted nuts", "Whole grains"],
        "recommended_foods":  ["Fresh fruits", "Vegetables", "Whole grains"],
        "serving_advice":     [advice],
    }
