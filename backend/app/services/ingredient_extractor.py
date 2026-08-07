"""
Ingredient & Nutrition Extractor — Robust multi-strategy parser.

Improvements over the previous version:
  1. Fuzzy / OCR-error-tolerant nutrient name matching using regex
     (e.g. "Sod1um", "Prot3in", "Calclum" are all matched).
  2. Multi-line value recovery: when a nutrient name appears on one line
     and its value on the next, we stitch the lines together before parsing.
  3. Intelligent orphan recovery: bare numbers on their own line are matched
     to the nearest preceding or following nutrient name.
  4. Unit-anchored patterns with %DV guard — values must be followed by g / mg
     (not %) to avoid picking up Daily Value percentages.
  5. Expanded OCR-variant spelling patterns for every nutrient.
  6. Two-pass extraction: full flat text first, then line-by-line fallback.
  7. Sanity-range validation on every extracted value.
  8. Detailed logging: FOUND, MISSED, RECOVERED, CONFIDENCE per nutrient.
"""

import re
import logging

logger = logging.getLogger(__name__)

# ── Sanity ranges (min, max) ───────────────────────────────────────────────────
SANITY_RANGES: dict[str, tuple[float, float]] = {
    "calories":      (0,  2000),
    "total_fat":     (0,   200),
    "saturated_fat": (0,   100),
    "trans_fat":     (0,    20),
    "cholesterol":   (0,  1500),
    "sodium":        (0,  5000),
    "carbohydrates": (0,   300),
    "sugar":         (0,   200),
    "fiber":         (0,    80),
    "protein":       (0,   200),
    "potassium":     (0,  6000),
    "calcium":       (0,  3000),
    "iron":          (0,   150),
    "serving_size":  (1,  2000),
}

# ── OCR common character substitutions ────────────────────────────────────────
# These allow our normaliser to fix garbled text before regex matching.
_OCR_FIXES: list[tuple[str, str]] = [
    # Zero / O confusion
    (r"\b0g\b",        "og"),
    # Number-to-letter in nutrient names
    (r"\bsod1um\b",    "sodium"),
    (r"\bsod[il1]um\b","sodium"),
    (r"\bprot[e3][il1]n\b", "protein"),
    (r"\bcalc[il1]um\b", "calcium"),
    (r"\bp0tass[il1]um\b", "potassium"),
    (r"\bp[o0]tass[il1]um\b", "potassium"),
    (r"\bch[o0]lest[e3]r[o0]l\b", "cholesterol"),
    (r"\bcarb[o0]hydrate[s]?\b", "carbohydrates"),
    (r"\bsat[vu]rated\b", "saturated"),
    (r"\btrans f[a4]t\b", "trans fat"),
    (r"\bdi[e3]tary\b", "dietary"),
    (r"\bf[il1]b[e3]r\b", "fiber"),
    (r"\bf[il1]bre\b", "fiber"),
    (r"\bsugars?\b", "sugar"),
    # Unit fixes
    (r"(\d)\s*[gG9]\b", r"\1g"),       # "8G" or "8 g" → "8g"
    (r"(\d)\s*[mM][gG9]\b", r"\1mg"),  # "430MG" → "430mg"
    (r"og\b", "0g"),                   # "og" → "0g"
    # Dot leaders and junk separators between name and value
    (r"[\.·•·]{2,}", " "),
    (r"[|\\{}<>~^]", " "),
    # Double-space collapse
    (r"\s{2,}", " "),
]


def _apply_ocr_fixes(text: str) -> str:
    t = text
    for pattern, replacement in _OCR_FIXES:
        t = re.sub(pattern, replacement, t, flags=re.IGNORECASE)
    return t


def _normalise(text: str) -> str:
    """Flatten OCR output to a single clean lowercase string with OCR fixes applied."""
    t = text
    t = re.sub(r"-\s*\n\s*", "", t)           # join hyphenated line breaks
    t = re.sub(r"[\r\n\t]+", " ", t)           # newlines → single space
    t = _apply_ocr_fixes(t)
    return t.lower().strip()


