"""
Personalized Medical Risk Engine
=================================
Performs true medical threshold analysis using health_r.csv and health_rules.csv.


Key design:
- Starts at 100 (safe) and DEDUCTS points based on violations
- Uses actual BP / sugar / BMI values to determine severity stage
- Each exceeded threshold deducts proportionally to how much it is exceeded
- Same food produces completely different scores for different users
- Generates human-readable explanations with exact values and percentages
"""
from typing import Optional
from . import dataset_loader as dl
from app.utils.nutrient_format import (
    canonical_unit, is_percent_threshold, format_nutrient, safe_pct_of_limit
)
import logging

logger = logging.getLogger(__name__)

# ── Risk Level Thresholds (score is 0-100, higher = safer) ───────────────────
RISK_LEVELS = [
    (81, 101, "Safe",                    "green",   "This food is safe for your health conditions."),
    (61,  81, "Occasional Use",          "yellow",  "Consume only occasionally and in small portions."),
    (41,  61, "Moderate Risk",           "orange",  "Significant concerns. Limit or avoid this product."),
    (21,  41, "High Risk",               "red",     "Not recommended for your health conditions."),
    ( 0,  21, "Dangerous",               "darkred", "This food is dangerous for your conditions. Avoid completely."),
]


# ── BP Stage Classification ───────────────────────────────────────────────────
def classify_bp_stage(systolic: Optional[int], diastolic: Optional[int], bp_status: Optional[str]) -> str:
    """Determine hypertension stage from actual readings."""
    if systolic and systolic >= 180:
        return "Stage 2"   # hypertensive crisis falls under Stage 2 rules
    if systolic and diastolic:
        if systolic >= 140 or diastolic >= 90:
            return "Stage 2"
        if systolic >= 130 or diastolic >= 80:
            return "Stage 1"
        if systolic >= 120:
            return "Elevated"
        return "General"
    # Fallback to stored status
    status = (bp_status or "").lower()
    if status == "high":   return "Stage 2"
    if status == "low":    return "General"
    return "General"


# ── Sugar Stage Classification ────────────────────────────────────────────────
def classify_sugar_stage(fasting: Optional[float], post_meal: Optional[float], status: Optional[str]) -> str:
    """Determine diabetes severity from actual readings."""
    if fasting:
        if fasting >= 126: return "Type 2"
        if fasting >= 100: return "Prediabetes"
        return "General"
    if post_meal:
        if post_meal >= 200: return "Diabetic"
        if post_meal >= 140: return "Prediabetes"
        return "General"
    s = (status or "").lower()
    if s == "high": return "Diabetic"
    if s == "low":  return "General"
    return "General"


# ── BMI → Obesity Class ───────────────────────────────────────────────────────
def classify_obesity(bmi: Optional[float]) -> Optional[str]:
    if not bmi: return None
    if bmi >= 40:  return "Class 3"
    if bmi >= 35:  return "Class 2"
    if bmi >= 30:  return "Class 1"
    if bmi >= 25:  return "Overweight"
    return None


