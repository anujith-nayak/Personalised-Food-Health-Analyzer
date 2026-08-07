"""
AI Violation Engine
====================
Converts AI dietary analysis for an "Other" health condition into
structured violation dicts that are compatible with risk_engine.py.

Design
------
- The existing Rule Engine is ALWAYS responsible for the final health score.
  The AI never sets the score directly.
- This service asks the AI two specific questions:
    1. What nutrients should be limited for this disease?
    2. What ingredients in THIS food should be avoided for this disease?
- The AI response is parsed into violation dicts with the same schema as
  _make_violation() in risk_engine.py.
- Those violations are fed directly into calculate_health_score() alongside
  any rule-engine violations — so the existing scoring algorithm applies.

Violation dict schema (identical to risk_engine._make_violation output):
    {
        condition:         str,   e.g. "GERD"
        nutrient:          str,   e.g. "caffeine"
        user_value:        float, e.g. 50.0  (mg, g, or kcal)
        threshold:         float, e.g. 0.0   (0 = avoid entirely)
        unit:              str,   e.g. "mg"
        pct_of_limit:      int,
        pct_above:         int,
        deduction:         int,   calculated by severity tier
        restriction_level: str,   "Strict" | "Moderate"
        explanation:       str,   clinical explanation from AI
        recommendation:    str,
        guideline:         str,
    }

current_health_status (other_status) is NEVER included in violations.
It is advisory only and must never affect the health score.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)

# ── Severity → deduction mapping ─────────────────────────────────────────────
# These mirror the tier system in risk_engine._compute_deduction but applied
# to qualitative AI severity labels instead of numeric ratios.
_SEVERITY_DEDUCTION: dict[str, int] = {
    "critical":  40,   # must avoid entirely — zero tolerance
    "high":      25,   # significantly harmful
    "moderate":  15,   # noticeable risk
    "low":        8,   # minor concern
}

# ── Nutrient → canonical unit ─────────────────────────────────────────────────
# Used to assign a plausible unit when the AI doesn't specify one.
_DEFAULT_UNITS: dict[str, str] = {
    "caffeine":          "mg",
    "sodium":            "mg",
    "potassium":         "mg",
    "calcium":           "mg",
    "iron":              "mg",
    "cholesterol":       "mg",
    "saturated_fat":     "g",
    "trans_fat":         "g",
    "total_fat":         "g",
    "fat":               "g",
    "sugar":             "g",
    "added_sugar":       "g",
    "carbohydrates":     "g",
    "fiber":             "g",
    "protein":           "g",
    "calories":          "kcal",
    "alcohol":           "g",
    "spicy":             "",
    "acidic":            "",
    "processed":         "",
    "fried":             "",
    "chocolate":         "g",
    "gluten":            "g",
    "lactose":           "g",
    "fructose":          "g",
    "phosphorus":        "mg",
    "magnesium":         "mg",
    "zinc":              "mg",
}

def _canonical_unit(nutrient_key: str) -> str:
    key = nutrient_key.lower().strip().replace(" ", "_")
    return _DEFAULT_UNITS.get(key, "")


# ── AI prompt: structured food analysis ───────────────────────────────────────

_VIOLATION_PROMPT = """
You are a registered clinical dietitian. A patient has the condition: {condition}

They ate or are considering eating a packaged food with these nutrients:
{nutrition_json}

The food also contains these detected ingredients:
{ingredients_list}

Your task:
1. Identify which nutrients in this specific food are harmful for {condition}.
2. Identify which detected ingredients in this food should be avoided for {condition}.
3. For each concern, assign a severity: "critical", "high", "moderate", or "low".
4. Give a brief clinical reason (1 sentence).

Return ONLY this JSON structure. No text outside the JSON block.
{{
  "nutrient_violations": [
    {{
      "nutrient": "saturated_fat",
      "severity": "high",
      "reason": "Saturated fat worsens inflammation in GERD patients.",
      "recommendation": "Limit saturated fat to under 5g per serving."
    }}
  ],
  "ingredient_violations": [
    {{
      "ingredient": "chocolate",
      "severity": "high",
      "reason": "Chocolate relaxes the lower oesophageal sphincter, worsening reflux.",
      "recommendation": "Avoid chocolate entirely for GERD."
    }}
  ],
  "guideline_source": "ACG/NHS",
  "overall_risk": "high"
}}

