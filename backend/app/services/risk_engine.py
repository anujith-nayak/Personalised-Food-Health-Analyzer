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
        if fasting >= 126: return "Diabetic"
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
    "sodium":         ["sodium", "salt", "sodium_chloride"],
    "sugar":          ["sugar", "added_sugar", "sugars", "total_sugar", "fructose"],
    "calories":       ["calories", "energy", "kcal", "cal"],
    "fat":            ["fat", "total_fat", "saturated_fat", "trans_fat"],
    "saturated_fat":  ["saturated_fat", "saturated fat"],
    "trans_fat":      ["trans_fat", "trans fat"],
    "protein":        ["protein"],
    "carbohydrates":  ["carbohydrates", "carbs", "refined_carbs"],
    "cholesterol":    ["cholesterol", "dietary_cholesterol"],
    "potassium":      ["potassium"],
    "phosphorus":     ["phosphorus"],
    "caffeine":       ["caffeine"],
}

def _match_nutrient(rule_nutrient: str, nutrition: dict) -> Optional[tuple]:
    """Find the best matching nutrition value for a rule nutrient. Returns (key, value) or None."""
    rn = rule_nutrient.lower().strip()
    # Direct match
    for k, v in nutrition.items():
        if v is not None and k.lower() == rn:
            return (k, float(v))
    # Alias match
    aliases = NUTRIENT_ALIASES.get(rn, [rn])
    for alias in aliases:
        for k, v in nutrition.items():
            if v is not None and (alias in k.lower() or k.lower() in alias):
                return (k, float(v))
    return None

def _normalize(s: str) -> str:
    return str(s).lower().strip()

# ── Main profile extractor ────────────────────────────────────────────────────
def _get_user_conditions(health_profile: dict) -> list[str]:
    """
    Map stored health profile fields to condition names used in CSV.
    Also adds implied comorbidity conditions:
    - Diabetes → also check Hypertension rules for sodium
      (diabetics have elevated cardiovascular/BP risk)
    """
    conditions = []
    if health_profile.get("hypertension"): conditions.append("Hypertension")
    if health_profile.get("diabetes"):     conditions.append("Diabetes")
    if health_profile.get("pcos"):         conditions.append("PCOS")
    if health_profile.get("pcod"):         conditions.append("PCOS")
    if health_profile.get("heart_disease"): conditions.append("Heart Disease")
    if health_profile.get("kidney_disease"): conditions.append("Kidney Disease")
    if health_profile.get("obesity"):      conditions.append("Obesity")

    thyroid_type = (health_profile.get("thyroid_type") or "").lower()
    if health_profile.get("thyroid"):
        if "hypo" in thyroid_type:    conditions.append("Hypothyroidism")
        elif "hyper" in thyroid_type: conditions.append("Hyperthyroidism")
        else:                          conditions.append("Hypothyroidism")

    bmi = health_profile.get("bmi_score") or 0
    if bmi >= 25 and "Obesity" not in conditions:
        conditions.append("Obesity")

    # ── Comorbidity rules ──────────────────────────────────────────────────
    # Diabetes increases cardiovascular and BP risk — evaluate sodium rules
    # even if hypertension not explicitly selected
    if "Diabetes" in conditions and "Hypertension" not in conditions:
        conditions.append("Hypertension")   # implied sodium/BP check
        health_profile["_diabetes_implied_hypertension"] = True

    # Diabetes also raises heart disease risk
    if "Diabetes" in conditions and "Heart Disease" not in conditions:
        conditions.append("Heart Disease")
        health_profile["_diabetes_implied_heart"] = True

    return list(dict.fromkeys(conditions))  # preserve order, deduplicate

# ── Core Analysis Functions ───────────────────────────────────────────────────