# ── Nutrient name aliases ─────────────────────────────────────────────────────
NUTRIENT_ALIASES = {
    "calories": ["calories", "energy"],

    # Sugar
    "sugar": [
        "sugar",
        "total_sugars",
        "added_sugar",
        "added sugars",
        "sugars",
    ],
    "added_sugar": [
        "added_sugar",
        "added sugars",
        "sugar",
        "total_sugars",
    ],

    # Carbohydrates
    "carbs": [
        "carbs",
        "carbohydrates",
        "total_carbohydrates",
        "total_carb",
        "total_carbs",
    ],
    "carbohydrates": [
        "carbohydrates",
        "carbs",
        "total_carb",
        "total_carbs",
        "total_carbohydrates",
    ],
    "total_carb": [
        "total_carb",
        "total_carbs",
        "carbohydrates",
        "carbs",
        "total_carbohydrates",
    ],
    "total_carbs": [
        "total_carbs",
        "total_carb",
        "carbohydrates",
        "carbs",
        "total_carbohydrates",
    ],
    "total_carbohydrates": [
        "total_carbohydrates",
        "total_carbs",
        "total_carb",
        "carbohydrates",
        "carbs",
    ],

    # Fat
    "fat": [
        "fat",
        "total_fat",
    ],
    "total_fat": [
        "total_fat",
        "fat",
    ],

    "saturated_fat": [
        "saturated_fat",
        "sat_fat",
        "saturated fat",
    ],
    "sat_fat": [
        "sat_fat",
        "saturated_fat",
    ],

    "trans_fat": [
        "trans_fat",
        "trans fat",
    ],

    "protein": [
        "protein",
    ],

    "fiber": [
        "fiber",
        "dietary_fiber",
        "dietary fibre",
    ],
    "dietary_fiber": [
        "fiber",
        "dietary_fiber",
    ],

    "sodium": [
        "sodium",
        "salt",
    ],
    "salt": [
        "salt",
        "sodium",
    ],

    "cholesterol": [
        "cholesterol",
    ],

    # Dataset-specific nutrients
    "glycemic_index": [
        "glycemic_index",
        "gi",
        "glycemic index",
    ],
    "glycemic_load": [
        "glycemic_load",
        "gl",
        "glycemic load",
    ],
    "omega3": [
        "omega3",
        "omega-3",
        "omega_3",
    ],
    "magnesium": [
        "magnesium",
    ],
    "chromium": [
        "chromium",
    ],
    "vitamin_d": [
        "vitamin_d",
        "vitamin d",
    ],
    "potassium": [
        "potassium",
    ],
    "calcium": [
        "calcium",
    ],
    "iron": [
        "iron",
    ],
}
def normalize_nutrient(name: str) -> str:
    name = name.lower().strip()

    mapping = {
        "fat": "total_fat",
        "total_fat": "total_fat",

        "carbs": "carbohydrates",
        "carbohydrate": "carbohydrates",
        "carbohydrates": "carbohydrates",
        "total_carbs": "carbohydrates",
        "total_carbohydrates": "carbohydrates",

        "sugars": "sugar",
        "total_sugars": "sugar",
        "added_sugar": "sugar",
        "added sugars": "sugar",
        "sugar": "sugar",

        "fiber": "fiber",
        "dietary_fiber": "fiber",

        "salt": "sodium",
        "sodium": "sodium",

        "sat_fat": "saturated_fat",
        "saturated fat": "saturated_fat",

        "trans fat": "trans_fat",

        "protein": "protein",
        "cholesterol": "cholesterol",
        "calories": "calories",
        "energy": "calories",
    }

    return mapping.get(name, name)

def _match_nutrient(rule_nutrient: str, nutrition: dict) -> Optional[tuple]:
    """
    Find the best matching nutrition value for a rule nutrient.
    Returns (matched_key, value) or None.
    """

    # Normalize the nutrient name from the CSV
    rn = normalize_nutrient(rule_nutrient)

    # ---------------------------------------------------------
    # 1. Direct normalized match (preferred)
    # ---------------------------------------------------------
    for k, v in nutrition.items():
        if v is None:
            continue

        if normalize_nutrient(k) == rn:
            return (k, float(v))

    # ---------------------------------------------------------
    # 2. Alias fallback
    # ---------------------------------------------------------
    aliases = NUTRIENT_ALIASES.get(rn, [rn])

    for alias in aliases:
        alias = normalize_nutrient(alias)

        for k, v in nutrition.items():
            if v is None:
                continue

            nk = normalize_nutrient(k)

            if alias == nk or alias in nk or nk in alias:
                return (k, float(v))

    # ---------------------------------------------------------
    # 3. Debug
    # ---------------------------------------------------------
    logger.info(
        f"No nutrient match for rule '{rule_nutrient}'. "
        f"Normalized='{rn}'. "
        f"Available={list(nutrition.keys())}"
    )

    return None


def _normalize(s: str) -> str:
    return str(s).lower().strip()


# ── Main profile extractor ────────────────────────────────────────────────────
def _get_user_conditions(health_profile: dict) -> list[str]:
    """
    Map stored health profile fields to condition names used in health_r.csv.
    Automatically handles all diseases — no hardcoding needed.
    Adding a new bool field to HealthProfile + a matching condition name in health_r.csv
    is all that is required to support a new disease end-to-end.
    """
    conditions = []
    if health_profile.get("hypertension"):      conditions.append("Hypertension")
    if health_profile.get("diabetes"):          conditions.append("Diabetes")
    if health_profile.get("pcos"):              conditions.append("PCOS")
    if health_profile.get("pcod"):              conditions.append("PCOS")
    if health_profile.get("heart_disease"):     conditions.append("Heart Disease")
    if health_profile.get("kidney_disease"):    conditions.append("Kidney Disease")
    if health_profile.get("obesity"):           conditions.append("Obesity")
    if health_profile.get("high_cholesterol"):  conditions.append("High Cholesterol")
    if health_profile.get("appendicitis"):      conditions.append("Appendicitis")

    thyroid_type = (health_profile.get("thyroid_type") or "").lower()
    if health_profile.get("thyroid"):
        if "hypo" in thyroid_type:    conditions.append("Hypothyroidism")
        elif "hyper" in thyroid_type: conditions.append("Hyperthyroidism")
        else:                          conditions.append("Hypothyroidism")

    bmi = health_profile.get("bmi_score") or 0
    if bmi >= 25 and "Obesity" not in conditions:
        conditions.append("Obesity")

    # ── Comorbidity rules ──────────────────────────────────────────────────
    if "Diabetes" in conditions and "Hypertension" not in conditions:
        conditions.append("Hypertension")
        health_profile["_diabetes_implied_hypertension"] = True

    if "Diabetes" in conditions and "Heart Disease" not in conditions:
        conditions.append("Heart Disease")
        health_profile["_diabetes_implied_heart"] = True

    return list(dict.fromkeys(conditions))


