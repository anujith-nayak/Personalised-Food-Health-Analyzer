"""
Ingredient Cleaner & Normaliser
================================
Parts 1 & 2: Removes nutrition noise from the OCR ingredient list,
then normalises ingredient names for consistent AI/rule analysis.

Part 1 — Noise filtering
  OCR often picks up nutrition facts text alongside the ingredient list.
  Lines like "Carbohydrates 33g", "490 kcal", "28%" or "Servings Per Package"
  are silently dropped — only real food ingredient names are kept.

Part 2 — Name normalisation
  Common aliases, abbreviations and OCR variants are mapped to a
  canonical name. e.g. "HFCS" → "High Fructose Corn Syrup",
  "Maida" → "Refined Wheat Flour", "Hydrogenated Oil" → "Hydrogenated Vegetable Fat".
"""
from __future__ import annotations

import re
import logging

logger = logging.getLogger(__name__)

# ── Part 1: Noise patterns — lines matching these are NOT ingredients ─────────

# Nutrition keywords that appear on labels but are not ingredients.
# IMPORTANT: Only multi-word phrases or terms that cannot appear as ingredient names.
# Single generic words like "sugar", "salt", "fiber" are excluded because
# they are also valid ingredient names (e.g. "Sugar" as an ingredient is real).
_NUTRITION_NOISE_KEYWORDS: frozenset[str] = frozenset({
    "calories", "energy", "kcal", "kj",
    "total fat", "saturated fat", "trans fat",
    "total carbohydrate", "total carbohydrates",
    "dietary fiber", "dietary fibre",
    "total sugars", "added sugar", "added sugars", "of which sugars",
    "of which saturates",
    "serving size", "servings per", "per serving", "per 100g", "per 100 ml",
    "daily value", "% daily", "amount per", "nutrition facts",
    "nutritional information", "typical values", "reference intake",
    "ingredients", "allergen", "contains", "manufactured",
    "best before", "storage",
    "e number", "mono and diglycerides",
    "polyunsaturated", "monounsaturated",
    "vitamin c", "vitamin d", "vitamin a", "vitamin b",
    "cholesterol", "potassium", "calcium", "iron",
    "magnesium", "phosphorus", "zinc", "selenium",
    "total protein",
})

# Patterns that definitively identify a non-ingredient line
_NOISE_PATTERNS: list[re.Pattern] = [
    # Purely numeric (e.g. "490", "33g", "28%", "1.2mg")
    re.compile(r"^\s*[\d,]+(?:\.\d+)?\s*(?:g|mg|mcg|ml|kcal|kj|%|iu)?\s*$", re.IGNORECASE),
    # Percentage only
    re.compile(r"^\s*\d+\s*%\s*$"),
    # Starts with a number followed by unit (e.g. "33g Energy")
    re.compile(r"^\s*\d+[\.,]?\d*\s*(?:g|mg|kcal|kj|%|ml)\b", re.IGNORECASE),
    # Contains "per 100" / "per serving"
    re.compile(r"\bper\s+(?:100|serving|pack|portion)\b", re.IGNORECASE),
    # Format: "NutrientName NNN unit" (e.g. "Protein 6.2g")
    re.compile(r"^[a-z\s]{3,25}\s+[\d,]+(?:\.\d+)?\s*(?:g|mg|mcg|kcal|kj|%|iu)\s*$", re.IGNORECASE),
    # Very short token with only numbers/symbols
    re.compile(r"^[\d\s%.,:/\-\+\(\)]{1,6}$"),
    # E-numbers alone (e.g. "E102", "E211")
    re.compile(r"^\s*e\d{3,4}[a-z]?\s*$", re.IGNORECASE),
]

# Minimum word length — single-letter tokens and very short fragments are noise
_MIN_INGREDIENT_LENGTH = 3
_MAX_INGREDIENT_LENGTH = 60