Rules:
- Only flag nutrients/ingredients that are genuinely problematic for {condition}.
- Use "critical" only when the item must be completely avoided.
- Do NOT fabricate nutrient values. Use only what is provided above.
- Do NOT include nutrients that are actually beneficial for {condition}.
- If a nutrient is NOT present in the food, do NOT include it.
- Respond with ONLY valid JSON. No markdown, no explanation outside JSON.
"""

_DISCLAIMER = (
    "AI-generated dietary concern. Not medical advice. "
    "Consult a qualified healthcare professional before making dietary changes."
)


# ── AI callers ────────────────────────────────────────────────────────────────

def _call_gemini_violations(prompt: str) -> dict | None:
    try:
        import google.generativeai as genai  # type: ignore
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            logger.warning("[AIViolation] GEMINI_API_KEY not set")
            return None
        genai.configure(api_key=api_key)
        model    = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        raw      = response.text.strip()
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        return json.loads(m.group() if m else raw)
    except Exception as e:
        logger.error(f"[AIViolation] Gemini failed: {e}")
        return None


def _call_openai_violations(prompt: str) -> dict | None:
    try:
        from openai import OpenAI  # type: ignore
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            logger.warning("[AIViolation] OPENAI_API_KEY not set")
            return None
        client     = OpenAI(api_key=api_key)
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Clinical dietitian. JSON only."},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.2,
        )
        raw = completion.choices[0].message.content.strip()
        m   = re.search(r"\{.*\}", raw, re.DOTALL)
        return json.loads(m.group() if m else raw)
    except Exception as e:
        logger.error(f"[AIViolation] OpenAI failed: {e}")
        return None


# ── Violation converter ───────────────────────────────────────────────────────

def _severity_to_deduction(severity: str, nutrition: dict, nutrient_key: str) -> tuple[int, str]:
    """
    Map AI severity label → deduction points + restriction_level string.
    Uses the existing tier table from risk_engine._compute_deduction.
    """
    sev   = severity.lower().strip()
    deduct = _SEVERITY_DEDUCTION.get(sev, 10)
    restr  = "Strict" if sev in ("critical", "high") else "Moderate"
    return deduct, restr


def _build_nutrient_violation(
    condition: str,
    item: dict,
    nutrition: dict,
) -> dict:
    """Convert one AI nutrient finding → risk_engine violation dict."""
    nutrient  = str(item.get("nutrient", "unknown")).lower().strip()
    severity  = str(item.get("severity", "moderate")).lower()
    reason    = str(item.get("reason", ""))
    reco      = str(item.get("recommendation", ""))
    guideline = str(item.get("guideline_source", "AI-Generated"))

    unit      = _canonical_unit(nutrient)
    # Get the actual value from the scanned food (0 if not found)
    user_val  = float(nutrition.get(nutrient, nutrition.get(nutrient.replace("_", ""), 0.0)) or 0.0)
    deduct, restr = _severity_to_deduction(severity, nutrition, nutrient)

    # threshold=0 means "avoid entirely"; positive threshold = limit
    threshold = 0.0 if severity == "critical" else user_val * 0.3  # 30% of current = safe limit

    pct_of_limit = 100 if threshold == 0 else min(round((user_val / max(threshold, 0.001)) * 100), 999)
    pct_above    = max(0, pct_of_limit - 100)

    explanation = (
        f"This food contains {user_val}{unit} of {nutrient}. "
        f"For a patient with {condition}: {reason} "
        f"Restriction level: {restr}."
    )

    return {
        "condition":         condition,
        "nutrient":          nutrient,
        "user_value":        user_val,
        "threshold":         threshold,
        "unit":              unit,
        "pct_of_limit":      pct_of_limit,
        "pct_above":         pct_above,
        "deduction":         deduct,
        "restriction_level": restr,
        "explanation":       explanation,
        "recommendation":    reco,
        "guideline":         guideline,
    }


def _build_ingredient_violation(
    condition: str,
    item: dict,
) -> dict:
    """Convert one AI ingredient finding → risk_engine violation dict."""
    ingredient = str(item.get("ingredient", "unknown"))
    severity   = str(item.get("severity", "moderate")).lower()
    reason     = str(item.get("reason", ""))
    reco       = str(item.get("recommendation", ""))

    deduct, restr = _severity_to_deduction(severity, {}, ingredient)

    explanation = (
        f"Ingredient '{ingredient}' is flagged for {condition}: {reason}"
    )

    return {
        "condition":         condition,
        "nutrient":          ingredient.lower().replace(" ", "_"),
        "user_value":        1.0,    # presence = 1 (binary flag)
        "threshold":         0.0,    # must be avoided
        "unit":              "",
        "pct_of_limit":      100,
        "pct_above":         0,
        "deduction":         deduct,
        "restriction_level": restr,
        "explanation":       explanation,
        "recommendation":    reco,
        "guideline":         "AI-Generated",
    }


# ── Public function ───────────────────────────────────────────────────────────

def get_ai_violations(
    condition: str,
    nutrition: dict,
    ingredients: list[str],
) -> tuple[list[dict], str]:
    """
    Ask AI to analyse the scanned food for the given Other condition.
    Returns (violations, overall_risk_label).

    The violations are in the exact same format as risk_engine violations,
    ready to be passed directly into calculate_health_score().

    current_health_status (other_status) is NEVER passed here.
    Only the medical condition (other_condition) is used.
    """
    if not condition or not condition.strip():
        return [], "unknown"

    condition = condition.strip()

    # Build the prompt with actual food data
    nutrition_lines = "\n".join(
        f"  {k}: {v}" for k, v in nutrition.items() if v is not None
    ) or "  (no nutrition data extracted)"

    ingredients_str = ", ".join(ingredients[:20]) if ingredients else "(none detected)"

    prompt = _VIOLATION_PROMPT.format(
        condition=condition,
        nutrition_json=nutrition_lines,
        ingredients_list=ingredients_str,
    )

    logger.info(f"[AIViolation] Querying AI for '{condition}' violations")

    # Try Gemini → OpenAI → fallback
    raw = _call_gemini_violations(prompt) or _call_openai_violations(prompt)

    if raw is None:
        logger.warning(f"[AIViolation] Both AI providers unavailable for '{condition}'")
        return [], "unknown"

    violations: list[dict] = []

    # Convert nutrient violations
    for item in raw.get("nutrient_violations", [])[:8]:
        try:
            v = _build_nutrient_violation(condition, item, nutrition)
            violations.append(v)
            logger.info(
                f"[AIViolation] Nutrient: {v['nutrient']} severity={item.get('severity')} "
                f"deduction={v['deduction']}"
            )
        except Exception as e:
            logger.warning(f"[AIViolation] Skipping malformed nutrient item: {e}")

    # Convert ingredient violations
    for item in raw.get("ingredient_violations", [])[:8]:
        try:
            v = _build_ingredient_violation(condition, item)
            violations.append(v)
            logger.info(
                f"[AIViolation] Ingredient: {item.get('ingredient')} "
                f"severity={item.get('severity')} deduction={v['deduction']}"
            )
        except Exception as e:
            logger.warning(f"[AIViolation] Skipping malformed ingredient item: {e}")

    overall_risk = str(raw.get("overall_risk", "moderate")).lower()
    logger.info(
        f"[AIViolation] '{condition}': {len(violations)} violations, "
        f"overall_risk={overall_risk}"
    )

    return violations, overall_risk


# ── Part 6: Deduplication ─────────────────────────────────────────────────────
# Sugar / Added Sugar / Sugar Syrup must not triple-penalise the same thing.
# We group them by a normalised nutrient key and keep only the worst deduction.

_DEDUP_GROUPS: list[frozenset[str]] = [
    # Sugar family
    frozenset({"sugar", "added_sugar", "total_sugars", "invert_sugar_syrup",
                "sugar_syrup", "glucose_syrup", "corn_syrup", "high_fructose_corn_syrup",
                "dextrose", "fructose", "sucrose"}),
    # Fat family
    frozenset({"total_fat", "fat", "saturated_fat", "trans_fat",
                "hydrogenated_vegetable_fat", "palm_oil", "palm_olein",
                "vegetable_shortening"}),
    # Flour family
    frozenset({"refined_wheat_flour", "maida", "wheat_flour", "enriched_flour",
                "refined_flour", "all_purpose_flour"}),
    # Sodium / salt family
    frozenset({"sodium", "salt", "iodised_salt", "sea_salt", "table_salt"}),
]

def _group_key(nutrient: str) -> str:
    """Return the group representative for a nutrient (for dedup purposes)."""
    n = nutrient.lower().replace(" ", "_")
    for group in _DEDUP_GROUPS:
        if n in group:
            return min(group)   # use alphabetically first as canonical group key
    return n


def deduplicate_violations(violations: list[dict]) -> list[dict]:
    """
    Part 6: Remove duplicate violations.
    For each (condition, nutrient_group) pair, keep only the violation
    with the HIGHEST deduction so the user is penalised once per risk group.
    """
    best: dict[tuple[str, str], dict] = {}

    for v in violations:
        cond    = v.get("condition", "").lower()
        nutrient = v.get("nutrient", "")
        gkey    = _group_key(nutrient)
        key     = (cond, gkey)

        if key not in best or v["deduction"] > best[key]["deduction"]:
            best[key] = v

    deduped = list(best.values())
    removed = len(violations) - len(deduped)
    if removed > 0:
        logger.info(f"[Dedup] Removed {removed} duplicate violations, {len(deduped)} remain")

    return deduped


# ── Part 3 & 7: Per-ingredient risk analysis for ALL conditions ───────────────
# This runs regardless of whether the user has an "Other" condition.
# It analyses every extracted ingredient against the user's actual conditions
# and flags harmful ones — improving disease risk display (Part 7).

_INGREDIENT_ANALYSIS_PROMPT = """
You are a registered clinical dietitian.