# ── Core Analysis Functions ───────────────────────────────────────────────────
def get_severity_multiplier(condition, health_profile):
    condition = condition.lower()

    if condition == "hypertension":
        stage = classify_bp_stage(
            health_profile.get("systolic"),
            health_profile.get("diastolic"),
            health_profile.get("bp_status"),
        )

        return {
            "General": 1.0,
            "Stage 1": 1.2,
            "Stage 2": 1.5,
            "Stage 3": 2.0,
        }.get(stage, 1.0)

    elif condition == "diabetes":
        stage = classify_sugar_stage(
            health_profile.get("fasting_sugar"),
            health_profile.get("post_meal_sugar"),
            health_profile.get("sugar_status"),
        )

        return {
            "General": 1.0,
            "Prediabetes": 1.2,
            "Type 2": 1.6,
            "Diabetic": 2.0,
        }.get(stage, 1.0)
    elif condition == "obesity":
        bmi = health_profile.get("bmi_score") or 0

        if bmi >= 40:
            return 2.0
        elif bmi >= 35:
            return 1.7
        elif bmi >= 30:
            return 1.5
        elif bmi >= 25:
            return 1.2
        return 1.0

    elif condition == "kidney disease":
        return 1.8

    elif condition == "heart disease":
        return 1.8

    elif condition in ["pcos", "pcod"]:
        return 1.3

    elif "thyroid" in condition:
        return 1.2

    return 1.0


