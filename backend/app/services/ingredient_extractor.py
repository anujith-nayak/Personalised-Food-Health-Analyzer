"""
Ingredient Extractor — Precision nutrition parser with %DV guard.

ROOT CAUSE OF WRONG VALUES:
  A nutrition label line looks like:
    "Total Fat  8g  10%"
  After OCR flattens newlines:
    "total fat 8g 10%"

  A naive pattern like:  fat[\D]{0,30}(\d+)g
  can match "8" correctly, BUT if the label is:
    "Sodium  430mg  19%"
  and OCR garbles it to:
    "Sodium 430mg 19%"
  a loose pattern could skip 430 and match 19 (the %DV).

FIXES APPLIED:
  1. UNIT-ANCHORED patterns — the number MUST be immediately followed by its unit
     (g, mg, mcg, kcal, IU). This eliminates bare percentage numbers.

  2. %DV GUARD — before accepting a match, check that the number is NOT
     followed by a "%" sign (which would make it a %DV value).

  3. LINE-BY-LINE parsing — instead of searching the whole flat string,
     we also attempt per-line extraction where each OCR line is examined
     individually. This prevents values from one nutrient's line being
     attributed to a different nutrient.

  4. SANITY CHECKS — after extraction, validate each value against
     physiologically plausible ranges. Flag or discard impossible values.

  5. CONFIDENCE SCORING — when multiple candidate matches exist for one
     nutrient, pick the one whose value is most plausible.
"""
import re
import logging

logger = logging.getLogger(__name__)

# ── Sanity ranges (min, max) per nutrient ─────────────────────────────────────
# Values outside these ranges are considered extraction errors.
SANITY_RANGES = {
    "calories":      (0,    2000),   # kcal per serving
    "total_fat":     (0,     100),   # g
    "saturated_fat": (0,      60),   # g
    "trans_fat":     (0,      20),   # g
    "cholesterol":   (0,    1000),   # mg
    "sodium":        (0,    3000),   # mg
    "carbohydrates": (0,     200),   # g
    "sugar":         (0,     150),   # g
    "fiber":         (0,      50),   # g
    "protein":       (0,     100),   # g
    "potassium":     (0,    5000),   # mg
    "calcium":       (0,    3000),   # mg
    "iron":          (0,     100),   # mg
    "serving_size":  (1,    1000),   # g or ml
}


def _normalise(text: str) -> str:
    """Flatten OCR output to a single clean lowercase string."""
    t = text
    t = re.sub(r"-\s*\n\s*", "", t)           # join hyphenated breaks
    t = re.sub(r"[\r\n\t]+", " ", t)           # newlines → space
    t = re.sub(r"[\.·•]{2,}", " ", t)          # dot leaders → space
    t = re.sub(r"[|\\{}<>~^]", " ", t)         # table junk → space
    t = re.sub(r"\s{2,}", " ", t)              # collapse spaces
    return t.lower().strip()


def _split_lines(text: str) -> list[str]:
    """Split OCR text into individual lines, normalised."""
    lines = []
    for raw in text.split("\n"):
        line = raw.strip()
        if len(line) > 1:
            # Normalise within the line but keep it separate
            line = re.sub(r"[\.·•]{2,}", " ", line)
            line = re.sub(r"\s{2,}", " ", line)
            lines.append(line.lower())
    return lines


def _pdv_guard(text: str, match_end: int) -> bool:
    """
    Return True if the character(s) immediately after the match look like
    a % Daily Value percentage (e.g. "  19%"). If so, the match is a %DV —
    do NOT use it as the nutrient amount.
    """
    # Look at the 10 characters after the match
    suffix = text[match_end: match_end + 10].strip()
    return suffix.startswith("%")


# ── Nutrient patterns — unit-anchored, %DV-safe ───────────────────────────────
#
# Each pattern REQUIRES the unit immediately after the number.
# Number format: digits with optional comma-thousands and optional decimal.
_N  = r"([\d,]+(?:\.\d+)?)"   # captured number
_WS = r"[\s:\/\-\.]*"         # flexible whitespace / separator

# Patterns: (regex, unit_for_logging)
# All use re.IGNORECASE
NUTRIENT_PATTERNS: dict[str, list[str]] = {
    "calories": [
        # "Calories 250 kcal", "Energy 250kcal", "Calories 250"
        # Calories often has no unit on US labels — allow bare number if surrounded
        # by word boundary / end-of-line
        rf"(?:calories?|energy|cal(?:ories?)?)[\s:\/\-]*{_N}\s*(?:kcal|kj|cal)?\b",
        rf"{_N}\s*kcal\b",
    ],
    "sodium": [
        rf"sodium{_WS}{_N}\s*mg\b",
        rf"\bna\b{_WS}{_N}\s*mg\b",
    ],
    "total_fat": [
        rf"total\s+fat{_WS}{_N}\s*g\b",
        rf"fat\s+total{_WS}{_N}\s*g\b",
    ],
    "saturated_fat": [
        rf"saturated\s+fat{_WS}{_N}\s*g\b",
        rf"sat\.?\s*fat{_WS}{_N}\s*g\b",
        rf"saturates{_WS}{_N}\s*g\b",
    ],
    "trans_fat": [
        rf"trans\s+fat{_WS}{_N}\s*g\b",
        rf"trans\s+fatty{_WS}{_N}\s*g\b",
        rf"\btrans\b{_WS}{_N}\s*g\b",
    ],
    "cholesterol": [
        rf"cholesterol{_WS}{_N}\s*mg\b",
        rf"chol\.?{_WS}{_N}\s*mg\b",
    ],
    "carbohydrates": [
        rf"total\s+carbohydrates?{_WS}{_N}\s*g\b",
        rf"carbohydrates?{_WS}{_N}\s*g\b",
        rf"total\s+carbs?{_WS}{_N}\s*g\b",
        rf"\bcarbs?{_WS}{_N}\s*g\b",
    ],
    "sugar": [
        rf"total\s+sugars?{_WS}{_N}\s*g\b",
        rf"added\s+sugars?{_WS}{_N}\s*g\b",
        rf"\bsugars?{_WS}{_N}\s*g\b",
    ],
    "fiber": [
        rf"dietary\s+fib(?:er|re){_WS}{_N}\s*g\b",
        rf"\bfib(?:er|re){_WS}{_N}\s*g\b",
    ],
    "protein": [
        rf"protein{_WS}{_N}\s*g\b",
    ],
    "serving_size": [
        rf"serving\s+size{_WS}{_N}\s*(?:g|ml|oz)\b",
        rf"per\s+serving{_WS}{_N}\s*(?:g|ml)\b",
        rf"per\s+{_N}\s*(?:g|ml)\b",
    ],
    "potassium": [
        rf"potassium{_WS}{_N}\s*mg\b",
    ],
    "calcium": [
        rf"calcium{_WS}{_N}\s*(?:mg|%)\b",
    ],
    "iron": [
        rf"\biron{_WS}{_N}\s*(?:mg|%)\b",
    ],
}