def _is_noise(token: str) -> bool:
    """Return True if this token is nutrition noise rather than an ingredient."""
    t = token.strip().lower()

    # Too short or too long
    if len(t) < _MIN_INGREDIENT_LENGTH or len(t) > _MAX_INGREDIENT_LENGTH:
        return True

    # Matches a noise regex pattern
    for pat in _NOISE_PATTERNS:
        if pat.match(t):
            return True

    # Contains a known nutrition keyword — substring match is fine here
    # because all keywords are multi-word phrases that cannot appear in ingredient names
    for kw in _NUTRITION_NOISE_KEYWORDS:
        if kw in t:
            return True

    # Starts with a digit (nutrition value line, not an ingredient name)
    if re.match(r"^\d", t):
        return True

    # Standalone nutrition nutrient names without a value
    # (e.g. "Protein" or "Sodium" alone — when OCR splits name/value onto separate lines)
    # NOTE: "Sugar", "Salt", "Fat" are excluded because they ARE valid ingredient names.
    _STANDALONE_NUTRIENTS = re.compile(
        r"^(protein|sodium|energy|calories?|total\s+fat|carbohydrates?|"
        r"dietary\s+fib(?:er|re)|total\s+sugars?|added\s+sugars?|"
        r"potassium|calcium|iron|cholesterol|vitamins?|minerals?)$",
        re.IGNORECASE,
    )
    if _STANDALONE_NUTRIENTS.match(t.strip()):
        return True

    return False


# ── Part 2: Name normalisation map ───────────────────────────────────────────
# Maps known aliases / abbreviations / OCR variants → canonical ingredient name
# Keys are lowercase; matching is case-insensitive and substring-safe.

_NORMALISATION_MAP: list[tuple[str, str]] = [
    # Wheat / flour variants
    ("maida",                         "Refined Wheat Flour"),
    ("refined flour",                 "Refined Wheat Flour"),
    ("wheat flour",                   "Refined Wheat Flour"),
    ("all purpose flour",             "Refined Wheat Flour"),
    ("bleached flour",                "Refined Wheat Flour"),
    ("enriched flour",                "Enriched Wheat Flour"),
    ("whole wheat flour",             "Whole Wheat Flour"),
    ("atta",                          "Whole Wheat Flour"),

    # Oils and fats
    ("palm olein",                    "Palm Oil"),
    ("vegetable oil (palm)",          "Palm Oil"),
    ("rbd palm oil",                  "Palm Oil"),
    ("hydrogenated oil",              "Hydrogenated Vegetable Fat"),
    ("hydrogenated fat",              "Hydrogenated Vegetable Fat"),
    ("partially hydrogenated",        "Partially Hydrogenated Vegetable Fat"),
    ("vanaspati",                     "Hydrogenated Vegetable Fat"),
    ("shortening",                    "Vegetable Shortening"),
    ("vegetable shortening",          "Vegetable Shortening"),

    # Sweeteners
    ("hfcs",                          "High Fructose Corn Syrup"),
    ("high fructose corn syrup",      "High Fructose Corn Syrup"),
    ("corn syrup solids",             "Corn Syrup"),
    ("glucose syrup",                 "Glucose Syrup"),
    ("invert sugar syrup",            "Invert Sugar Syrup"),
    ("invert syrup",                  "Invert Sugar Syrup"),
    ("golden syrup",                  "Invert Sugar Syrup"),
    ("dextrose monohydrate",          "Dextrose"),
    ("anhydrous dextrose",            "Dextrose"),
    ("cane sugar",                    "Sugar"),
    ("sucrose",                       "Sugar"),
    ("granulated sugar",              "Sugar"),
    ("brown sugar",                   "Brown Sugar"),
    ("liquid glucose",                "Glucose"),

    # Cocoa / chocolate
    ("cocoa mass",                    "Cocoa Solids"),
    ("cocoa liquor",                  "Cocoa Solids"),
    ("cocoa powder",                  "Cocoa Powder"),
    ("dark chocolate",                "Dark Chocolate"),
    ("milk chocolate",                "Milk Chocolate"),

    # Dairy
    ("skimmed milk powder",           "Skimmed Milk Powder"),
    ("non fat dry milk",              "Skimmed Milk Powder"),
    ("milk solids",                   "Milk Solids"),
    ("whole milk powder",             "Whole Milk Powder"),
    ("full cream milk powder",        "Whole Milk Powder"),
    ("anhydrous milk fat",            "Butter Fat"),
    ("butter oil",                    "Butter Fat"),
    ("whey powder",                   "Whey Powder"),
    ("whey protein concentrate",      "Whey Protein"),

    # Starch / thickeners
    ("modified corn starch",          "Modified Starch"),
    ("modified food starch",          "Modified Starch"),
    ("modified tapioca starch",       "Modified Starch"),
    ("corn starch",                   "Corn Starch"),
    ("tapioca starch",                "Tapioca Starch"),

    # Leavening
    ("sodium bicarbonate",            "Baking Soda"),
    ("baking soda",                   "Baking Soda"),
    ("sodium carbonate",              "Raising Agent"),
    ("ammonium bicarbonate",          "Raising Agent"),
    ("raising agent",                 "Raising Agent"),
    ("leavening",                     "Raising Agent"),

    # Emulsifiers
    ("soy lecithin",                  "Soy Lecithin"),
    ("sunflower lecithin",            "Sunflower Lecithin"),
    ("lecithin",                      "Lecithin"),
    ("mono and diglycerides",         "Emulsifier"),
    ("polyglycerol esters",           "Emulsifier"),
    ("emulsifier",                    "Emulsifier"),

    # Salt
    ("iodised salt",                  "Iodised Salt"),
    ("iodized salt",                  "Iodised Salt"),
    ("sea salt",                      "Salt"),
    ("table salt",                    "Salt"),

    # Common additives
    ("artificial flavor",             "Artificial Flavour"),
    ("natural and artificial flavor", "Natural & Artificial Flavour"),
    ("natural flavors",               "Natural Flavour"),
    ("flavouring",                    "Flavouring"),
    ("vanillin",                      "Artificial Vanilla Flavour"),

    # Preservatives
    ("e211",                          "Sodium Benzoate"),
    ("e202",                          "Potassium Sorbate"),
    ("e200",                          "Sorbic Acid"),

    # Colours
    ("e102",                          "Tartrazine"),
    ("e110",                          "Sunset Yellow"),
    ("caramel color",                 "Caramel Colour"),
    ("caramel colour",                "Caramel Colour"),
]