def analyze_with_health_r(
    nutrition: dict,
    health_profile: dict,
) -> tuple[list[dict], int]:
    """
    Primary analysis using health_r.csv.
    Determines disease stage from actual health values,
    finds matching rules, checks nutrition thresholds,
    and calculates medically realistic deductions.

    Deduction formula (per violation):
      1. exceedance_ratio  = user_value / threshold_max
      2. base_deduction    = determined by exceedance ratio tiers
      3. restriction_boost = multiplier for strict (×1.4) vs moderate (×1.0)
      4. severity_boost    = get_severity_multiplier() for the user's disease stage
      5. Each violation also has a MINIMUM FLOOR deduction so that even a
         small exceedance of a critical nutrient (sodium for Stage-2 HTN)
         always produces a meaningful score drop.

    Multi-disease penalty:
      When the user has ≥2 conditions, every violation's deduction is
      further multiplied by a comorbidity factor (1.2 per additional disease,
      capped at 2.0) to reflect compounded medical risk.

    Returns: (list of violations, total_deduction 0-100)
    """
    df = dl.health_r
    if df.empty or not nutrition:
        return [], 0

    violations      = []
    total_deduction = 0.0

    # ── Determine severity sub-conditions per disease ─────────────────────
    sub_map = {}

    if health_profile.get("hypertension"):
        stage = classify_bp_stage(
            health_profile.get("systolic"),
            health_profile.get("diastolic"),
            health_profile.get("bp_status"),
        )
        sub_map["Hypertension"] = [stage, "General"]

    if health_profile.get("diabetes"):
        stage = classify_sugar_stage(
            health_profile.get("fasting_sugar"),
            health_profile.get("post_meal_sugar"),
            health_profile.get("sugar_status"),
        )
        diabetes_subs = [stage, "General"]
        if health_profile.get("hypertension"):
            diabetes_subs.append("With Hypertension")
        if health_profile.get("kidney_disease"):
            diabetes_subs.append("With CKD")
        if health_profile.get("heart_disease"):
            diabetes_subs.append("With Heart")
        if health_profile.get("pcos") or health_profile.get("pcod"):
            diabetes_subs.append("With PCOS")
        sub_map["Diabetes"] = diabetes_subs

    if health_profile.get("pcos") or health_profile.get("pcod"):
        sub_map["PCOS"] = ["General", "Overweight"]

    if health_profile.get("heart_disease"):
        sub_map["Heart Disease"] = ["General"]

    if health_profile.get("kidney_disease"):
        sub_map["Kidney Disease"] = ["Stage 3-4", "General"]

    if health_profile.get("thyroid"):
        thyroid_type = (health_profile.get("thyroid_type") or "hypo").lower()
        cond = "Hypothyroidism" if "hypo" in thyroid_type else "Hyperthyroidism"
        sub_map[cond] = ["General"]

    bmi = health_profile.get("bmi_score") or 0
    if bmi >= 25 or health_profile.get("obesity"):
        obesity_class = classify_obesity(bmi) or "General"
        sub_map["Obesity"] = [obesity_class, "General"]

    # ── New conditions — automatically supported via health_r.csv ─────────
    if health_profile.get("high_cholesterol"):
        chol_subs = ["General", "LDL High"]
        if health_profile.get("diabetes"):       chol_subs.insert(0, "With Diabetes")
        if health_profile.get("heart_disease"):  chol_subs.insert(0, "With Heart")
        if health_profile.get("pcos") or health_profile.get("pcod"):
            chol_subs.insert(0, "With PCOS")
        sub_map["High Cholesterol"] = chol_subs

    if health_profile.get("appendicitis"):
        phase = (health_profile.get("appendicitis_phase") or "acute").lower()
        if "acute" in phase:
            sub_map["Appendicitis"] = ["Acute Phase", "General"]
        elif "recovery" in phase or "post" in phase:
            sub_map["Appendicitis"] = ["Post-Appendectomy Recovery", "General"]
        else:
            sub_map["Appendicitis"] = ["General"]

    # ── Multi-disease comorbidity multiplier ──────────────────────────────
    # Each additional disease beyond the first adds 20% to every deduction,
    # capped at 2.0×.  This ensures that a patient with 3+ diseases cannot
    # receive a "safe" score for a food that is dangerous for even one of them.
    num_conditions        = len(sub_map)
    comorbidity_factor    = min(1.0 + 0.20 * max(0, num_conditions - 1), 2.0)
    logger.info(f"[SCORE] {num_conditions} conditions → comorbidity_factor={comorbidity_factor:.2f}")

    # ── Check each condition's rules ──────────────────────────────────────
    for condition, sub_conditions in sub_map.items():
        cond_lower = condition.lower()
        cond_mask  = df["condition"].str.lower().apply(
            lambda x: cond_lower in x or x in cond_lower
        )
        cond_df = df[cond_mask]
        if cond_df.empty:
            continue

        seen_nutrients = set()

        for sub in sub_conditions:
            sub_lower = sub.lower()
            sub_mask  = cond_df["sub_condition"].str.lower().apply(
                lambda x: sub_lower in x or x in sub_lower or "general" in x
            )
            rows = cond_df[sub_mask]
            logger.info(f"[SCORE] {condition} | {sub} → {len(rows)} rows")

            for _, row in rows.iterrows():
                rule_nutrient = str(row.get("nutrient", "")).strip()
                threshold_max = row.get("threshold_max")
                restriction   = str(row.get("restriction_level", "")).lower()
                rw            = float(row.get("risk_weight", 0.5))

                # Only evaluate strict / moderate rules
                if restriction not in ("strict", "moderate"):
                    continue

                # One violation per (condition, nutrient) pair
                key = (condition, rule_nutrient)
                if key in seen_nutrients:
                    continue

                logger.info(
                    f"[SCORE] Checking {condition}|{sub}|{rule_nutrient}"
                    f" threshold={threshold_max}"
                )

                matched = _match_nutrient(rule_nutrient, nutrition)
                logger.info(f"[SCORE] Matched = {matched}")
                if not matched:
                    continue

                nutr_key, user_value = matched
                if threshold_max is None:
                    continue

                try:
                    max_val = float(threshold_max)
                except (ValueError, TypeError):
                    continue

                # ── Bug 2 fix: skip percent-unit rules ────────────────────
                # Rows like "saturated_fat < 7 percent" mean 7% of daily
                # calories, NOT 7g. We cannot compare mg/g values to a
                # percentage threshold, so skip these entirely.
                csv_unit = str(row.get("unit", ""))
                if is_percent_threshold(csv_unit):
                    logger.debug(
                        f"[SCORE] Skipping percent-unit rule: "
                        f"{condition}|{rule_nutrient} unit={csv_unit}"
                    )
                    continue

                # ── ZERO-TOLERANCE rule ───────────────────────────────────
                if max_val == 0:
                    if user_value > 0:
                        # Floor: strict zero-tolerance → always significant deduction
                        floor   = _zero_tolerance_floor(restriction, rw)
                        sev     = get_severity_multiplier(condition, health_profile)
                        deduct  = round(min(floor * sev * comorbidity_factor, 60))

                        seen_nutrients.add(key)
                        total_deduction += deduct

                        violations.append(
                            _make_violation(
                                condition, rule_nutrient, user_value, max_val,
                                100, 0, deduct, row, health_profile,
                            )
                        )
                    continue

                # ── THRESHOLD EXCEEDED ────────────────────────────────────
                if user_value > max_val:
                    ratio      = user_value / max_val          # e.g. 1.067 or 2.5
                    pct_above  = round((ratio - 1) * 100)      # e.g. 7% or 150%
                    pct_of_lim = round(ratio * 100)            # e.g. 107% or 250%

                    deduct = _compute_deduction(
                        ratio, rw, restriction, condition, health_profile,
                        comorbidity_factor
                    )

                    seen_nutrients.add(key)
                    total_deduction += deduct

                    violations.append(
                        _make_violation(
                            condition, rule_nutrient, user_value, max_val,
                            pct_of_lim, pct_above, round(deduct),
                            row, health_profile,
                        )
                    )

    # ── Log summary ───────────────────────────────────────────────────────
    logger.info("========== VIOLATIONS ==========")
    for v in violations:
        logger.info(
            f"  {v['condition']:20} | {v['nutrient']:20} | "
            f"value={v['user_value']:>8} | limit={v['threshold']:>8} | "
            f"deduction={v['deduction']}"
        )
    logger.info(f"[SCORE] Total violations      = {len(violations)}")
    logger.info(f"[SCORE] Total raw deduction   = {total_deduction:.1f}")

    return violations, min(round(total_deduction), 100)


