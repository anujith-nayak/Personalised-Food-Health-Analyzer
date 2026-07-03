"""
Disease-Specific Analyzer
==========================
Step 3 of the pipeline:
  For each of the user's health conditions, evaluate ONLY the relevant nutrients.
  Returns a structured impact report per condition with clear explanations.
"""

# ── Which nutrients matter for each condition ─────────────────────────────────
CONDITION_NUTRIENTS = {
    "Hypertension": {
        "sodium":        ("critical",  140,  "mg", "Sodium directly raises blood pressure"),
        "saturated_fat": ("important",   2,  "g",  "Saturated fat contributes to arterial stiffness"),
        "trans_fat":     ("critical",    0,  "g",  "Trans fat worsens cardiovascular health"),
    },
    "Diabetes": {
        "sugar":         ("critical",    5,  "g",  "Added sugar rapidly elevates blood glucose"),
        "carbohydrates": ("important",  30,  "g",  "High carbs spike blood glucose levels"),
        "fiber":         ("beneficial",  3,  "g",  "Fiber slows glucose absorption — more is better"),
        "saturated_fat": ("important",   2,  "g",  "Saturated fat worsens insulin resistance"),
        "trans_fat":     ("critical",    0,  "g",  "Trans fat severely impairs glucose metabolism"),
    },
    "Heart Disease": {
        "saturated_fat": ("critical",   2,  "g",  "Saturated fat raises LDL cholesterol"),
        "trans_fat":     ("critical",   0,  "g",  "Trans fat is the most dangerous dietary fat for the heart"),
        "cholesterol":   ("important",  20, "mg", "Dietary cholesterol contributes to plaque formation"),
        "sodium":        ("important", 140, "mg", "Sodium increases fluid load on the heart"),
    },
    "Kidney Disease": {
        "sodium":        ("critical",  140, "mg", "Kidneys struggle to excrete excess sodium in CKD"),
        "protein":       ("important",  8,  "g",  "Excess protein overloads failing kidneys"),
        "potassium":     ("critical", 200, "mg", "Failed kidneys cannot excrete excess potassium"),
        "phosphorus":    ("important", 70, "mg", "Phosphorus buildup causes bone disease in CKD"),
    },
    "Obesity": {
        "calories":      ("critical",  200, "kcal", "Caloric surplus directly causes weight gain"),
        "sugar":         ("important",   5, "g",    "Empty sugar calories promote fat storage"),
        "total_fat":     ("important",   5, "g",    "High fat increases caloric density"),
        "trans_fat":     ("critical",    0, "g",    "Trans fat promotes abdominal fat accumulation"),
    },
    "PCOS": {
        "sugar":         ("critical",    5, "g",  "Sugar worsens insulin resistance in PCOS"),
        "carbohydrates": ("important",  30, "g",  "Refined carbs spike insulin worsening PCOS"),
        "trans_fat":     ("critical",    0, "g",  "Trans fat disrupts hormonal balance"),
        "fiber":         ("beneficial",  3, "g",  "Fiber improves insulin sensitivity"),
    },
    "Hypothyroidism": {
        "sodium":        ("moderate",  200, "mg", "Moderate sodium restriction supports thyroid health"),
        "sugar":         ("important",   5, "g",  "Sugar worsens metabolic dysfunction in hypothyroidism"),
    },
    "Hyperthyroidism": {
        "sodium":        ("moderate",  200, "mg", "Sodium management for hyperthyroid-related hypertension"),
    },
}


def analyze_for_condition(condition: str, nutrition: dict) -> dict:
    """
    Evaluate food impact for ONE health condition.
    Returns:
        {condition, overall_impact, concerns, positives, summary}
    """
    rules = CONDITION_NUTRIENTS.get(condition, {})
    if not rules:
        return {
            "condition":       condition,
            "overall_impact":  "No specific rules available",
            "impact_color":    "gray",
            "concerns":        [],
            "positives":       [],
            "summary":         f"No specific dietary rules found for {condition}.",
        }

    concerns   = []
    positives  = []
    risk_score = 0

    for nutrient_key, (importance, threshold, unit, reason) in rules.items():
        value = nutrition.get(nutrient_key)

        if value is None:
            continue

        is_beneficial = importance == "beneficial"

        if is_beneficial:
            # More is better
            if value >= threshold:
                positives.append(f"{_lbl(nutrient_key)} {value}{unit} — {reason}")
            else:
                concerns.append({
                    "nutrient":    _lbl(nutrient_key),
                    "value":       f"{value}{unit}",
                    "threshold":   f"≥{threshold}{unit} recommended",
                    "importance":  importance,
                    "message":     f"Low {_lbl(nutrient_key)}: {reason}",
                })
                risk_score += 1
        else:
            # Less is better
            if nutrient_key == "trans_fat" and value > 0:
                concerns.append({
                    "nutrient":    _lbl(nutrient_key),
                    "value":       f"{value}{unit}",
                    "threshold":   "0g (strictly avoid)",
                    "importance":  "critical",
                    "message":     f"Contains Trans Fat: {reason}",
                })
                risk_score += 3 if importance == "critical" else 2
            elif value > threshold:
                pct = int((value / threshold) * 100) if threshold > 0 else 999
                severity = (
                    "Very high" if pct > 200 else
                    "High"      if pct > 130 else
                    "Moderate"
                )
                weight = 3 if importance == "critical" else 2 if importance == "important" else 1
                concerns.append({
                    "nutrient":    _lbl(nutrient_key),
                    "value":       f"{value}{unit}",
                    "threshold":   f"≤{threshold}{unit} per serving",
                    "importance":  importance,
                    "message":     f"{severity} {_lbl(nutrient_key)} ({pct}% of limit): {reason}",
                })
                risk_score += weight
            else:
                positives.append(f"{_lbl(nutrient_key)} {value}{unit} — within safe range")

    # Overall impact
    if risk_score == 0:
        overall, color = "Low Risk", "green"
    elif risk_score <= 2:
        overall, color = "Moderate Risk", "yellow"
    elif risk_score <= 4:
        overall, color = "High Risk", "orange"
    else:
        overall, color = "Very High Risk", "red"

    # Summary sentence
    if concerns:
        names = [c["nutrient"] for c in concerns[:3]]
        summary = f"This food raises concerns for {condition} due to: {', '.join(names)}."
    else:
        summary = f"This food appears acceptable for {condition} based on extracted values."

    return {
        "condition":      condition,
        "overall_impact": overall,
        "impact_color":   color,
        "concerns":       concerns,
        "positives":      positives,
        "summary":        summary,
    }


def analyze_all_conditions(conditions: list[str], nutrition: dict) -> list[dict]:
    """Run disease analysis for all user conditions."""
    # Remove implied conditions from display
    display = [c for c in conditions if c in CONDITION_NUTRIENTS]
    return [analyze_for_condition(c, nutrition) for c in display]


def _lbl(key: str) -> str:
    m = {
        "calories": "Calories", "total_fat": "Total Fat",
        "saturated_fat": "Saturated Fat", "trans_fat": "Trans Fat",
        "cholesterol": "Cholesterol", "sodium": "Sodium",
        "carbohydrates": "Carbohydrates", "sugar": "Sugar",
        "fiber": "Dietary Fiber", "protein": "Protein",
        "potassium": "Potassium", "phosphorus": "Phosphorus",
    }
    return m.get(key, key.replace("_", " ").title())