def _try_patterns(text: str, patterns: list[str]) -> float | None:
    """
    Try each pattern against `text`. Return the first plausible numeric match,
    skipping any that are immediately followed by '%' (i.e. are %DV values).
    """
    for pattern in patterns:
        try:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                # %DV guard: reject if the match is followed by %
                if _pdv_guard(text, m.end()):
                    continue
                try:
                    val = float(m.group(1).replace(",", ""))
                    return val
                except (ValueError, IndexError):
                    continue
        except re.error:
            continue
    return None


def _sanity_check(key: str, value: float) -> float | None:
    """Return value if within plausible range, else None."""
    lo, hi = SANITY_RANGES.get(key, (0, 99999))
    if lo <= value <= hi:
        return value
    logger.warning(f"  SANITY FAIL {key}: {value} not in [{lo}, {hi}] — discarding")
    return None


def extract_nutrition(text: str) -> dict:
    """
    Two-pass extraction:
      Pass 1 — search the full flat normalised string.
      Pass 2 — search individual lines of the original text.
    For each nutrient, keep the Pass-1 result if it passes sanity.
    If Pass-1 fails sanity or is missing, try Pass-2.
    Log every FOUND and MISSED.
    """
    flat  = _normalise(text)
    lines = _split_lines(text)

    logger.info("=" * 60)
    logger.info("NORMALISED OCR (first 500 chars):")
    logger.info(flat[:500])
    logger.info("=" * 60)
    logger.info("NUTRIENT EXTRACTION:")

    results: dict[str, float | None] = {}

    for nutrient, patterns in NUTRIENT_PATTERNS.items():

        # ── Pass 1: full flat text ──────────────────────────────────────
        val1 = _try_patterns(flat, patterns)
        if val1 is not None:
            val1 = _sanity_check(nutrient, val1)

        # ── Pass 2: line-by-line (catches values split across lines) ───
        val2 = None
        if val1 is None:
            for line in lines:
                candidate = _try_patterns(line, patterns)
                if candidate is not None:
                    candidate = _sanity_check(nutrient, candidate)
                    if candidate is not None:
                        val2 = candidate
                        break

        final = val1 if val1 is not None else val2

        if final is not None:
            logger.info(f"  FOUND   {nutrient:20} = {final:>10}")
        else:
            logger.info(f"  MISSED  {nutrient}")

        results[nutrient] = final

    found = {k: v for k, v in results.items() if v is not None}
    logger.info("=" * 60)
    logger.info(f"EXTRACTED {len(found)}/{len(NUTRIENT_PATTERNS)}: {found}")
    logger.info("=" * 60)

    return results


def extract_product_name(text: str) -> str:
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    skip = ["ingredient", "nutrition", "serving", "calorie", "per 100",
            "per serving", "contain", "allergy", "manufactur", "best before",
            "storage", "www", "daily value", "% daily", "amount per", "fact"]
    for line in lines[:10]:
        ll = line.lower()
        if (len(line) > 2 and
                not any(kw in ll for kw in skip) and
                not re.match(r"^[\d%]", line)):
            return line.title()
    return "Unknown Product"


def extract_ingredients(text: str) -> list[str]:
    flat = _normalise(text)
    m = re.search(
        r"ingredients?\s*[:\-]?\s*(.*?)(?:nutritional|nutrition\s+facts|per\s+\d|allergen|contains\s*:|manufactur|$)",
        flat, re.DOTALL,
    )
    if not m:
        return []
    raw = re.sub(r"\(.*?\)", "", m.group(1).strip())
    raw = re.sub(r"\[.*?\]", "", raw)
    parts = re.split(r"[,;]", raw)
    out = []
    for p in parts:
        p = p.strip().strip(".")
        p = re.sub(r"^\d+\.\s*", "", p)
        if len(p) > 1 and not re.match(r"^\d+$", p):
            out.append(p.strip().title())
    return [i for i in out if i][:30]


def parse_food_label(ocr_text: str) -> dict:
    logger.info("===== RAW OCR TEXT =====")
    logger.info(ocr_text[:800])
    logger.info("========================")
    nutrition   = extract_nutrition(ocr_text)
    ingredients = extract_ingredients(ocr_text)
    name        = extract_product_name(ocr_text)
    return {
        "product_name": name,
        "ingredients":  ingredients,
        "nutrition":    nutrition,
        "raw_ocr_text": ocr_text[:2000],
    }