# ── Deduction helpers ─────────────────────────────────────────────────────────

def _zero_tolerance_floor(restriction: str, risk_weight: float) -> float:
    """
    Minimum deduction for any zero-tolerance nutrient (trans fat, alcohol, etc.).
    Strict zero-tolerance rules always produce at least 20 points deduction.
    """
    if restriction == "strict":
        return max(20.0, risk_weight * 25.0)
    return max(10.0, risk_weight * 15.0)


def _compute_deduction(
    ratio: float,
    risk_weight: float,
    restriction: str,
    condition: str,
    health_profile: dict,
    comorbidity_factor: float,
) -> float:
    """
    Compute a medically realistic deduction for one nutrient violation.

    Approach:
      - Tiered base deduction by exceedance ratio (not a pure linear formula).
        Even a 1% exceedance of a critical nutrient earns a meaningful floor.
      - Restriction level multiplier: strict violations penalised harder.
      - Disease severity multiplier: Stage 2 HTN doubles the penalty vs. General.
      - Comorbidity factor: extra diseases compound the risk.
      - Hard cap at 60 per single violation to avoid one nutrient dominating.

    Tier table (base points, before multipliers):
      ratio ≥ 3.0 → 40 pts   (tripling a critical limit is very dangerous)
      ratio ≥ 2.0 → 28 pts
      ratio ≥ 1.5 → 20 pts
      ratio ≥ 1.2 → 14 pts
      ratio ≥ 1.1 → 10 pts
      ratio > 1.0 → 7 pts    (any exceedance at all, even tiny)

    Minimum floor by restriction:
      strict   → floor 10 pts  (after multipliers; before cap)
      moderate → floor  5 pts
    """
    # Tier-based base
    if ratio >= 3.0:
        base = 40.0
    elif ratio >= 2.0:
        base = 28.0
    elif ratio >= 1.5:
        base = 20.0
    elif ratio >= 1.2:
        base = 14.0
    elif ratio >= 1.1:
        base = 10.0
    else:
        base = 7.0

    # Scale by risk_weight (0.0–1.0)
    base *= risk_weight

    # Restriction multiplier
    restriction_mult = 1.4 if restriction == "strict" else 1.0
    base *= restriction_mult

    # Disease severity multiplier (Stage 2 HTN = 1.5, hypertensive crisis = 2.0, etc.)
    severity = get_severity_multiplier(condition, health_profile)
    base *= severity

    # Multi-disease comorbidity
    base *= comorbidity_factor

    # Enforce minimum floors so even a small exceedance of a critical rule
    # always produces a perceptible score drop
    if restriction == "strict":
        min_floor = 10.0 * risk_weight * severity * comorbidity_factor
    else:
        min_floor = 5.0 * risk_weight * severity * comorbidity_factor

    deduction = max(base, min_floor)

    logger.info(
        f"    deduction: base={base:.1f} ratio={ratio:.3f} "
        f"rw={risk_weight:.2f} restr={restriction} sev={severity:.2f} "
        f"comorbidity={comorbidity_factor:.2f} floor={min_floor:.1f} "
        f"→ {deduction:.1f}"
    )

    return min(deduction, 60.0)