def _split_lines(text: str) -> list[str]:
    """
    Split OCR text into lines. Each line is lowercased and has OCR fixes applied.
    Empty / single-character lines are discarded.
    """
    lines = []
    for raw in text.split("\n"):
        line = raw.strip()
        if len(line) > 1:
            line = _apply_ocr_fixes(line)
            lines.append(line.lower())
    return lines


def _stitch_multiline(lines: list[str]) -> list[str]:
    """
    Merge lines where the nutrient name, value, and unit appear on separate lines.
    Handles 2-line (name / "430mg") AND 3-line (name / "430" / "mg") splits.
    """
    if not lines:
        return lines

    # A line that is ONLY a numeric value (with optional unit)
    _VALUE_ONLY = re.compile(
        r"^\s*[\d,]+(?:\.\d+)?\s*(?:g|mg|mcg|kcal|kj|%|iu|cal)?\s*$",
        re.IGNORECASE,
    )
    # A line that is ONLY a unit (OCR split unit onto its own line)
    _UNIT_ONLY = re.compile(
        r"^\s*(?:g|mg|mcg|kcal|kj|iu|cal|ml)\s*$",
        re.IGNORECASE,
    )
    # A line that contains a nutrient keyword
    _HAS_NAME = re.compile(
        r"calories?|energy|fat|protein|carbohydrate|sodium|sugar|fiber|fibre|"
        r"cholesterol|potassium|calcium|iron|vitamin|serving",
        re.IGNORECASE,
    )

    stitched = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # Case 1: "Nutrient Name" then "value unit" on next line
        if i + 1 < len(lines) and _HAS_NAME.search(line) and _VALUE_ONLY.match(lines[i + 1]):
            merged = line + " " + lines[i + 1]
            # Case 2: "Nutrient Name" / "value" / "unit" on 3 separate lines
            if i + 2 < len(lines) and _UNIT_ONLY.match(lines[i + 2]):
                merged += lines[i + 2]   # append unit without space: "14" + "g" = "14g"
                i += 3
            else:
                i += 2
            stitched.append(merged)
            continue

        # Case 3: bare unit on its own line following a value line — already handled above,
        # but if a unit line appears after a non-name line, merge it back
        if i > 0 and _UNIT_ONLY.match(line) and stitched:
            stitched[-1] = stitched[-1] + line.strip()
            i += 1
            continue

        stitched.append(line)
        i += 1
    return stitched


# ── Number capture helpers ─────────────────────────────────────────────────────
_N  = r"([\d,]+(?:\.\d+)?)"          # captured number (digits, optional comma & decimal)
_WS = r"[\s:\/\-\.]{0,25}"           # flexible separator between name and value

# OCR-tolerant fuzzy patterns for each nutrient name
# Each tuple: (key, [regex_patterns...])
# Patterns ordered from most specific → least specific to minimise false matches.