# Build a fast lookup: lowercase normalised key → canonical name
_NORM_LOOKUP: dict[str, str] = {k.lower(): v for k, v in _NORMALISATION_MAP}


def _normalise_name(raw: str) -> str:
    """
    Normalise a single ingredient name.
    1. Title-case the raw name.
    2. Check the lookup table for any known alias (substring match).
    3. Return the canonical name if found, otherwise the title-cased original.
    """
    cleaned = raw.strip().lower()
    cleaned = re.sub(r"\s+", " ", cleaned)

    # Exact or substring match in normalisation table
    for alias, canonical in _NORM_LOOKUP.items():
        if alias == cleaned or alias in cleaned:
            return canonical

    # No alias found — just title-case the original
    return raw.strip().title()


# ── Deduplication ─────────────────────────────────────────────────────────────

def _deduplicate(ingredients: list[str]) -> list[str]:
    """Remove duplicates, preserving first occurrence (case-insensitive)."""
    seen: set[str] = set()
    out:  list[str] = []
    for item in ingredients:
        key = item.lower().strip()
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


# ── Public function ───────────────────────────────────────────────────────────

def clean_and_normalize_ingredients(raw_list: list[str]) -> list[str]:
    """
    Part 1: Filter out nutrition noise tokens from the raw OCR ingredient list.
    Part 2: Normalise remaining ingredient names via the alias table.

    Returns a clean, deduplicated list of real ingredient names (max 30).
    """
    cleaned: list[str] = []

    for token in raw_list:
        token = token.strip()
        if not token:
            continue

        if _is_noise(token):
            logger.debug(f"[IngCleaner] Noise removed: '{token}'")
            continue

        normalised = _normalise_name(token)
        cleaned.append(normalised)
        if normalised != token.strip().title():
            logger.info(f"[IngCleaner] Normalised: '{token}' → '{normalised}'")

    result = _deduplicate(cleaned)[:30]
    logger.info(f"[IngCleaner] {len(raw_list)} raw → {len(result)} clean ingredients")
    return result