A patient has these health conditions: {conditions}

A packaged food product contains these ingredients:
{ingredients_list}

For each ingredient that is harmful for any of the patient's conditions:
1. Name the ingredient exactly as listed.
2. List which conditions it affects.
3. Assign severity: "critical", "high", "moderate", or "low".
4. Give a 1-sentence clinical explanation.
5. Give a brief recommendation.

Return ONLY this JSON. No text outside the JSON.
{{
  "ingredient_risks": [
    {{
      "ingredient": "Palm Oil",
      "conditions": ["Heart Disease", "Obesity", "Fatty Liver"],
      "severity": "high",
      "reason": "Palm oil is high in saturated fat which raises LDL cholesterol and promotes liver fat accumulation.",
      "recommendation": "Avoid regular consumption. Choose olive oil or sunflower oil instead."
    }}
  ]
}}

Rules:
- Only include ingredients that are genuinely harmful for the listed conditions.
- Skip ingredients that are neutral or beneficial (e.g. fiber, vitamins, water).
- Be concise — 1-sentence reasons only.
- Respond with ONLY valid JSON.
"""


def analyse_ingredients_for_conditions(
    ingredients: list[str],
    conditions: list[str],
) -> list[dict]:
    """
    Part 3 & 7: Ask AI to analyse every extracted ingredient against the user's
    actual health conditions, returning per-ingredient risk data.

    Returns list of:
    {
        ingredient: str,
        conditions: list[str],
        severity:   str,
        reason:     str,
        recommendation: str,
    }

    Used to:
    - Build ingredient-level violations for the health score (Part 4)
    - Improve disease analysis display (Part 7)
    - Generate Part 8 explanations
    """
    if not ingredients or not conditions:
        return []

    # Filter out conditions that are implied (don't add noise to prompt)
    display_conditions = [c for c in conditions
                          if c not in ("Hypertension", "Heart Disease")
                          or c in conditions]

    ingredients_str = "\n".join(f"- {i}" for i in ingredients[:25])
    conditions_str  = ", ".join(display_conditions[:8])

    prompt = _INGREDIENT_ANALYSIS_PROMPT.format(
        conditions=conditions_str,
        ingredients_list=ingredients_str,
    )

    logger.info(f"[IngredientAnalysis] Analysing {len(ingredients)} ingredients "
                f"for conditions: {conditions_str}")

    raw = _call_gemini_violations(prompt) or _call_openai_violations(prompt)

    if raw is None:
        logger.warning("[IngredientAnalysis] AI unavailable — skipping ingredient analysis")
        return []

    results = []
    for item in raw.get("ingredient_risks", [])[:15]:
        try:
            results.append({
                "ingredient":     str(item.get("ingredient", "")).strip(),
                "conditions":     list(item.get("conditions", [])),
                "severity":       str(item.get("severity", "moderate")).lower(),
                "reason":         str(item.get("reason", "")),
                "recommendation": str(item.get("recommendation", "")),
            })
        except Exception as e:
            logger.warning(f"[IngredientAnalysis] Skipping malformed item: {e}")

    logger.info(f"[IngredientAnalysis] Found {len(results)} harmful ingredients")
    return results


def ingredient_risks_to_violations(
    ingredient_risks: list[dict],
) -> list[dict]:
    """
    Part 4: Convert per-ingredient AI risk findings into rule-engine
    violation dicts — one violation per (condition, ingredient) pair.
    These are merged with rule-engine violations for final score calculation.
    """
    violations: list[dict] = []

    for risk in ingredient_risks:
        ingredient = risk.get("ingredient", "unknown")
        severity   = risk.get("severity", "moderate")
        reason     = risk.get("reason", "")
        reco       = risk.get("recommendation", "")
        affected   = risk.get("conditions", ["General"])

        for condition in affected:
            deduct, restr = _severity_to_deduction(severity, {}, ingredient)
            ing_key       = ingredient.lower().replace(" ", "_")

            violations.append({
                "condition":         condition,
                "nutrient":          ing_key,
                "user_value":        1.0,    # binary — ingredient is present
                "threshold":         0.0,    # should be avoided
                "unit":              "",
                "pct_of_limit":      100,
                "pct_above":         0,
                "deduction":         deduct,
                "restriction_level": restr,
                "explanation":       (
                    f"Ingredient '{ingredient}' flagged for {condition}. "
                    f"{reason}"
                ),
                "recommendation":    reco,
                "guideline":         "AI-Generated (Ingredient Analysis)",
            })

    return violations


# ── Part 9: Enhanced final recommendation ────────────────────────────────────

def build_ingredient_recommendation(
    ingredient_risks: list[dict],
    conditions: list[str],
    score: int,
) -> str:
    """
    Part 9: Build a recommendation paragraph that combines ingredient
    analysis findings with condition context.
    Returns empty string if no harmful ingredients found.
    """
    if not ingredient_risks:
        return ""

    # Group by severity
    critical = [r for r in ingredient_risks if r["severity"] == "critical"]
    high     = [r for r in ingredient_risks if r["severity"] == "high"]
    mod      = [r for r in ingredient_risks if r["severity"] == "moderate"]

    dangerous_ings = [r["ingredient"] for r in (critical + high)[:4]]
    conditions_str = " and ".join(conditions[:3]) if conditions else "your health conditions"

    if not dangerous_ings:
        if mod:
            mod_ings = [r["ingredient"] for r in mod[:3]]
            return (
                f"This product contains {', '.join(mod_ings)} which may have moderate "
                f"dietary concerns for {conditions_str}. Consume occasionally and in small portions."
            )
        return ""

    # Get the top reason
    top_reason = ""
    if critical:
        top_reason = critical[0].get("reason", "")
    elif high:
        top_reason = high[0].get("reason", "")

    verdict = (
        "Avoid completely." if score < 40
        else "Limit consumption." if score < 60
        else "Consume occasionally and in small portions."
    )

    return (
        f"This product contains {', '.join(dangerous_ings)}. "
        f"These ingredients are not recommended for patients with {conditions_str} "
        f"because {top_reason.lower().rstrip('.')}. "
        f"{verdict}"
    )


# ── Part 10: Score floor when only ingredients are available ──────────────────

def apply_ingredient_score_floor(
    health_score: int,
    ingredient_risks: list[dict],
) -> int:
    """
    Part 10: If OCR extracted no nutrition facts but harmful ingredients
    were found, ensure the score reflects the ingredient risk.
    Prevents foods from being classified "Safe" just because nutrition
    values were not extracted.

    Only lowers the score — never raises it.
    """
    if not ingredient_risks:
        return health_score

    critical_count = sum(1 for r in ingredient_risks if r["severity"] == "critical")
    high_count     = sum(1 for r in ingredient_risks if r["severity"] == "high")
    mod_count      = sum(1 for r in ingredient_risks if r["severity"] == "moderate")

    # Determine the floor based on what we found
    if critical_count >= 2:
        floor = 25   # Dangerous
    elif critical_count == 1:
        floor = 35   # High Risk
    elif high_count >= 2:
        floor = 45   # Moderate Risk
    elif high_count == 1:
        floor = 55   # Moderate Risk
    elif mod_count >= 2:
        floor = 65   # Occasional Use
    else:
        floor = 75   # Mild concern only

    if health_score > floor:
        logger.info(
            f"[ScoreFloor] Score {health_score} → {floor} "
            f"(ingredient risk: {critical_count} critical, {high_count} high, {mod_count} moderate)"
        )
        return floor

    return health_score