_NUTRIENT_PATTERNS: dict[str, list[str]] = {

    "calories": [
        # Standard: "Calories 250", "Energy 250 kcal"
        rf"(?:cal[o0]ri[e3]s?|energy|cal\.?){_WS}{_N}\s*(?:kcal|kj|cal)?\b",
        # OCR garbled
        rf"cal[o0\s]?r[il1][e3]s?{_WS}{_N}",
        rf"{_N}\s*kcal\b",
        rf"{_N}\s*kj\b",
        # Bare number after "Cal"
        rf"^cal[^a-z]{_N}",
    ],

    "total_fat": [
        # With unit
        rf"total\s*f[a4]t{_WS}{_N}\s*g(?:\b|%|\d)",
        rf"t[o0]tal\s*f[a4]t{_WS}{_N}\s*g(?:\b|%|\d)",
        rf"fat\s*[,;]?\s*total{_WS}{_N}\s*g(?:\b|%|\d)",
        rf"^f[a4]t{_WS}{_N}\s*g(?:\b|%|\d)",
        # Bare number (unit missing/OCR dropped it)
        rf"total\s*f[a4]t{_WS}{_N}(?:\s*g|\s*(?=%|\s|$))",
        rf"^f[a4]t\s*{_N}(?:\s*g)?\s*$",
    ],

    "saturated_fat": [
        # With unit — standard
        rf"sat(?:urated)?\s*f[a4]t{_WS}{_N}\s*g(?:\b|%|\d)",
        rf"s[a4]tur[a4]ted\s*f[a4]t{_WS}{_N}\s*g(?:\b|%|\d)",
        rf"saturated\s*fatty\s*acids?{_WS}{_N}\s*g(?:\b|%|\d)",
        rf"saturates{_WS}{_N}\s*g(?:\b|%|\d)",
        # "of which saturates/saturated" — Coca-Cola, UK/EU labels
        rf"of\s+which\s+saturates?d?{_WS}{_N}\s*g(?:\b|%|\d)",
        rf"of\s+which\s+sat\.?{_WS}{_N}\s*g(?:\b|%|\d)",
        rf"s[a4]t\.?\s*f[a4]t{_WS}{_N}\s*g(?:\b|%|\d)",
        rf"s[a4@]t[vu]r[a4@]t[e3]d\s*f[a4]t{_WS}{_N}\s*g(?:\b|%|\d)",
        # Bare number fallback
        rf"sat(?:urated)?\s*f[a4]t{_WS}{_N}(?:\s*g)?\s*$",
        rf"s[a4]t\.?\s*f[a4]t\s+{_N}$",
        rf"saturated\s*fatty\s*acids?\s+{_N}$",
        rf"of\s+which\s+saturates?d?\s+{_N}$",
    ],

    "trans_fat": [
        rf"tr[a4]ns\s*f[a4]t{_WS}{_N}\s*g(?:\b|%|\d)",
        rf"tr[a4]ns\s*fatty\s*acids?{_WS}{_N}\s*g(?:\b|%|\d)",
        rf"\btr[a4]ns\b{_WS}{_N}\s*g(?:\b|%|\d)",
        # Bare
        rf"tr[a4]ns\s*f[a4]t{_WS}{_N}(?:\s*g)?\s*$",
        rf"tr[a4]ns\s*fatty\s*acids?\s+{_N}$",
        rf"\btr[a4]ns\s+{_N}$",
    ],

    "cholesterol": [
        # mg immediately followed by % or digit (no space)
        rf"ch[o0]lester[o0]l{_WS}{_N}\s*mg",
        rf"ch[o0]lest\.?{_WS}{_N}\s*mg",
        rf"ch[o0]l[e3]st[e3]r[o0]l{_WS}{_N}\s*mg",
        # Garbled "Chol3sterol"
        rf"chol\w{0,6}l{_WS}{_N}\s*mg",
        # Abbreviation "Chol." or "Chol"
        rf"chol\.?\s*{_N}\s*mg",
        rf"chol\.?\s*{_N}$",
        # Bare number
        rf"ch[o0]lest\w*{_WS}{_N}(?:\s*mg)?\s*$",
    ],

    "sodium": [
        rf"s[o0]d[il1]um{_WS}{_N}\s*mg",
        rf"s[o0]d[il1\!]um{_WS}{_N}\s*mg",
        rf"\bna\b{_WS}{_N}\s*mg",
        rf"s[o0]d\.?{_WS}{_N}\s*mg",
        rf"\bs[a4]lt{_WS}{_N}\s*mg",
        rf"sodium\.?\s*{_N}\s*mg",
        # Abbreviation "Sod."
        rf"sod\.?\s*{_N}\s*mg",
        rf"sod\.?\s*{_N}$",
        # Sodium in grams (some labels use g instead of mg)
        # Convert: value × 1000 handled separately; just capture the number
        rf"s[o0]d[il1]um{_WS}{_N}\s*g(?:\b|%|\d)",
        rf"sodium{_WS}{_N}\s*g(?:\b|%|\d)",
        # Bare number
        rf"s[o0]d[il1]um{_WS}{_N}(?:\s*(?:mg|g))?\s*$",
        # Garbled "S0d1um"
        rf"s[o0]d\w{0,3}m{_WS}{_N}\s*mg",
    ],

    "carbohydrates": [
        rf"total\s*carb[o0]hydrates?{_WS}{_N}\s*g(?:\b|%|\d)",
        rf"t[o0]tal\s*c[a4]rb[o0]hydr[a4]te[s]?{_WS}{_N}\s*g(?:\b|%|\d)",
        rf"carb[o0]hydrates?{_WS}{_N}\s*g(?:\b|%|\d)",
        rf"\bcarbs?\b{_WS}{_N}\s*g(?:\b|%|\d)",
        rf"of\s+which\s+carb[o0]hydrates?{_WS}{_N}\s*g(?:\b|%|\d)",
        rf"carb[o0]hydrate\s*\([^)]*\){_WS}{_N}\s*g(?:\b|%|\d)",
        # "Total Carb." abbreviation (with and without space before number)
        rf"total\s*carb\.?\s*{_N}\s*g(?:\b|%|\d)",
        rf"total\s*carb\.?\s*{_N}$",
        # Garbled digits in "Total/T0t4l" and "Carb/C4rb"
        rf"t[o0]t[a4]l\s*c[a4]rb\.?{_WS}{_N}\s*g(?:\b|%|\d)",
        rf"t[o0]t[a4]l\s*c[a4]rb\.?\s*{_N}$",
        # Bare number
        rf"carb[o0]hydrates?{_WS}{_N}(?:\s*g)?\s*$",
        rf"\bcarbs?\s+{_N}$",
    ],

    "fiber": [
        rf"dietary\s*fib(?:er|re){_WS}{_N}\s*g(?:\b|%|\d)",
        rf"d[il1][e3]t[a4]ry\s*f[il1]b[e3]r{_WS}{_N}\s*g(?:\b|%|\d)",
        rf"\bfib(?:er|re){_WS}{_N}\s*g(?:\b|%|\d)",
        rf"of\s+which\s+(?:dietary\s*)?fib(?:er|re){_WS}{_N}\s*g(?:\b|%|\d)",
        rf"roughage{_WS}{_N}\s*g(?:\b|%|\d)",
        # "less than Xg" — Oreo style
        rf"dietary\s*fib(?:er|re)\s+less\s+than\s+{_N}\s*g",
        rf"\bfib(?:er|re)\s+less\s+than\s+{_N}\s*g",
        # Abbreviations "Fib."
        rf"fib\.?\s*{_N}\s*g(?:\b|%|\d)",
        rf"fib\.?\s*{_N}$",
        # Bare
        rf"\bfib(?:er|re)\s+{_N}$",
        rf"dietary\s*fib(?:er|re){_WS}{_N}(?:\s*g)?\s*$",
    ],

    "sugar": [
        rf"total\s*sugars?{_WS}{_N}\s*g(?:\b|%|\d)",
        rf"t[o0]tal\s*sugars?{_WS}{_N}\s*g(?:\b|%|\d)",
        # Garbled "T0t4l Sug4rs"
        rf"t[o0]t[a4]l\s*s[uo][g9][a4]rs?{_WS}{_N}\s*g(?:\b|%|\d)",
        rf"t[o0]t[a4]l\s*s[uo][g9][a4]rs?\s*{_N}$",
        rf"added\s*sugars?{_WS}{_N}\s*g(?:\b|%|\d)",
        rf"incl(?:udes?)?\s*{_N}\s*g\s*added\s*sugars?",
        rf"\bsugars?{_WS}{_N}\s*g(?:\b|%|\d)",
        rf"of\s+which\s+sugars?{_WS}{_N}\s*g(?:\b|%|\d)",
        # Abbreviation "Sug."
        rf"sug\.?\s*{_N}\s*g(?:\b|%|\d)",
        rf"sug\.?\s*{_N}$",
        # Bare
        rf"\bsugars?\s+{_N}$",
    ],

    "protein": [
        rf"pr[o0]t[e3][il1]n{_WS}{_N}\s*g(?:\b|%|\d)",
        rf"pr[o0]t[e3\!][il1\!]n{_WS}{_N}\s*g(?:\b|%|\d)",
        rf"prot\.?\s*{_N}\s*g(?:\b|%|\d)",
        # Abbreviation "Prot."
        rf"prot\.?\s*{_N}$",
        # Bare number
        rf"pr[o0]t[e3][il1]n{_WS}{_N}(?:\s*g)?\s*$",
        rf"^protein\s+{_N}$",
    ],

    "potassium": [
        rf"p[o0]tass[il1]um{_WS}{_N}\s*mg(?:\b|%|\d)",
        rf"p[o0]t[a4]ss[il1\!]um{_WS}{_N}\s*mg(?:\b|%|\d)",
        rf"\bk\b{_WS}{_N}\s*mg(?:\b|%|\d)",
        # Bare
        rf"p[o0]tass[il1]um{_WS}{_N}(?:\s*mg)?\s*$",
    ],

    "calcium": [
        rf"calc[il1]um{_WS}{_N}\s*mg(?:\b|%|\d)",
        rf"c[a4]lc[il1\!]um{_WS}{_N}\s*mg(?:\b|%|\d)",
        rf"calc[il1]um{_WS}{_N}\s*%",
        rf"\bca\b{_WS}{_N}\s*mg(?:\b|%|\d)",
        # Bare
        rf"calc[il1]um{_WS}{_N}(?:\s*mg)?\s*$",
    ],

    "iron": [
        rf"\bir[o0]n{_WS}{_N}\s*mg(?:\b|%|\d)",
        rf"\bir[o0\!]n{_WS}{_N}\s*mg(?:\b|%|\d)",
        rf"\bir[o0]n{_WS}{_N}\s*%",
        rf"\bfe\b{_WS}{_N}\s*mg(?:\b|%|\d)",
        # Bare
        rf"\bir[o0]n{_WS}{_N}(?:\s*mg)?\s*$",
    ],

    "serving_size": [
        rf"serving\s+size{_WS}{_N}\s*(?:g|ml|oz)\b",
        rf"serv[il1]ng\s+s[il1]ze{_WS}{_N}\s*(?:g|ml|oz)\b",
        rf"per\s+serving{_WS}{_N}\s*(?:g|ml|oz)\b",
        rf"per\s+{_N}\s*(?:g|ml|oz)\b",
        rf"serv\.\s*size{_WS}{_N}\s*(?:g|ml)\b",
    ],
}

