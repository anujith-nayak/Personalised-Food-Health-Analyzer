"""
Disease-Specific Analyzer  —  Data-driven, zero hardcoded thresholds.
======================================================================
Step 3 of the pipeline.

Design goals
------------
* Every disease, sub-condition, nutrient, threshold and recommendation
  comes directly from health_r.csv.  Adding a new disease to the CSV
  automatically makes it work here — no code changes needed.

* Severity sub-conditions are determined from real health values
  (BP readings, fasting sugar, BMI) the same way risk_engine does,
  ensuring the two engines always agree on which rules apply.

* Duplicate deductions are prevented: if the same nutrient appears in
  both a stage-specific row and a General row, only the *stricter* limit
  (lower threshold_max for "less is better" nutrients) is used.

* The JSON response shape is identical to the previous version so the
  Flutter frontend requires no changes:
    {
      condition:       str,
      overall_impact:  str,   ("Low Risk" | "Moderate Risk" | "High Risk" | "Very High Risk")
      impact_color:    str,   ("green" | "yellow" | "orange" | "red")
      concerns:        list[ConcernDict],
      positives:       list[str],
      summary:         str,
    }

  Each ConcernDict:
    {
      nutrient:    str,
      value:       str,   e.g. "1280mg"
      threshold:   str,   e.g. "≤1200mg/day"
      importance:  str,   "critical" | "important" | "moderate" | "beneficial"
      message:     str,
    }
"""

from __future__ import annotations
import logging
from functools import lru_cache
from typing import Optional

import pandas as pd

from . import dataset_loader as dl
from .risk_engine import (
    classify_bp_stage,
    classify_sugar_stage,
    classify_obesity,
)
from app.utils.nutrient_format import (
    canonical_unit, is_percent_threshold,
    format_nutrient, fmt_val, safe_pct_of_limit,
    _CANONICAL_UNITS,
)

logger = logging.getLogger(__name__)


# ── Nutrient label lookup (display names only) ────────────────────────────────
_NUTRIENT_LABELS: dict[str, str] = {
    "calories":       "Calories",
    "total_fat":      "Total Fat",
    "fat":            "Total Fat",
    "saturated_fat":  "Saturated Fat",
    "trans_fat":      "Trans Fat",
    "cholesterol":    "Cholesterol",
    "sodium":         "Sodium",
    "potassium":      "Potassium",
    "calcium":        "Calcium",
    "iron":           "Iron",
    "carbohydrates":  "Total Carbohydrates",
    "carbs":          "Total Carbohydrates",
    "sugar":          "Sugar",
    "added_sugar":    "Added Sugar",
    "fiber":          "Dietary Fiber",
    "protein":        "Protein",
    "phosphorus":     "Phosphorus",
}

def _lbl(key: str) -> str:
    return _NUTRIENT_LABELS.get(key.lower(), key.replace("_", " ").title())


# ── Nutrient normalisation (maps CSV names → extracted dict keys) ─────────────
# The extraction dict uses keys like "carbohydrates", "sugar", "total_fat".
# The CSV uses aliases like "carbs", "fat", "added_sugar".
# This map translates CSV nutrient names to extraction keys.
_CSV_TO_EXTRACTED: dict[str, str] = {
    "fat":              "total_fat",
    "total_fat":        "total_fat",
    "carbs":            "carbohydrates",
    "total_carbs":      "carbohydrates",
    "total_carbohydrates": "carbohydrates",
    "added_sugar":      "sugar",       # fall back to total sugar if no added_sugar key
    "sugar":            "sugar",
    "total_sugars":     "sugar",
    "saturated fat":    "saturated_fat",
    "trans fat":        "trans_fat",
    "dietary_fiber":    "fiber",
    "fiber":            "fiber",
    "sodium":           "sodium",
    "salt":             "sodium",
    "calories":         "calories",
    "energy":           "calories",
    "protein":          "protein",
    "potassium":        "potassium",
    "calcium":          "calcium",
    "iron":             "iron",
    "cholesterol":      "cholesterol",
    "saturated_fat":    "saturated_fat",
    "trans_fat":        "trans_fat",
    "phosphorus":       "phosphorus",
}

# Nutrients that are BENEFICIAL (higher is better, threshold_min applies)
_BENEFICIAL_NUTRIENTS: frozenset[str] = frozenset({
    "fiber", "dietary_fiber", "protein", "potassium", "calcium",
    "iron", "omega3", "magnesium", "vitamin_d",
})

