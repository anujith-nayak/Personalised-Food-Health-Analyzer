"""
Recommendation Engine Service
==============================
Generates personalized, nutrient-aware food recommendations.

Improvements over the previous version:
  1. Serving advice is calculated dynamically from the health score.
  2. Better alternatives are selected based on the actual violated nutrients,
     not just the user's conditions.  High-sodium violations → low-sodium
     alternatives; high-sugar → low-GI foods; etc.
  3. Duplicate messages are removed across all output fields.
  4. Recommended foods are filtered to exclude anything in foods_to_avoid.
"""
from __future__ import annotations
from . import dataset_loader as dl


# ── Score-based serving frequency (Req 2) ────────────────────────────────────
def serving_advice_from_score(score: int) -> str:
    """
    Return a single, plain-English serving frequency sentence
    derived from the health score.

      90-100 → Safe to consume daily.
      80-89  → 2–3 times per week.
      60-79  → Once per week at most.
      40-59  → Twice per month at most.
      < 40   → Avoid this product.
    """
    if score >= 90:
        return "Safe to consume daily in normal portions."
    if score >= 80:
        return "Suitable 2–3 times per week. Watch portion size."
    if score >= 60:
        return "Consume at most once per week. Prefer healthier options on other days."
    if score >= 40:
        return "Consume at most twice per month. Choose healthier alternatives regularly."
    return "Avoid this product. It is not suitable for your health conditions."


# ── Nutrient-specific alternative lookup (Req 3) ─────────────────────────────
#
# Maps a violated nutrient key to a curated list of better alternatives.
# These are used when the CSV doesn't have a matching row for the condition.
_NUTRIENT_ALTERNATIVES: dict[str, list[str]] = {
    "sodium": [
        "Unsalted nuts or seeds",
        "Fresh or frozen vegetables (no added salt)",
        "Home-cooked dal or lentil soup",
        "Fresh fruit",
        "Plain yogurt",
    ],
    "sugar": [
        "Fresh fruits (apple, pear, guava)",
        "Unsweetened Greek yogurt",
        "Dark chocolate (≥70% cocoa)",
        "Oat-based snacks with no added sugar",
        "Roasted makhana (fox nuts)",
    ],
    "added_sugar": [
        "Fresh fruits (apple, pear, guava)",
        "Unsweetened herbal tea",
        "Plain water with lemon",
        "Oat biscuits or rice cakes",
    ],
    "saturated_fat": [
        "Grilled chicken or fish",
        "Legumes and lentils (dal)",
        "Unsalted almonds or walnuts",
        "Tofu or paneer (low-fat)",
        "Oats or whole-grain bread",
    ],
    "trans_fat": [
        "Home-baked snacks (no margarine)",
        "Avocado or olive oil-based spreads",
        "Fresh fruit",
        "Unsalted roasted nuts",
    ],
    "total_fat": [
        "Steamed or baked snacks",
        "Fresh salad with lemon dressing",
        "Boiled chickpeas or sprouts",
        "Plain popcorn (air-popped)",
    ],
    "calories": [
        "Fresh fruit salad",
        "Plain vegetable soup",
        "Cucumber and carrot sticks with hummus",
        "Buttermilk (chaas)",
        "Plain roasted makhana",
    ],
    "carbohydrates": [
        "Whole-grain bread or brown rice",
        "Legumes and pulses (lower GI)",
        "Non-starchy vegetables",
        "Nuts and seeds",
    ],
    "cholesterol": [
        "Egg whites instead of whole eggs",
        "Oat-based porridge",
        "Plant-based protein sources",
        "Fish (omega-3 rich)",
    ],
    "potassium": [
        "Low-potassium fruits: apple, grapes, berries",
        "White bread instead of whole grain",
        "Cooked and drained vegetables",
    ],
    "protein": [
        "Lean chicken breast",
        "Egg whites",
        "Low-fat dairy",
        "Tofu",
    ],
}

# Maps condition names to nutrient keys they are most sensitive to
_CONDITION_KEY_NUTRIENTS: dict[str, list[str]] = {
    "hypertension":    ["sodium", "saturated_fat", "trans_fat"],
    "diabetes":        ["sugar", "added_sugar", "carbohydrates", "trans_fat"],
    "heart disease":   ["saturated_fat", "trans_fat", "cholesterol", "sodium"],
    "kidney disease":  ["sodium", "potassium", "protein"],
    "obesity":         ["calories", "total_fat", "sugar", "trans_fat"],
    "pcos":            ["sugar", "added_sugar", "trans_fat", "saturated_fat"],
    "pcod":            ["sugar", "added_sugar", "trans_fat", "saturated_fat"],
    "hypothyroidism":  ["saturated_fat", "sugar", "calories"],
    "hyperthyroidism": ["calories", "sodium"],
    "high cholesterol":["saturated_fat", "trans_fat", "cholesterol"],
}