# ── %DV guard ─────────────────────────────────────────────────────────────────

def _is_pdv(text: str, match_end: int) -> bool:
    """
    Return True ONLY when the captured value IS a percentage (Daily Value).
    This means: the match ends at the number and the very next non-space char is %.

    We do NOT block when the sequence is "1.5g8%" because:
      - "1.5g" is the nutrient value (1.5g fat)
      - "8%" is the %DV — which is a separate token
    The pattern ends after "g8" (matching g followed by digit 8),
    so `after` = "%..." → we would wrongly block it.

    Fix: only block if the character immediately after the match is % with
    NO preceding digits (i.e. the match itself ended at a unit boundary, not a digit).
    """
    # If the match ended on a digit, the % belongs to the DV column, not our value
    if match_end > 0 and text[match_end - 1:match_end].isdigit():
        return False   # digit before %, so this is "14g8%" — our value is 14, not 8
    suffix = text[match_end: match_end + 3]
    return bool(re.match(r"^\s*%", suffix))


# ── Pattern matching helpers ───────────────────────────────────────────────────

def _try_patterns(text: str, patterns: list[str], nutrient_key: str) -> float | None:
    """
    Try each pattern against `text`.
    Returns the FIRST plausible numeric value that passes the %DV guard.
    """
    for pattern in patterns:
        try:
            for m in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
                # Skip matches that are %DV values
                if _is_pdv(text, m.end()):
                    continue
                # Group 1 should be the numeric value
                try:
                    raw_val = m.group(1).replace(",", "").strip()
                    # OCR artefact: trailing '9' sometimes means 'g' was mis-read
                    # Only apply if the value looks like it ends with a stray digit
                    # that makes it physiologically impossible
                    value = float(raw_val)
                    return value
                except (ValueError, IndexError):
                    continue
        except re.error as e:
            logger.debug(f"  Regex error in pattern for {nutrient_key}: {e}")
            continue
    return None