# Restriction level → importance label (used in concern dicts)
_RESTRICTION_TO_IMPORTANCE: dict[str, str] = {
    "strict":      "critical",
    "moderate":    "important",
    "recommended": "beneficial",
}


# ── Severity sub-condition resolver ──────────────────────────────────────────
def _resolve_sub_conditions(condition: str, health_profile: dict) -> list[str]:
    """
    Given a condition name and the user's health profile, return the ordered
    list of sub-condition labels to check (most specific first, General last).
    The logic mirrors risk_engine.py so both engines use identical staging.
    """
    c = condition.lower().strip()

    # ── Hypertension ─────────────────────────────────────────────────────
    if c == "hypertension":
        stage = classify_bp_stage(
            health_profile.get("systolic"),
            health_profile.get("diastolic"),
            health_profile.get("bp_status"),
        )
        subs = [stage, "General"]
        if health_profile.get("diabetes"):       subs.insert(1, "With Diabetes")
        if health_profile.get("kidney_disease"): subs.insert(1, "With CKD")
        if health_profile.get("heart_disease"):  subs.insert(1, "With Heart")  # not in CSV but safe
        bmi = health_profile.get("bmi_score") or 0
        if bmi >= 25:                            subs.insert(1, "With Obesity")
        return subs

    # ── Diabetes ─────────────────────────────────────────────────────────
    if c == "diabetes":
        stage = classify_sugar_stage(
            health_profile.get("fasting_sugar"),
            health_profile.get("post_meal_sugar"),
            health_profile.get("sugar_status"),
        )
        # When no readings available, apply Type 2 rules as a safe default
        # so the most common and strict rules are always checked
        if stage == "General":
            stage = "Type 2"
        subs = [stage, "General"]
        if health_profile.get("hypertension"):   subs.insert(1, "With Hypertension")
        if health_profile.get("kidney_disease"): subs.insert(1, "With CKD")
        if health_profile.get("kidney_disease"): subs.insert(1, "With Kidney")
        if health_profile.get("heart_disease"):  subs.insert(1, "With Heart")
        if health_profile.get("pcos") or health_profile.get("pcod"):
            subs.insert(1, "With PCOS")
        return subs

    # ── Obesity ──────────────────────────────────────────────────────────
    if c == "obesity":
        bmi   = health_profile.get("bmi_score") or 0
        klass = classify_obesity(bmi) or "General"
        subs  = [klass, "General"]
        if health_profile.get("diabetes"):       subs.insert(1, "With Diabetes")
        if health_profile.get("hypertension"):   subs.insert(1, "With Hypertension")
        if health_profile.get("heart_disease"):  subs.insert(1, "With Heart")
        if health_profile.get("pcos") or health_profile.get("pcod"):
            subs.insert(1, "With PCOS")
        return subs

    # ── Kidney Disease ────────────────────────────────────────────────────
    if "kidney" in c:
        # Without explicit staging info, default to Stage 3-4 (conservative)
        subs = ["Stage 3-4", "General"]
        if health_profile.get("diabetes"):       subs.insert(1, "With Diabetes")
        if health_profile.get("hypertension"):   subs.insert(1, "With Hypertension")
        if health_profile.get("obesity"):        subs.insert(1, "With Obesity")
        if health_profile.get("pcos") or health_profile.get("pcod"):
            subs.insert(1, "With PCOS")
        return subs

    # ── Heart Disease ─────────────────────────────────────────────────────
    if "heart" in c:
        subs = ["General"]
        if health_profile.get("hypertension"):   subs.insert(0, "With Hypertension")
        if health_profile.get("diabetes"):       subs.insert(0, "With Diabetes")
        if health_profile.get("kidney_disease"): subs.insert(0, "With CKD")
        bmi = health_profile.get("bmi_score") or 0
        if bmi >= 25:                            subs.insert(0, "With Obesity")
        return subs

    # ── PCOS / PCOD ───────────────────────────────────────────────────────
    if c in ("pcos", "pcod"):
        bmi  = health_profile.get("bmi_score") or 0
        subs = ["General"]
        if bmi >= 25:                            subs.insert(0, "Overweight")
        if health_profile.get("diabetes"):       subs.insert(0, "With Insulin Resistance")
        if health_profile.get("thyroid"):        subs.insert(0, "With Thyroid")
        return subs

    # ── Hypothyroidism ────────────────────────────────────────────────────
    if c == "hypothyroidism":
        subs = ["General"]
        bmi = health_profile.get("bmi_score") or 0
        if bmi >= 25:                            subs.insert(0, "With Obesity")
        if health_profile.get("hypertension") or health_profile.get("heart_disease"):
            subs.insert(0, "With Cholesterol")
        if health_profile.get("diabetes"):       subs.insert(0, "With Diabetes")
        return subs

    # ── Hyperthyroidism ───────────────────────────────────────────────────
    if c == "hyperthyroidism":
        return ["General", "Graves Disease"]

    # ── Thyroid (generic — when type not specified) ───────────────────────
    if c == "thyroid":
        thyroid_type = (health_profile.get("thyroid_type") or "hypo").lower()
        if "hyper" in thyroid_type:
            return ["General", "Graves Disease"]
        return ["General", "Levothyroxine"]

    # ── High Cholesterol ──────────────────────────────────────────────────
    if "cholesterol" in c:
        # LDL High is the most common presentation; always include it as default
        subs = ["LDL High", "General"]
        if health_profile.get("diabetes"):       subs.insert(0, "With Diabetes")
        if health_profile.get("heart_disease"):  subs.insert(0, "With Heart")
        if health_profile.get("pcos") or health_profile.get("pcod"):
            subs.insert(0, "With PCOS")
        return subs

    # ── Appendicitis ──────────────────────────────────────────────────────
    if "appendicitis" in c:
        phase = (health_profile.get("appendicitis_phase") or "").lower()
        if "acute" in phase:
            return ["Acute Phase", "General"]
        if "recovery" in phase or "post" in phase:
            return ["Post-Appendectomy Recovery", "General"]
        return ["General"]

    # ── Default: just use General ─────────────────────────────────────────
    return ["General"]