def get_recommendations(
    conditions: list[str],
    ingredients: list[str],
    risk_score: int,                # 100 - health_score  (higher = riskier)
    violations: list[dict] | None = None,
    health_score: int = 0,
) -> dict:
    """
    Generate personalized recommendations.

    Parameters
    ----------
    conditions    : list of user health conditions
    ingredients   : list of detected food ingredients
    risk_score    : 100 - health_score (kept for backward compat, not used for serving advice)
    violations    : list of violation dicts from risk_engine (optional but preferred)
    health_score  : the actual health score (0-100) used for serving advice
    """
    df = dl.recommended_foods
    foods_to_avoid:      list[str] = []
    better_alternatives: list[str] = []
    csv_serving_advice:  list[str] = []

    norm_ingredients = [i.lower().strip() for i in ingredients]

    # ── Identify violated nutrients from risk_engine violations ──────────────
    violated_nutrients: list[str] = []
    if violations:
        seen_viol = set()
        for v in violations:
            n = v.get("nutrient", "").lower().replace(" ", "_")
            if n and n not in seen_viol:
                violated_nutrients.append(n)
                seen_viol.add(n)

    # Also add nutrients implied by condition if no violations passed
    if not violated_nutrients:
        for cond in conditions:
            for n in _CONDITION_KEY_NUTRIENTS.get(cond.lower(), []):
                if n not in violated_nutrients:
                    violated_nutrients.append(n)

    # ── Pull rows from recommended_foods.csv ─────────────────────────────────
    if not df.empty:
        for condition in conditions + ["General"]:
            cond_lower = condition.lower()
            mask = df["Condition"].str.lower().apply(
                lambda x: cond_lower in x or x in cond_lower
            )
            for _, row in df[mask].iterrows():
                food_to_avoid = str(row.get("FoodToAvoid", "")).strip()
                alternative   = str(row.get("BetterAlternative", "")).strip()
                advice        = str(row.get("ServingAdvice", "")).strip()

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
                    if advice and advice not in csv_serving_advice:
                        csv_serving_advice.append(advice)

    # ── Nutrient-driven alternatives (Req 3) ─────────────────────────────────
    # Add alternatives specific to actually violated nutrients,
    # placing them at the front of the list so they appear first.
    nutrient_alts: list[str] = []
    for nutrient_key in violated_nutrients:
        for alt in _NUTRIENT_ALTERNATIVES.get(nutrient_key, []):
            if alt not in better_alternatives and alt not in nutrient_alts:
                nutrient_alts.append(alt)

    # Merge: nutrient-specific first, then CSV-sourced
    merged_alternatives = list(dict.fromkeys(nutrient_alts + better_alternatives))

    # ── Serving advice (Req 2) — score-based, single authoritative sentence ──
    serving_sentence = serving_advice_from_score(health_score)

    # ── Recommended healthy foods ─────────────────────────────────────────────
    baseline_recommended = [
        "Fresh fruits (apple, pear, guava)",
        "Roasted makhana (fox nuts) — unsalted",
        "Unsalted almonds or walnuts",
        "Plain Greek yogurt",
        "Fresh vegetables with hummus",
        "Whole-grain crackers or oat biscuits",
        "Buttermilk (chaas) — low-fat",
        "Boiled chickpeas or sprouts",
    ]
    avoid_lower = {f.lower() for f in foods_to_avoid}
    recommended = [
        r for r in baseline_recommended
        if not any(a in r.lower() for a in avoid_lower)
    ]

    return {
        "foods_to_avoid":      _dedup(foods_to_avoid)[:8],
        "better_alternatives": _dedup(merged_alternatives)[:8],
        "recommended_foods":   recommended[:6],
        "serving_advice":      [serving_sentence] + _dedup(csv_serving_advice)[:3],
    }


def _dedup(lst: list[str]) -> list[str]:
    """Return list with duplicates removed, order preserved."""
    seen: set[str] = set()
    out:  list[str] = []
    for item in lst:
        key = item.lower().strip()
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def _fallback(risk_score: int) -> dict:
    """Default recommendations when CSV is unavailable."""
    score = max(0, 100 - risk_score)
    return {
        "foods_to_avoid":      [],
        "better_alternatives": ["Fresh fruits", "Unsalted nuts", "Whole grains"],
        "recommended_foods":   ["Fresh fruits", "Vegetables", "Whole grains"],
        "serving_advice":      [serving_advice_from_score(score)],
    }