def analyze_with_health_r(
    nutrition: dict,
    health_profile: dict,
) -> tuple[list[dict], int]:
    """
    Primary analysis using health_r.csv.
    Determines disease stage from actual health values,
    finds matching rules, checks nutrition thresholds,
    and calculates proportional deductions.

    Returns: (list of violations, total_deduction 0-70)
    """
    df = dl.health_r
    if df.empty or not nutrition:
        return [], 0

    violations = []
    total_deduction = 0

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
        sub_map["Diabetes"] = [stage, "General"]

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

    # ── Check each condition's rules ──────────────────────────────────────
    for condition, sub_conditions in sub_map.items():
        cond_lower = condition.lower()
        cond_mask = df["condition"].str.lower().apply(
            lambda x: cond_lower in x or x in cond_lower
        )
        cond_df = df[cond_mask]
        if cond_df.empty:
            continue

        # Only check rules matching the user's sub-condition or General
        seen_nutrients = set()
        for sub in sub_conditions:
            sub_lower = sub.lower()
            sub_mask = cond_df["sub_condition"].str.lower().apply(
                lambda x: sub_lower in x or x in sub_lower or "general" in x
            )
            rows = cond_df[sub_mask]

            for _, row in rows.iterrows():
                rule_nutrient = str(row.get("nutrient", "")).strip()
                threshold_max = row.get("threshold_max")
                restriction   = str(row.get("restriction_level", "")).lower()
                rw            = float(row.get("risk_weight", 0.5))

                # Skip non-strict/moderate rules for performance
                if restriction not in ("strict", "moderate"):
                    continue

                # Avoid duplicate nutrient checks per condition
                key = (condition, rule_nutrient)
                if key in seen_nutrients:
                    continue

                matched = _match_nutrient(rule_nutrient, nutrition)
                if not matched:
                    continue

                nutr_key, user_value = matched
                if threshold_max is None:
                    continue

                try:
                    max_val = float(threshold_max)
                except (ValueError, TypeError):
                    continue

                if max_val == 0:
                    # Zero tolerance rule — any presence is a violation
                    if user_value > 0:
                        deduction = int(rw * 30)  # up to 30 points for zero-tolerance
                        seen_nutrients.add(key)
                        pct = 100
                        violations.append(_make_violation(
                            condition, rule_nutrient, user_value, max_val,
                            pct, deduction, row, health_profile
                        ))
                        total_deduction += deduction
                elif user_value > max_val:
                    pct_over = min(int((user_value / max_val) * 100), 300)
                    # Deduction scales with how much over the limit
                    if pct_over > 200:       severity_mult = 2.5
                    elif pct_over > 150:     severity_mult = 2.0
                    elif pct_over > 100:     severity_mult = 1.5
                    elif pct_over > 50:      severity_mult = 1.2
                    else:                    severity_mult = 1.0

                    base = rw * 15 * severity_mult
                    if restriction == "strict":   base *= 1.5
                    deduction = min(int(base), 35)
                    seen_nutrients.add(key)
                    violations.append(_make_violation(
                        condition, rule_nutrient, user_value, max_val,
                        pct_over, deduction, row, health_profile
                    ))
                    total_deduction += deduction

    return violations, min(int(total_deduction), 70)


def _make_violation(
    condition: str,
    nutrient: str,
    user_value: float,
    threshold: float,
    pct_of_threshold: int,
    deduction: int,
    row,
    health_profile: dict,
) -> dict:
    """Build a detailed violation dict with human-readable explanation."""
    unit = str(row.get("unit", "")).split("/")[0]  # e.g. "mg" from "mg/day"
    recommendation = str(row.get("recommendation", ""))
    restriction    = str(row.get("restriction_level", "")).capitalize()
    guideline      = str(row.get("guideline_source", ""))

    # Build contextual explanation
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
            f"This food contains {user_value}{unit} of {nutrient}. "
            f"Your recommended limit for {condition}{context} is {threshold}{unit}/day. "
            f"This product alone uses {pct_of_threshold}% of your daily allowance. "
            f"Restriction level: {restriction}. [{guideline}]"
        )
    else:
        explanation = (
            f"This food contains {nutrient}, which must be completely avoided "
            f"for {condition}{context}. [{guideline}]"
        )

    return {
        "condition":           condition,
        "nutrient":            nutrient,
        "user_value":          user_value,
        "threshold":           threshold,
        "unit":                unit,
        "pct_of_threshold":    pct_of_threshold,
        "deduction":           deduction,
        "restriction_level":   restriction,
        "explanation":         explanation,
        "recommendation":      recommendation,
        "guideline":           guideline,
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
    Returns final score 0-100 (higher = safer).
    """
    violation_deduction = sum(v["deduction"] for v in violations)
    total_deduction = violation_deduction + ingredient_deduction + allergy_bonus
    score = max(0, 100 - total_deduction)
    return score


def get_risk_level(score: int) -> dict:
    """Map 0-100 health score to risk level."""
    for lo, hi, level, color, advice in RISK_LEVELS:
        if lo <= score < hi:
            return {"level": level, "color": color, "advice": advice}
    return {"level": "Unknown", "color": "gray", "advice": "Unable to determine risk."}


def build_reasons(violations: list[dict], ingredient_triggers: list[dict],
                  health_profile: dict | None = None) -> list[str]:
    """Build human-readable reasons. Adds comorbidity context where applicable."""
    reasons = []
    seen = set()

    for v in sorted(violations, key=lambda x: -x["deduction"]):
        exp = v["explanation"]

        # Replace generic Hypertension sodium warning with diabetes-specific one
        # when hypertension was implied by diabetes (not explicitly selected)
        if (health_profile and
                health_profile.get("_diabetes_implied_hypertension") and
                v["condition"] == "Hypertension" and
                v["nutrient"] == "sodium"):
            exp = (
                f"High Sodium: This product contains {v['user_value']}{v['unit']} of sodium. "
                f"People with diabetes are at increased risk of hypertension and heart disease, "
                f"so frequent consumption of high-sodium foods is not recommended. "
                f"Safe limit: {v['threshold']}{v['unit']}/day. "
                f"This product uses {v['pct_of_threshold']}% of the recommended daily allowance."
            )

        if exp not in seen:
            reasons.append(exp)
            seen.add(exp)

    for t in ingredient_triggers[:5]:
        r = f"{t['ingredient']} — {t['reason']} ({t['condition']})"
        if r not in seen:
            reasons.append(r)
            seen.add(r)

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
        if key in seen: continue
        seen.add(key)
        summary.append({
            "condition":        v["condition"],
            "nutrient":         v["nutrient"],
            "your_value":       v["user_value"],
            "safe_limit":       v["threshold"],
            "unit":             v["unit"],
            "percent_used":     v["pct_of_threshold"],
            "restriction":      v["restriction_level"],
        })
    return summary