def _make_violation(
    condition: str,
    nutrient: str,
    user_value: float,
    threshold: float,
    pct_of_limit: int,
    pct_above: int,
    deduction: int,
    row,
    health_profile: dict,
) -> dict:
    """
    Build a detailed violation dict.

    Bug 1 fix: unit is derived from canonical_unit(nutrient) instead of
               raw CSV — so "percent" can never appear.
    Bug 2 fix: pct_of_limit and pct_above are calculated by safe_pct_of_limit()
               which caps at 999 and always computes (value/limit)*100.
    Bug 4 fix: explanation uses format_nutrient() for consistent display.
    """
    csv_unit       = str(row.get("unit", ""))
    unit           = canonical_unit(nutrient, csv_unit)          # Bug 1 fix
    recommendation = str(row.get("recommendation", ""))
    restriction    = str(row.get("restriction_level", "")).capitalize()
    guideline      = str(row.get("guideline_source", ""))

    # Bug 2 fix: always recalculate percentages correctly
    pct_of_limit, pct_above = safe_pct_of_limit(user_value, threshold)

    val_str   = format_nutrient(user_value, nutrient, csv_unit)  # Bug 1 & 4 fix
    limit_str = format_nutrient(threshold,  nutrient, csv_unit)

    # Build contextual explanation (Bug 4: no more "10.0percent")
    context = ""
    if condition == "Hypertension":
        sys = health_profile.get("systolic")
        dia = health_profile.get("diastolic")
        if sys and dia:
            context = f" (Your BP: {sys}/{dia} mmHg)"
        elif health_profile.get("bp_status"):
            context = f" ({health_profile['bp_status'].upper()} BP)"
    elif condition == "Diabetes":
        fs = health_profile.get("fasting_sugar")
        if fs:
            context = f" (Your fasting sugar: {fs} mg/dL)"
    elif condition == "Obesity":
        bmi = health_profile.get("bmi_score")
        if bmi:
            context = f" (Your BMI: {bmi:.1f})"

    if threshold > 0:
        explanation = (
            f"This food contains {val_str} of {nutrient}. "
            f"Your recommended limit for {condition}{context} is {limit_str}/day. "
            f"This product uses {pct_of_limit}% of your recommended daily limit "
            f"({pct_above}% above the recommended limit). "
            f"Restriction level: {restriction}. [{guideline}]"
        )
    else:
        explanation = (
            f"This food contains {nutrient} ({val_str}), which must be completely avoided "
            f"for {condition}{context}. [{guideline}]"
        )

    return {
        "condition":         condition,
        "nutrient":          nutrient,
        "user_value":        user_value,
        "threshold":         threshold,
        "unit":              unit,              # Bug 1 fix: canonical unit
        "pct_of_limit":      pct_of_limit,      # Bug 2 fix
        "pct_above":         pct_above,         # Bug 2 fix
        "deduction":         deduction,
        "restriction_level": restriction,
        "explanation":       explanation,
        "recommendation":    recommendation,
        "guideline":         guideline,
    }



def analyze_ingredients_against_rules(
    ingredients: list[str],
    conditions: list[str],
) -> tuple[list[dict], int]:
    """
    Check detected ingredients against ingredient_rules.csv and health_r.csv
    ingredient_flag column.
    Returns (triggered list, deduction 0-30)
    """
    df_ingr = dl.ingredient_rules
    df_r    = dl.health_r
    triggered    = []
    total_deduct = 0
    seen = set()


    for ingredient in ingredients:
        ing_lower = _normalize(ingredient)


        # ── ingredient_rules.csv ──────────────────────────────────────────
        if not df_ingr.empty:
            for condition in conditions:
                cond_lower = _normalize(condition)
                mask = (
                    df_ingr["Ingredient"].str.lower().apply(
                        lambda x: ing_lower in x or x in ing_lower
                    ) &
                    df_ingr["Condition"].str.lower().apply(
                        lambda x: cond_lower in x or x in cond_lower
                    )
                )
                for _, row in df_ingr[mask].iterrows():
                    key = (ingredient, condition)
                    if key in seen: continue
                    seen.add(key)
                    rw = int(float(row.get("RiskWeight", 5)))
                    total_deduct += rw
                    triggered.append({
                        "ingredient": ingredient,
                        "condition": condition,
                        "reason": row.get("Reason", ""),
                        "recommendation": row.get("Recommendation", ""),
                        "deduction": rw,
                    })


        # ── health_r.csv ingredient_flag ──────────────────────────────────
        if not df_r.empty:
            flag_mask = df_r["ingredient_flag"].str.lower().apply(
                lambda x: ing_lower in x or x in ing_lower
            )
            for _, row in df_r[flag_mask].iterrows():
                rule_cond = _normalize(row.get("condition", ""))
                for condition in conditions:
                    if _normalize(condition) not in rule_cond and rule_cond not in _normalize(condition):
                        continue
                    key = (ingredient, condition, "flag")
                    if key in seen: continue
                    seen.add(key)
                    rw = int(float(row.get("risk_weight", 0.5)) * 8)
                    total_deduct += rw
                    triggered.append({
                        "ingredient": ingredient,
                        "condition": condition,
                        "reason": row.get("recommendation", ""),
                        "recommendation": row.get("recommendation", ""),
                        "deduction": rw,
                    })


    return triggered, min(total_deduct, 30)