def _sanity_check(key: str, value: float) -> float | None:
    """Return value if within plausible physiological range, else None."""
    lo, hi = SANITY_RANGES.get(key, (0, 999_999))
    if lo <= value <= hi:
        return value
    logger.warning(f"  [SANITY] {key}={value} outside [{lo}, {hi}] — discarded")
    return None


# ── Orphan value recovery ─────────────────────────────────────────────────────

# Maps keyword fragments to nutrient keys for orphan recovery
_NAME_TO_KEY: list[tuple[str, str]] = [
    (r"calori|energy|kcal",        "calories"),
    (r"total\s*fat",               "total_fat"),
    (r"sat\w*\s*fat|saturate",     "saturated_fat"),
    (r"trans\s*fat",               "trans_fat"),
    (r"cholest",                   "cholesterol"),
    (r"sod[il1]?um|sodium",        "sodium"),
    (r"total\s*carb|carbohydr",    "carbohydrates"),
    (r"fib(?:er|re)|roughage",     "fiber"),
    (r"sugar",                     "sugar"),
    (r"prot[e3][il1]n|protein",    "protein"),
    (r"potass|p[o0]tass",          "potassium"),
    (r"calc[il1]?um|calcium",      "calcium"),
    (r"ir[o0]n\b",                 "iron"),
]

