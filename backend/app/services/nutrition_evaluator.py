"""
Nutrition Evaluator Service
============================
Step 2 of the analysis pipeline:
  Compare every extracted nutrient against healthy reference ranges.
  Returns per-nutrient status: Good / Moderate / High / Very High / Low / Not Available

Reference ranges are evidence-based daily limits (per serving context):
  We compare against standard single-serving benchmarks, then scale by daily limits.
"""

# ── Reference benchmarks per SERVING (not per day) ───────────────────────────
# Source: FDA nutrition label guidelines + WHO/AHA recommendations
NUTRIENT_BENCHMARKS = {
    # nutrient_key: (low_threshold, high_threshold, very_high_threshold, unit, higher_is_better)
    "calories":        (None,  200,  400,  "kcal", False),
    "total_fat":       (None,   5,   20,   "g",    False),
    "saturated_fat":   (None,   2,    5,   "g",    False),
    "trans_fat":       (None,   0,    1,   "g",    False),   # 0 = any is high
    "cholesterol":     (None,  20,   60,   "mg",   False),
    "sodium":          (None, 140,  575,   "mg",   False),
    "carbohydrates":   (None,  30,   60,   "g",    False),
    "sugar":           (None,   5,   12,   "g",    False),
    "fiber":           (2,    None, None,  "g",    True),    # higher = better
    "protein":         (None, None, None,  "g",    True),    # higher = better (no upper limit)
    "potassium":       (None, None, None,  "mg",   True),
    "calcium":         (None, None, None,  "mg",   True),
    "iron":            (None, None, None,  "mg",   True),
}


def evaluate_nutrient(key: str, value: float | None) -> dict:
    """
    Return evaluation dict for one nutrient:
      {nutrient, value, unit, status, status_color, note}
    """
    if value is None:
        return {
            "nutrient":      _label(key),
            "key":           key,
            "value":         None,
            "unit":          NUTRIENT_BENCHMARKS.get(key, (None, None, None, "", False))[3],
            "status":        "Not Available",
            "status_color":  "gray",
            "note":          "Not found on label",
        }

    bench = NUTRIENT_BENCHMARKS.get(key)
    if not bench:
        return {
            "nutrient":      _label(key),
            "key":           key,
            "value":         value,
            "unit":          "",
            "status":        "Extracted",
            "status_color":  "blue",
            "note":          "",
        }

    low_thresh, high_thresh, very_high_thresh, unit, higher_is_better = bench

    # Special case: trans fat — any amount > 0 is flagged
    if key == "trans_fat":
        if value == 0:
            status, color, note = "Good",      "green",  "No trans fat detected"
        elif value <= 0.5:
            status, color, note = "Moderate",  "yellow", "Trace amounts of trans fat"
        elif value <= 2:
            status, color, note = "High",      "orange", "Contains trans fat"
        else:
            status, color, note = "Very High", "red",    "High trans fat content"
        return {"nutrient": _label(key), "key": key, "value": value, "unit": unit,
                "status": status, "status_color": color, "note": note}

    if higher_is_better:
        # Nutrients where more is better (fiber, protein, etc.)
        if low_thresh and value < low_thresh:
            status, color = "Low", "orange"
            note = f"Less than recommended {low_thresh}{unit}"
        else:
            status, color = "Good", "green"
            note = "Adequate amount"
    else:
        # Nutrients where less is better
        if very_high_thresh and value > very_high_thresh:
            status, color = "Very High", "red"
            note = f"Significantly exceeds {very_high_thresh}{unit} per serving"
        elif high_thresh and value > high_thresh:
            status, color = "High", "orange"
            note = f"Exceeds {high_thresh}{unit} per serving"
        elif high_thresh and value > high_thresh * 0.6:
            status, color = "Moderate", "yellow"
            note = f"Approaching limit of {high_thresh}{unit}"
        else:
            status, color = "Good", "green"
            note = "Within healthy range"

    return {
        "nutrient":      _label(key),
        "key":           key,
        "value":         value,
        "unit":          unit,
        "status":        status,
        "status_color":  color,
        "note":          note,
    }


def evaluate_all_nutrients(nutrition: dict) -> list[dict]:
    """Evaluate every nutrient in extraction order."""
    ordered_keys = [
        "calories", "total_fat", "saturated_fat", "trans_fat", "cholesterol",
        "sodium", "carbohydrates", "sugar", "fiber", "protein",
        "potassium", "calcium", "iron",
    ]
    results = []
    for key in ordered_keys:
        val = nutrition.get(key)
        results.append(evaluate_nutrient(key, val))

    # Any extra keys not in the standard list
    for key, val in nutrition.items():
        if key not in ordered_keys and val is not None:
            results.append(evaluate_nutrient(key, val))

    return results


def _label(key: str) -> str:
    labels = {
        "calories":       "Calories",
        "total_fat":      "Total Fat",
        "saturated_fat":  "Saturated Fat",
        "trans_fat":      "Trans Fat",
        "cholesterol":    "Cholesterol",
        "sodium":         "Sodium",
        "carbohydrates":  "Total Carbohydrates",
        "sugar":          "Total Sugar",
        "fiber":          "Dietary Fiber",
        "protein":        "Protein",
        "potassium":      "Potassium",
        "calcium":        "Calcium",
        "iron":           "Iron",
        "serving_size":   "Serving Size",
    }
    return labels.get(key, key.replace("_", " ").title())