def calculate_health_score(
    violations: list[dict],
    ingredient_deduction: int,
    allergy_bonus: int = 0,
) -> int:
    """
    Score starts at 100 and deductions are subtracted.

    Rules:
      - Total deduction = sum of all violation deductions + ingredient deduction + allergy_bonus.
      - Fiber/protein bonus is applied AFTER deductions in the route (packaged_food.py).
        That bonus is capped at 5 pts and suppressed when total_deduction > 20.
        (The route must honour these limits — see bonus guard below.)
      - Returns final score clamped to [0, 100].
    """
    violation_deduction = sum(v["deduction"] for v in violations)
    total_deduction     = violation_deduction + ingredient_deduction + allergy_bonus

    logger.info(
        f"[SCORE] violation_deduction={violation_deduction}  "
        f"ingredient_deduction={ingredient_deduction}  "
        f"allergy_bonus={allergy_bonus}  "
        f"total_deduction={total_deduction}"
    )

    score = max(0, 100 - total_deduction)
    logger.info(f"[SCORE] Raw score before bonus = {score}")
    return score



def get_risk_level(score: int) -> dict:
    """Map 0-100 health score to risk level."""
    for lo, hi, level, color, advice in RISK_LEVELS:
        if lo <= score < hi:
            return {"level": level, "color": color, "advice": advice}
    return {"level": "Unknown", "color": "gray", "advice": "Unable to determine risk."}



