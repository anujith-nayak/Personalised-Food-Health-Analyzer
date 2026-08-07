"""
nutrient_format.py — Shared nutrient formatting utility.

BUG FIXES
---------
Bug 1: Incorrect units ("percent" displayed instead of g / mg / kcal).
  Root cause: health_r.csv stores units like "percent", "g/day", "kcal/day".
  The code stripped "/day" but left "percent" as-is.
  Fix: canonical_unit() maps every known nutrient to its correct display unit,
  completely ignoring the raw CSV unit string for presentation.

Bug 2: Unrealistic percentages (e.g. 914%).
  Root cause: rows with unit="percent" have threshold_max values like 30 (meaning
  "30 percent of calories"), not 30g. Dividing a mg value by a % threshold
  produces nonsense ratios.
  Fix: skip_percentage_threshold() detects these rows so callers can skip
  percent-based thresholds when displaying absolute nutrient quantities.

Bug 5: Duplicated formatting logic across risk_engine, disease_analyzer,
  recommendation_engine, and packaged_food.
  Fix: all formatting goes through format_nutrient() and fmt_val() in this module.
"""

from __future__ import annotations

# ── Canonical display units per nutrient key ─────────────────────────────────
# These are the correct physical units regardless of what the CSV stores.
_CANONICAL_UNITS: dict[str, str] = {
    # Energy
    "calories":       "kcal",
    "energy":         "kcal",
    # Macros — grams
    "total_fat":      "g",
    "fat":            "g",
    "saturated_fat":  "g",
    "trans_fat":      "g",
    "carbohydrates":  "g",
    "carbs":          "g",
    "total_carbs":    "g",
    "fiber":          "g",
    "dietary_fiber":  "g",
    "sugar":          "g",
    "added_sugar":    "g",
    "protein":        "g",
    # Minerals — milligrams
    "sodium":         "mg",
    "salt":           "mg",
    "potassium":      "mg",
    "calcium":        "mg",
    "iron":           "mg",
    "cholesterol":    "mg",
    "phosphorus":     "mg",
    "magnesium":      "mg",
    "zinc":           "mg",
    # Micrograms
    "chromium":       "mcg",
    "vitamin_b12":    "mcg",
    "iodine":         "mcg",
    "selenium":       "mcg",
    # IU
    "vitamin_d":      "IU",
}

# Units that should never be used as absolute thresholds for nutrients
# we extract from food labels. Rules with these CSV units are percentage-of-
# daily-calories rules (e.g. "saturated_fat < 7 percent of calories"), not
# gram thresholds — so we cannot compare them to extracted gram values.
_PERCENT_UNITS: frozenset[str] = frozenset({
    "percent",
    "percent_rda",
    "%",
})


def canonical_unit(nutrient_key: str, csv_unit: str = "") -> str:
    """
    Return the correct display unit for a nutrient.

    Priority:
      1. Canonical map (most reliable — keyed by nutrient name)
      2. CSV unit after stripping /day, /week, /meal suffixes —
         but ONLY if the result is a recognised physical unit (g, mg, kcal …)
      3. Empty string (better than showing "percent" or "servings")

    Parameters
    ----------
    nutrient_key : str
        Normalised nutrient name, e.g. "sodium", "saturated_fat"
    csv_unit : str
        Raw unit string from health_r.csv, e.g. "mg/day", "percent", "g/day"
    """
    key = nutrient_key.lower().strip()
    if key in _CANONICAL_UNITS:
        return _CANONICAL_UNITS[key]

    # Strip time/frequency suffixes from CSV unit
    raw = csv_unit.split("/")[0].strip().lower()

    # Accept only known physical units
    if raw in ("g", "mg", "mcg", "kcal", "kj", "iu", "ml", "l"):
        return raw

    # Everything else (percent, servings, cups …) → empty
    return ""


def is_percent_threshold(csv_unit: str) -> bool:
    """
    Return True when a CSV rule uses a percentage-of-calories threshold.
    Such rules cannot be compared directly against extracted gram/mg values.

    Examples that return True:
        "percent", "%", "percent_rda"
    """
    raw = csv_unit.strip().lower()
    return raw in _PERCENT_UNITS


def fmt_val(value: float, unit: str) -> str:
    """
    Format a numeric value + unit for display.

    Rules:
      - Integer display when value is whole (8g not 8.0g)
      - One decimal place when fractional (3.5g, 1.2mg)
      - Value and unit are always joined without a space (8g, 430mg, 390kcal)
    """
    if value == int(value):
        return f"{int(value)}{unit}"
    return f"{round(value, 1)}{unit}"


def format_nutrient(value: float, nutrient_key: str, csv_unit: str = "") -> str:
    """
    Master formatter — the single function every backend file calls.

    Parameters
    ----------
    value        : extracted numeric value
    nutrient_key : normalised key e.g. "sodium", "saturated_fat"
    csv_unit     : raw unit from CSV (used only as fallback, never "percent")

    Returns
    -------
    Formatted string e.g. "430mg", "8g", "390kcal"
    """
    unit = canonical_unit(nutrient_key, csv_unit)
    return fmt_val(value, unit)


def safe_pct_of_limit(user_value: float, threshold: float) -> tuple[int, int]:
    """
    Calculate percentage metrics for a threshold exceedance.

    Returns (pct_of_limit, pct_above) where:
        pct_of_limit = round((user_value / threshold) * 100)   e.g. 107
        pct_above    = pct_of_limit - 100                      e.g. 7

    Both values are clamped to [0, 999] to prevent display of nonsense
    ratios caused by percent-unit thresholds or near-zero denominators.
    """
    if threshold <= 0:
        return 100, 0
    ratio = user_value / threshold
    pct_of_limit = min(round(ratio * 100), 999)
    pct_above    = max(0, pct_of_limit - 100)
    return pct_of_limit, pct_above