# ── CSV rule cache (grouped by condition for O(1) per-condition lookup) ───────
@lru_cache(maxsize=1)
def _get_grouped_rules() -> dict[str, pd.DataFrame]:
    """
    Build a dict: lowercase_condition_name → DataFrame of its rows.
    Cached after first call — zero repeated CSV scans.
    """
    df = dl.health_r
    if df.empty:
        return {}
    grouped: dict[str, pd.DataFrame] = {}
    for cond, grp in df.groupby(df["condition"].str.lower().str.strip()):
        grouped[cond] = grp.copy()
    return grouped


# ── Per-condition nutrient rule selector ─────────────────────────────────────

def _select_rules_for_condition(
    condition: str,
    health_profile: dict,
) -> list[dict]:
    """
    Return the de-duplicated list of applicable nutrient rules for one
    condition + user severity.

    De-duplication strategy (per nutrient):
      For "less is better" nutrients → keep the row with the LOWEST threshold_max
      (strictest). For "more is better" nutrients → keep the HIGHEST threshold_min.
    This ensures stage-specific limits always override General limits.
    """
    grouped = _get_grouped_rules()
    cond_key = condition.lower().strip()

    # Fuzzy match: "high cholesterol" vs "high_cholesterol" etc.
    cond_df: Optional[pd.DataFrame] = None
    for key, df_part in grouped.items():
        if cond_key in key or key in cond_key:
            cond_df = df_part
            break

    if cond_df is None or cond_df.empty:
        logger.debug(f"[DiseaseAnalyzer] No CSV rules found for '{condition}'")
        return []

    sub_conditions = _resolve_sub_conditions(condition, health_profile)
    sub_lower      = [s.lower() for s in sub_conditions]

    # Collect all rows matching any of the user's sub-conditions.
    # "general" rows are always included as a baseline fallback.
    def _sub_matches(x: str) -> bool:
        x = x.lower().strip()
        if "general" in x:
            return True
        return any(s in x or x in s for s in sub_lower)

    mask    = cond_df["sub_condition"].str.lower().str.strip().apply(_sub_matches)
    relevant = cond_df[mask].copy()

    # Only evaluate actionable rules
    relevant = relevant[relevant["restriction_level"].isin(["strict", "moderate", "recommended"])]

    # ── De-duplicate per nutrient ─────────────────────────────────────────
    best: dict[str, dict] = {}   # nutrient_key → best row as dict

    for _, row in relevant.iterrows():
        csv_nutrient = str(row.get("nutrient", "")).lower().strip()
        ext_key      = _CSV_TO_EXTRACTED.get(csv_nutrient, csv_nutrient)
        is_beneficial = csv_nutrient in _BENEFICIAL_NUTRIENTS

        try:
            tmax = float(row.get("threshold_max")) if pd.notna(row.get("threshold_max")) else None
            tmin = float(row.get("threshold_min")) if pd.notna(row.get("threshold_min")) else None
        except (ValueError, TypeError):
            tmax, tmin = None, None

        csv_unit_raw = str(row.get("unit", ""))

        # Bug 2 & 3 fix: skip percent-unit rows — they express limits as
        # "% of daily calories" which cannot be compared to extracted g/mg values.
        if is_percent_threshold(csv_unit_raw):
            continue

        display_unit = canonical_unit(csv_nutrient, csv_unit_raw)   # Bug 1 fix

        r = {
            "csv_nutrient":   csv_nutrient,
            "ext_key":        ext_key,
            "threshold_max":  tmax,
            "threshold_min":  tmin,
            "unit":           display_unit,                          # Bug 1 fix
            "restriction":    str(row.get("restriction_level", "moderate")).lower(),
            "risk_weight":    float(row.get("risk_weight", 0.5)) if pd.notna(row.get("risk_weight")) else 0.5,
            "recommendation": str(row.get("recommendation", "")),
            "guideline":      str(row.get("guideline_source", "")),
            "is_beneficial":  is_beneficial,
        }

        if ext_key not in best:
            best[ext_key] = r
        else:
            existing = best[ext_key]
            if not is_beneficial:
                # Keep strictest (lowest) threshold_max
                if (tmax is not None and
                        (existing["threshold_max"] is None or tmax < existing["threshold_max"])):
                    best[ext_key] = r
            else:
                # Keep highest threshold_min (most demanding for beneficial)
                if (tmin is not None and
                        (existing["threshold_min"] is None or tmin > existing["threshold_min"])):
                    best[ext_key] = r

    return list(best.values())