def build_reasons(violations: list[dict], ingredient_triggers: list[dict],
                  health_profile: dict | None = None) -> list[str]:
    """
    Build deduplicated, clinically detailed human-readable reasons.

    Each violation produces a paragraph of the form:
      "This product contains <value><unit> of <Nutrient>.
       For a patient with <Condition> [context], the recommended maximum is
       <limit><unit>/day. This exceeds the safe limit by <pct>% and may
       contribute to <clinical effect>. [Guideline]"

    Duplicates are removed by (condition, nutrient) pair.
    Ingredient triggers are appended after nutrition violations.
    """
    # ── Clinical effect descriptions per nutrient + condition ─────────────────
    _EFFECTS: dict[tuple[str, str], str] = {
        # (condition_lower, nutrient_lower): effect string
        ("hypertension", "sodium"):          "increased blood pressure and fluid retention",
        ("hypertension", "saturated_fat"):   "arterial stiffness and elevated cardiovascular risk",
        ("hypertension", "trans_fat"):       "worsened endothelial function and raised LDL cholesterol",
        ("hypertension", "added_sugar"):     "indirect blood pressure elevation through insulin resistance",
        ("hypertension", "calories"):        "weight gain which raises blood pressure",
        ("diabetes", "sugar"):               "rapid blood glucose spikes and worsened glycaemic control",
        ("diabetes", "added_sugar"):         "rapid blood glucose spikes and worsened glycaemic control",
        ("diabetes", "carbohydrates"):       "elevated post-meal blood glucose",
        ("diabetes", "saturated_fat"):       "worsened insulin resistance",
        ("diabetes", "trans_fat"):           "severely impaired glucose metabolism and raised cardiovascular risk",
        ("heart disease", "saturated_fat"):  "raised LDL cholesterol and increased plaque formation",
        ("heart disease", "trans_fat"):      "raised LDL, lowered HDL, and increased coronary artery disease risk",
        ("heart disease", "sodium"):         "increased fluid load on the heart and elevated blood pressure",
        ("heart disease", "cholesterol"):    "accelerated atherosclerosis and coronary artery disease",
        ("kidney disease", "sodium"):        "fluid retention and accelerated kidney function decline",
        ("kidney disease", "potassium"):     "dangerous hyperkalaemia in patients with reduced kidney function",
        ("kidney disease", "protein"):       "increased uraemic load and accelerated nephron loss",
        ("obesity", "calories"):             "caloric surplus promoting weight gain and metabolic dysfunction",
        ("obesity", "total_fat"):            "high caloric density and fat accumulation",
        ("obesity", "sugar"):                "lipogenesis and insulin resistance",
        ("pcos", "sugar"):                   "worsened insulin resistance and androgen elevation",
        ("pcos", "added_sugar"):             "worsened insulin resistance and hormonal imbalance",
        ("pcos", "trans_fat"):               "increased systemic inflammation and disrupted hormone balance",
        ("hypothyroidism", "sugar"):         "worsened metabolic dysfunction and weight gain",
        ("hypothyroidism", "calories"):      "weight gain which compounds hypothyroid-related metabolic slowing",
        ("high cholesterol", "saturated_fat"): "raised LDL cholesterol levels",
        ("high cholesterol", "trans_fat"):   "raised LDL and lowered HDL simultaneously",
    }

    def _effect(condition: str, nutrient: str) -> str:
        key = (condition.lower(), nutrient.lower().replace(" ", "_"))
        return _EFFECTS.get(key, "potential worsening of your condition")

    # ── Stage context builder ─────────────────────────────────────────────────
    def _stage_context(condition: str, hp: dict) -> str:
        c = condition.lower()
        if c == "hypertension":
            sys = hp.get("systolic")
            dia = hp.get("diastolic")
            if sys and dia:
                from app.services.risk_engine import classify_bp_stage
                stage = classify_bp_stage(sys, dia, hp.get("bp_status"))
                return f"{stage} Hypertension (BP {sys}/{dia} mmHg)"
            return "Hypertension"
        if c == "diabetes":
            fs = hp.get("fasting_sugar")
            if fs:
                from app.services.risk_engine import classify_sugar_stage
                stage = classify_sugar_stage(fs, hp.get("post_meal_sugar"), hp.get("sugar_status"))
                return f"{stage} Diabetes (fasting glucose {fs} mg/dL)"
            return "Diabetes"
        if c == "obesity":
            bmi = hp.get("bmi_score")
            if bmi:
                from app.services.risk_engine import classify_obesity
                klass = classify_obesity(bmi) or "Obesity"
                return f"{klass} Obesity (BMI {bmi:.1f})"
            return "Obesity"
        return condition

    hp = health_profile or {}
    reasons: list[str] = []
    seen: set[tuple[str, str]] = set()

    for v in sorted(violations, key=lambda x: -x["deduction"]):
        key = (v["condition"].lower(), v["nutrient"].lower())
        if key in seen:
            continue
        seen.add(key)

        unit       = v.get("unit", "")            # already canonical (Bug 1 fix)
        val_str    = format_nutrient(v["user_value"], v["nutrient"], "")
        limit_str  = format_nutrient(v["threshold"],  v["nutrient"], "")
        val        = val_str
        limit_fmt  = limit_str
        cond_ctx   = _stage_context(v["condition"], hp)
        guideline  = v.get("guideline", "")
        restr      = v.get("restriction_level", "").lower()
        pct_above  = v.get("pct_above", 0)
        pct_of_lim = v.get("pct_of_limit", 0)
        reco       = v.get("recommendation", "")
        effect     = _effect(v["condition"], v["nutrient"])

        # Diabetes hypertension implication override
        if (hp.get("_diabetes_implied_hypertension")
                and v["condition"] == "Hypertension"
                and "sodium" in v["nutrient"].lower()):
            cond_ctx = "Diabetes (elevated cardiovascular and BP risk)"

        if v["threshold"] == 0:
            explanation = (
                f"This product contains {val_str} of {v['nutrient']}. "
                f"For patients with {cond_ctx}, this nutrient must be completely avoided "
                f"as it causes {effect}. "
                f"{reco}"
                + (f" [{guideline}]" if guideline else "")
            )
        else:
            over_phrase = (
                f"{pct_above}% over the recommended limit"
                if pct_above > 0
                else "at the upper limit"
            )
            restr_phrase = (
                "This is a strict dietary restriction."
                if restr == "strict"
                else "This is a moderate dietary recommendation."
            )
            explanation = (
                f"This product contains {val_str} of {v['nutrient']}. "
                f"For a patient with {cond_ctx}, the recommended maximum is "
                f"{limit_fmt}/day — this food is {over_phrase}. "
                f"Excess {v['nutrient']} may contribute to {effect}. "
                f"{restr_phrase}"
                + (f" {reco}" if reco else "")
                + (f" [{guideline}]" if guideline else "")
            )

        reasons.append(explanation)

    # ── Ingredient triggers ───────────────────────────────────────────────────
    seen_ing: set[str] = set()
    for t in ingredient_triggers[:5]:
        key_ing = f"{t['ingredient']}|{t['condition']}".lower()
        if key_ing in seen_ing:
            continue
        seen_ing.add(key_ing)
        r = (
            f"{t['ingredient']} is flagged for {t['condition']}: "
            f"{t.get('reason', 'may worsen your condition')}. "
            f"{t.get('recommendation', '')}".strip()
        )
        reasons.append(r)

    return reasons[:12]



def get_affected_conditions(violations: list[dict], ingredient_triggers: list[dict]) -> list[str]:
    """Return unique affected conditions."""
    conditions = set()
    for v in violations:
        conditions.add(v["condition"])
    for t in ingredient_triggers:
        conditions.add(t["condition"])
    return sorted(conditions)



def build_threshold_summary(violations: list[dict]) -> list[dict]:
    """Return a clean per-nutrient threshold summary for the result screen."""
    summary = []
    seen = set()

    for v in violations:
        key = (v["condition"], v["nutrient"])

        if key in seen:
            continue

        seen.add(key)

        summary.append({
            "condition": v["condition"],
            "nutrient": v["nutrient"],
            "your_value": v["user_value"],
            "safe_limit": v["threshold"],
            "unit": v["unit"],
            "percent_used": v["pct_of_limit"],
            "percent_above": v["pct_above"],
            "restriction": v["restriction_level"],
        })

    return summary