_BARE_VALUE = re.compile(
    r"^\s*[\d,]+(?:\.\d+)?\s*(?:g|mg|mcg|kcal|kj|iu)?\s*$",
    re.IGNORECASE,
)


def _recover_orphans(lines: list[str], results: dict[str, float | None]) -> dict[str, float | None]:
    """
    For nutrients still missing after two-pass extraction:
      Walk each line. If a line contains a nutrient name but no value,
      look one line ahead (or behind) for a bare numeric value and assign it.
    """
    recovered = dict(results)

    for i, line in enumerate(lines):
        for pattern, key in _NAME_TO_KEY:
            if recovered.get(key) is not None:
                continue  # already extracted
            if not re.search(pattern, line, re.IGNORECASE):
                continue

            # Check next line for a bare value
            for offset in [1, -1]:
                j = i + offset
                if 0 <= j < len(lines):
                    neighbor = lines[j].strip()
                    if _BARE_VALUE.match(neighbor):
                        raw = re.sub(r"[^\d.,]", "", neighbor)
                        try:
                            val = float(raw.replace(",", ""))
                            val = _sanity_check(key, val)
                            if val is not None:
                                recovered[key] = val
                                logger.info(
                                    f"  [RECOVERED] {key:20} = {val:>8}  "
                                    f"(from line {j}: '{neighbor}')"
                                )
                        except ValueError:
                            pass
                        break
    return recovered


# ── Two-pass extraction ────────────────────────────────────────────────────────

def extract_nutrition(text: str) -> dict:
    """
    Three-pass extraction:
      Pass 1 — full flat normalised string (catches values on the same line)
      Pass 2 — stitched lines (catches name/value split across adjacent lines)
      Pass 3 — orphan recovery (bare numeric values near a nutrient name)

    Logs FOUND / MISSED / RECOVERED with confidence estimate.
    """
    flat  = _normalise(text)
    raw_lines = _split_lines(text)
    lines = _stitch_multiline(raw_lines)

    logger.info("=" * 65)
    logger.info("[EXTRACTOR] Normalised OCR (first 600 chars):")
    logger.info(flat[:600])
    logger.info("=" * 65)

    logger.info("[EXTRACTOR] OCR Lines (after stitching):")
    for l in lines:
        logger.info(f"  | {l}")
    logger.info("=" * 65)

    results: dict[str, float | None] = {}

    for nutrient, patterns in _NUTRIENT_PATTERNS.items():

        # Pass 1 — flat string
        val = _try_patterns(flat, patterns, nutrient)
        if val is not None:
            val = _sanity_check(nutrient, val)

        # Pass 2 — line-by-line (catches split layouts)
        if val is None:
            for line in lines:
                candidate = _try_patterns(line, patterns, nutrient)
                if candidate is not None:
                    candidate = _sanity_check(nutrient, candidate)
                    if candidate is not None:
                        val = candidate
                        break

        results[nutrient] = val

    # Pass 3 — orphan recovery
    results = _recover_orphans(lines, results)

    # ── Special conversion: sodium in grams → mg ──────────────────────────────
    # Some labels (Kellogg's, Coca-Cola) print sodium in g (e.g. "0.77g").
    # If sodium was matched but the value is very small (< 10), it was likely
    # in grams — convert to mg by multiplying by 1000.
    if results.get("sodium") is not None and results["sodium"] < 10:
        converted = results["sodium"] * 1000
        lo, hi = SANITY_RANGES["sodium"]
        if lo <= converted <= hi:
            logger.info(f"[EXTRACTOR] Sodium converted from g to mg: {results['sodium']}g → {converted}mg")
            results["sodium"] = converted

    # ── Summary log ───────────────────────────────────────────────────────────
    found  = {k: v for k, v in results.items() if v is not None}
    missed = [k for k, v in results.items() if v is None]
    confidence = int(len(found) / len(_NUTRIENT_PATTERNS) * 100)

    logger.info("[EXTRACTOR] RESULTS:")
    for k, v in results.items():
        if v is not None:
            logger.info(f"  FOUND    {k:20} = {v:>10}")
        else:
            logger.info(f"  MISSED   {k}")

    logger.info(f"[EXTRACTOR] Extracted {len(found)}/{len(_NUTRIENT_PATTERNS)} nutrients  "
                f"confidence={confidence}%")
    logger.info(f"[EXTRACTOR] Missed: {missed}")
    logger.info("=" * 65)

    return results