# ── Single-condition evaluator ────────────────────────────────────────────────

def analyze_for_condition(
    condition: str,
    nutrition: dict,
    health_profile: Optional[dict] = None,
) -> dict:
    """
    Evaluate food impact for ONE health condition against CSV rules.

    Returns the same dict shape as the old hardcoded version:
      {condition, overall_impact, impact_color, concerns, positives, summary}
    """
    if health_profile is None:
        health_profile = {}

    rules = _select_rules_for_condition(condition, health_profile)

    if not rules:
        return {
            "condition":      condition,
            "overall_impact": "No specific rules available",
            "impact_color":   "gray",
            "concerns":       [],
            "positives":      [],
            "summary":        f"No dietary rules found for {condition} in the dataset.",
        }

    concerns:  list[dict] = []
    positives: list[str]  = []
    risk_score = 0

    for rule in rules:
        ext_key    = rule["ext_key"]
        csv_key    = rule["csv_nutrient"]
        unit       = rule["unit"]
        restr      = rule["restriction"]
        tmax       = rule["threshold_max"]
        tmin       = rule["threshold_min"]
        reco       = rule["recommendation"]
        guideline  = rule["guideline"]
        rw         = rule["risk_weight"]
        is_ben     = rule["is_beneficial"]
        importance = _RESTRICTION_TO_IMPORTANCE.get(restr, "important")

        # Look up value (try extracted key first, then csv key directly)
        value: Optional[float] = nutrition.get(ext_key)
        if value is None:
            value = nutrition.get(csv_key)
        if value is None:
            continue   # nutrient not extracted from this label — skip

        label = _lbl(ext_key if ext_key in _NUTRIENT_LABELS else csv_key)
        # Bug 1 fix: always use canonical unit, never raw CSV unit
        unit  = canonical_unit(ext_key if ext_key in _CANONICAL_UNITS else csv_key, unit)

        val_str   = format_nutrient(value, ext_key, "")        # Bug 1 & 4 fix
        tmax_str  = format_nutrient(tmax, ext_key, "") if tmax is not None else ""
        tmin_str  = format_nutrient(tmin, ext_key, "") if tmin is not None else ""

        # ── BENEFICIAL nutrients (fiber, protein, potassium …) ─────────────
        if is_ben:
            if tmin is not None and value >= tmin:
                positives.append(
                    f"{label} {val_str} — adequate for {condition}. {reco}"
                )
            else:
                threshold_str = f"≥{tmin_str}" if tmin is not None else "adequate amount"
                concerns.append({
                    "nutrient":   label,
                    "value":      val_str,                           # Bug 1 fix
                    "threshold":  f"{threshold_str} recommended",
                    "importance": importance,
                    "message": (
                        f"Low {label} ({val_str}): {reco}"
                        + (f" [{guideline}]" if guideline else "")
                    ),
                })
                risk_score += 1

        # ── ZERO-TOLERANCE nutrients (trans_fat, alcohol …) ────────────────
        elif tmax == 0:
            if value > 0:
                concerns.append({
                    "nutrient":   label,
                    "value":      val_str,                           # Bug 1 fix
                    "threshold":  f"0{unit} — strictly avoid",
                    "importance": "critical",
                    "message": (
                        f"Contains {label} ({val_str}): {reco}"
                        + (f" [{guideline}]" if guideline else "")
                    ),
                })
                risk_score += int(rw * 4)
            else:
                positives.append(f"No {label} detected — good for {condition}.")

        # ── UPPER-LIMIT nutrients (sodium, sugar, saturated fat …) ─────────
        elif tmax is not None and value > tmax:
            # Bug 2 fix: correct percentage calculation
            pct_of_limit, pct_above = safe_pct_of_limit(value, tmax)
            severity_lbl = (
                "Severely high" if pct_of_limit > 200 else
                "High"          if pct_of_limit > 130 else
                "Moderately high"
            )
            concerns.append({
                "nutrient":   label,
                "value":      val_str,                               # Bug 1 fix
                "threshold":  f"≤{tmax_str}/day",                   # Bug 1 fix
                "importance": importance,
                "message": (
                    f"{severity_lbl} {label}: {val_str} is {pct_of_limit}% of your "
                    f"{condition} daily limit ({tmax_str}), which is {pct_above}% over. "
                    f"{reco}"
                    + (f" [{guideline}]" if guideline else "")
                ),
            })
            weight = 3 if restr == "strict" else 2 if restr == "moderate" else 1
            risk_score += int(weight * rw)

        elif tmax is not None:
            # Within limit
            positives.append(
                f"{label} {val_str} — within {condition} limit (≤{tmax_str})."
            )

    # ── Overall impact ────────────────────────────────────────────────────
    if risk_score == 0:
        overall, color = "Low Risk",       "green"
    elif risk_score <= 2:
        overall, color = "Moderate Risk",  "yellow"
    elif risk_score <= 5:
        overall, color = "High Risk",      "orange"
    else:
        overall, color = "Very High Risk", "red"

    # ── Summary sentence ──────────────────────────────────────────────────
    if concerns:
        concern_names = list(dict.fromkeys(c["nutrient"] for c in concerns))[:3]
        summary = (
            f"This food raises concerns for {condition} due to: "
            f"{', '.join(concern_names)}."
        )
    else:
        summary = (
            f"Based on extracted values, this food appears acceptable for {condition}."
        )

    logger.info(
        f"[DiseaseAnalyzer] {condition}: risk_score={risk_score} "
        f"concerns={len(concerns)} positives={len(positives)} → {overall}"
    )

    return {
        "condition":      condition,
        "overall_impact": overall,
        "impact_color":   color,
        "concerns":       concerns,
        "positives":      positives,
        "summary":        summary,
    }


# ── Multi-condition entry point ───────────────────────────────────────────────

def analyze_all_conditions(
    conditions: list[str],
    nutrition: dict,
    health_profile: Optional[dict] = None,
) -> list[dict]:
    """
    Run disease analysis for every condition in the user's profile.

    - Automatically uses CSV rules for every condition.
    - No condition is skipped unless the CSV has no rows for it.
    - Returns one result dict per condition (same shape as before).
    """
    if health_profile is None:
        health_profile = {}

    if not conditions:
        return []

    results = []
    seen    = set()

    for condition in conditions:
        # Deduplicate: PCOS and PCOD produce the same analysis
        canonical = condition.lower().strip()
        if canonical == "pcod":
            canonical = "pcos"
            condition = "PCOS"
        if canonical in seen:
            continue
        seen.add(canonical)

        result = analyze_for_condition(condition, nutrition, health_profile)
        results.append(result)

    return results