# ── Product name and ingredient extraction ─────────────────────────────────────

_SKIP_WORDS = [
    "ingredient", "nutrition", "serving", "calorie", "per 100",
    "per serving", "contain", "allergy", "manufactur", "best before",
    "storage", "www", "daily value", "% daily", "amount per", "fact",
    "dietary", "total fat", "saturated", "cholesterol", "sodium",
]


def extract_product_name(text: str) -> str:
    """
    Heuristic: the product name is one of the first non-nutritional lines,
    is not purely numeric, and is typically title-cased or all-caps.
    """
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    for line in lines[:12]:
        ll = line.lower()
        if (len(line) > 3
                and not any(kw in ll for kw in _SKIP_WORDS)
                and not re.match(r"^[\d%]", line)
                and not re.match(r"^(nutrition|ingredient|serving)", ll)):
            return line.title()
    return "Unknown Product"


def extract_ingredients(text: str) -> list[str]:
    """
    Extract the ingredients list from the OCR text.
    Looks for the 'Ingredients:' block, parses comma/semi-colon separated items,
    then passes the raw list through the ingredient cleaner to remove nutrition
    noise and normalise names (Parts 1 & 2).
    """
    from app.services.ingredient_cleaner import clean_and_normalize_ingredients

    flat = _normalise(text)
    m = re.search(
        r"ingredients?\s*[:\-]?\s*(.*?)"
        r"(?:nutritional|nutrition\s*facts?|per\s*\d|allergen|contains\s*:|"
        r"manufactur|best\s*before|storage|$)",
        flat,
        re.DOTALL | re.IGNORECASE,
    )
    if not m:
        return []

    raw = m.group(1).strip()
    raw = re.sub(r"\(.*?\)", "", raw)   # remove parenthetical notes
    raw = re.sub(r"\[.*?\]", "", raw)
    parts = re.split(r"[,;]", raw)
    pre_cleaned = []
    for p in parts:
        p = p.strip().strip(".").strip()
        p = re.sub(r"^\d+\.\s*", "", p)
        if len(p) > 1:
            pre_cleaned.append(p)

    # Clean noise and normalise names
    return clean_and_normalize_ingredients(pre_cleaned)


# ── Public entry point ────────────────────────────────────────────────────────

def parse_food_label(ocr_text: str) -> dict:
    """
    Main entry point called by the packaged food route.
    Returns the same structure as before — API response format is unchanged.
    """
    logger.info("[EXTRACTOR] ===== RAW OCR TEXT (first 800 chars) =====")
    logger.info(ocr_text[:800])
    logger.info("[EXTRACTOR] ==========================================")

    nutrition   = extract_nutrition(ocr_text)
    ingredients = extract_ingredients(ocr_text)
    name        = extract_product_name(ocr_text)

    return {
        "product_name": name,
        "ingredients":  ingredients,
        "nutrition":    nutrition,
        "raw_ocr_text": ocr_text[:2000],
    }
