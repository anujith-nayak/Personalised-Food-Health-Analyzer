"""
Packaged Food Analysis API — Full 5-Step Pipeline

Step 1: OCR extraction
Step 2: Nutrient evaluation against healthy reference ranges
Step 3: Disease-specific impact analysis
Step 4: Personalized health score
Step 5: Structured detailed report
"""
import logging
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User, HealthProfile
from app.services.ocr_service import extract_text_from_image
from app.services.ingredient_extractor import parse_food_label
from app.services.allergy_engine import check_allergies, get_allergy_risk_score
from app.services.nutrition_evaluator import evaluate_all_nutrients
from app.services.disease_analyzer import analyze_all_conditions
from app.services.risk_engine import (
    _get_user_conditions,
    analyze_with_health_r,
    analyze_ingredients_against_rules,
    calculate_health_score,
    get_risk_level,
    build_reasons,
    build_threshold_summary,
)
from app.services.recommendation_engine import get_recommendations
from app.utils.nutrient_format import format_nutrient, safe_pct_of_limit
from app.services.ai_violation_engine import (
    get_ai_violations,
    analyse_ingredients_for_conditions,
    ingredient_risks_to_violations,
    deduplicate_violations,
    apply_ingredient_score_floor,
    build_ingredient_recommendation,
)

router = APIRouter(prefix="/food", tags=["Packaged Food Analysis"])
logger = logging.getLogger(__name__)


def _build_health_dict(user: User, profile: HealthProfile | None) -> dict:
    data = {"bmi_score": user.bmi_score, "bmi_category": user.bmi_category}
    if profile:
        data.update({
            "hypertension":      profile.hypertension,
            "bp_status":         profile.bp_status,
            "systolic":          profile.systolic,
            "diastolic":         profile.diastolic,
            "diabetes":          profile.diabetes,
            "sugar_status":      profile.sugar_status,
            "fasting_sugar":     profile.fasting_sugar,
            "post_meal_sugar":   profile.post_meal_sugar,
            "thyroid":           profile.thyroid,
            "thyroid_type":      profile.thyroid_type,
            "pcos":              profile.pcos,
            "pcod":              profile.pcod,
            "heart_disease":     profile.heart_disease,
            "kidney_disease":    profile.kidney_disease,
            "obesity":           profile.obesity,
            "high_cholesterol":  getattr(profile, "high_cholesterol", False),
            "appendicitis":      getattr(profile, "appendicitis", False),
            "appendicitis_phase": getattr(profile, "appendicitis_phase", None),
            "other_condition":   getattr(profile, "other_condition", None),
        })
    return data


def _final_recommendation(
    score: int,
    conditions: list[str],
    disease_impacts: list[dict],
    violations: list[dict],
    health_dict: dict,
) -> str:
    """
    Generate a concise, non-repetitive paragraph combining:
    - Overall verdict based on score
    - Up to 3 distinct nutrient concerns across all conditions
    - Condition context (BP reading, sugar level, BMI)
    No condition name is repeated; no nutrient is repeated.
    """
    # ── Verdict sentence ──────────────────────────────────────────────────
    if score >= 90:
        verdict = "This food is generally safe for your health profile."
    elif score >= 80:
        verdict = "This food is acceptable but should be consumed in moderation."
    elif score >= 60:
        verdict = "This food poses moderate health concerns for your conditions."
    elif score >= 40:
        verdict = "This food is not recommended and poses significant health risks."
    else:
        verdict = "This food is dangerous for your health conditions and should be avoided."

    # ── Build context string (BP / sugar / BMI) ───────────────────────────
    context_parts: list[str] = []
    sys = health_dict.get("systolic")
    dia = health_dict.get("diastolic")
    if sys and dia:
        context_parts.append(f"your blood pressure ({sys}/{dia} mmHg)")
    fs = health_dict.get("fasting_sugar")
    if fs:
        context_parts.append(f"your blood sugar ({fs} mg/dL fasting)")
    bmi = health_dict.get("bmi_score")
    if bmi and bmi >= 25:
        context_parts.append(f"your BMI ({bmi:.1f})")

    # ── Collect unique nutrient concerns across all conditions ────────────
    seen_nutrients:  set[str] = set()
    seen_conditions: set[str] = set()
    concern_sentences: list[str] = []

    # Sort by impact severity: red → orange → yellow
    color_order = {"red": 0, "orange": 1, "yellow": 2, "green": 3, "gray": 4}
    sorted_impacts = sorted(
        disease_impacts,
        key=lambda d: color_order.get(d.get("impact_color", "gray"), 4)
    )

    for d in sorted_impacts:
        if len(concern_sentences) >= 3:
            break
        cond  = d["condition"]
        color = d.get("impact_color", "gray")
        if color not in ("orange", "red"):
            continue
        if cond in seen_conditions:
            continue
        seen_conditions.add(cond)

        for c in d.get("concerns", []):
            nutrient_key = c["nutrient"].lower()
            if nutrient_key in seen_nutrients:
                continue
            seen_nutrients.add(nutrient_key)
            # Pull value + threshold from the concern dict (already formatted)
            val   = c.get("value", "")
            limit = c.get("threshold", "")
            sentence = (
                f"It contains {val} of {c['nutrient']}, "
                f"which exceeds the {cond} limit of {limit}."
            )
            concern_sentences.append(sentence)
            break   # one key concern per condition

    # ── Assemble paragraph ────────────────────────────────────────────────
    parts = [verdict]
    if context_parts and score < 80:
        parts.append(f"Given {' and '.join(context_parts)}, this food requires careful consideration.")
    if concern_sentences:
        parts.extend(concern_sentences)

    return " ".join(parts)


@router.post("/analyze-food-label")
async def analyze_food_label(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Full 5-step personalized food analysis pipeline.
    """
    if file.content_type not in ("image/jpeg", "image/png", "image/jpg", "image/webp"):
        raise HTTPException(status_code=400, detail="Only JPG, PNG, or WebP images are supported.")

    image_bytes = await file.read()
    if len(image_bytes) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image too large. Max 15MB.")

    # ── STEP 1: OCR ───────────────────────────────────────────────────────────
    logger.info("STEP 1: Running OCR on uploaded image")
    try:
        ocr_text = extract_text_from_image(image_bytes)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"OCR failed: {e}")

    parsed       = parse_food_label(ocr_text)
    ingredients  = parsed["ingredients"]
    nutrition    = parsed["nutrition"]    # full dict including None values
    product_name = parsed["product_name"]

    non_null_nutrition = {k: v for k, v in nutrition.items() if v is not None}
    logger.info(f"STEP 1 DONE — product={product_name} extracted={list(non_null_nutrition.keys())}")

    if not non_null_nutrition:
        return {
            "product_name":    product_name,
            "step":            1,
            "error":           "nutrition_not_extracted",
            "message":         (
                "Could not extract nutrition values from this image. "
                "Please retake the photo with the Nutrition Facts panel fully visible and well-lit."
            ),
            "health_score":    None,
            "risk_level":      "Unable to Analyse",
            "risk_color":      "gray",
            "debug_ocr_snippet": ocr_text[:400],
        }

    # ── STEP 2: Nutrient evaluation ───────────────────────────────────────────
    logger.info("STEP 2: Evaluating nutrients against healthy benchmarks")
    nutrient_evaluation = evaluate_all_nutrients(nutrition)
    logger.info(f"STEP 2 DONE — {len(nutrient_evaluation)} nutrients evaluated")

    # ── STEP 3: User profile + disease analysis ───────────────────────────────
    logger.info("STEP 3: Running disease-specific analysis")
    profile     = db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()
    health_dict = _build_health_dict(current_user, profile)
    conditions  = _get_user_conditions(health_dict)

    # ── display_conditions initialized HERE — before any use ─────────────────
    # Must be set before build_ingredient_recommendation() is called below.
    display_conditions = [c for c in conditions if not (
        c == "Hypertension" and health_dict.get("_diabetes_implied_hypertension")
        and not health_dict.get("hypertension")
    )]

    disease_impacts = analyze_all_conditions(conditions, non_null_nutrition, health_dict)
    logger.info(f"STEP 3 DONE — conditions={conditions}")

    # ── STEP 4: Allergy check + personalized score ────────────────────────────
    logger.info("STEP 4: Calculating personalized health score")
    allergy_alerts   = check_allergies(ingredients, conditions)
    allergy_deduct   = get_allergy_risk_score(allergy_alerts)

    violations, nutrition_deduction = analyze_with_health_r(non_null_nutrition, health_dict)
    ing_triggers, ingredient_deduct  = analyze_ingredients_against_rules(ingredients, conditions)

    # ── AI violations for "Other" condition ──────────────────────────────────
    ai_violations: list[dict] = []
    ai_overall_risk: str = ""
    other_cond = health_dict.get("other_condition", "") or ""
    if other_cond.strip():
        try:
            ai_violations, ai_overall_risk = get_ai_violations(
                other_cond.strip(), non_null_nutrition, ingredients,
            )
        except Exception as e:
            logger.warning(f"[AI-Score] AI violation query failed: {e}")

    # ── Part 3 & 7: Per-ingredient analysis for ALL user conditions ───────────
    # Analyses every ingredient against the user's health conditions so that
    # harmful ingredients (Palm Oil, HFCS, Hydrogenated Fat) increase risk
    # even when nutrition values were not extracted by OCR.
    ingredient_risks: list[dict] = []
    if ingredients and conditions:
        try:
            ingredient_risks = analyse_ingredients_for_conditions(ingredients, conditions)
        except Exception as e:
            logger.warning(f"[AI-Score] Ingredient analysis failed: {e}")

    # Convert ingredient risks to violation dicts (Part 4)
    ing_risk_violations = ingredient_risks_to_violations(ingredient_risks)

    # ── Merge all violations then deduplicate (Part 5 & 6) ────────────────────
    all_violations_raw = violations + ai_violations + ing_risk_violations
    all_violations     = deduplicate_violations(all_violations_raw)
    logger.info(f"[SCORE] Raw violations: {len(all_violations_raw)} → "
                f"deduplicated: {len(all_violations)}")

    health_score    = calculate_health_score(all_violations, ingredient_deduct + allergy_deduct)
    risk_level_info = get_risk_level(health_score)

    # ── Part 10: Score floor from ingredient risk ──────────────────────────────
    # If OCR extracted few/no nutrition facts but harmful ingredients exist,
    # prevent the score from being falsely "Safe".
    if len(non_null_nutrition) < 3:
        health_score = apply_ingredient_score_floor(health_score, ingredient_risks)
        risk_level_info = get_risk_level(health_score)

    # Bonus points for beneficial nutrients (fiber, protein)
    # Cap: max 5 pts total. Suppressed entirely when total deductions exceed 20 pts.
    total_deduction_for_bonus = sum(v["deduction"] for v in all_violations) + ingredient_deduct + allergy_deduct
    if total_deduction_for_bonus <= 20:
        fiber   = non_null_nutrition.get("fiber", 0) or 0
        protein = non_null_nutrition.get("protein", 0) or 0
        bonus   = min(int(fiber * 0.5) + min(int(protein * 0.25), 2), 5)
        health_score = min(health_score + bonus, 100)
    else:
        bonus = 0
        logger.info(f"[SCORE] Bonus suppressed — total deductions ({total_deduction_for_bonus}) > 20")

    logger.info(f"STEP 4 DONE — score={health_score} level={risk_level_info['level']}")

    # ── STEP 5: Report assembly ───────────────────────────────────────────────
    reasons           = build_reasons(all_violations, ing_triggers, health_dict)
    threshold_summary = build_threshold_summary(all_violations)

    # ── Score explanation (Req 4) ─────────────────────────────────────────────
    # Each line: what was deducted, which nutrient, why, exact values
    score_explanation_parts: list[str] = ["Starting score: 100"]
    seen_expl_nutrients: set[str] = set()

    for v in sorted(all_violations, key=lambda x: -x["deduction"])[:8]:
        nutrient_key = f"{v['condition']}|{v['nutrient']}"
        if nutrient_key in seen_expl_nutrients:
            continue
        seen_expl_nutrients.add(nutrient_key)

        unit      = v.get("unit", "")                # already canonical
        val_str   = format_nutrient(v["user_value"], v["nutrient"], "")   # Bug 1 fix
        limit_str = format_nutrient(v["threshold"],  v["nutrient"], "")   # Bug 1 fix
        deduct    = v["deduction"]
        restr     = v.get("restriction_level", "")
        pct       = v.get("pct_of_limit", 0)        # Bug 2: already correct from _make_violation

        if v["threshold"] == 0:
            line = (
                f"−{deduct} pts | {v['condition']}: {v['nutrient']} present "
                f"({val_str}) — must be zero for this condition ({restr})"
            )
        else:
            line = (
                f"−{deduct} pts | {v['condition']}: {v['nutrient']} = {val_str} "
                f"(limit {limit_str}/day, {pct}% of daily allowance, {restr} rule)"
            )
        score_explanation_parts.append(line)

    for t in ing_triggers[:3]:
        score_explanation_parts.append(
            f"−{t['deduction']} pts | Ingredient: {t['ingredient']} "
            f"({t['condition']} — {t.get('reason', 'flagged ingredient')})"
        )

    if bonus > 0:
        fiber_val   = non_null_nutrition.get("fiber", 0) or 0
        protein_val = non_null_nutrition.get("protein", 0) or 0
        score_explanation_parts.append(
            f"+{bonus} pts | Nutrition bonus: "
            f"fiber {fiber_val}g, protein {protein_val}g"
        )
    score_explanation_parts.append(f"Final Score: {health_score}/100")

    # ── Recommendations (Req 2 & 3) ───────────────────────────────────────────
    recs = get_recommendations(
        conditions,
        ingredients,
        100 - health_score,
        violations=all_violations,
        health_score=health_score,
    )

    # ── Final recommendation paragraph (Parts 5, 9) ──────────────────────────
    final_recommendation = _final_recommendation(
        health_score, conditions, disease_impacts, all_violations, health_dict
    )
    # Part 9: Append ingredient-based recommendation if it adds new information
    logger.info(f"[SCORE] display_conditions={display_conditions}")
    ing_reco = build_ingredient_recommendation(ingredient_risks, display_conditions, health_score)
    if ing_reco and ing_reco.lower() not in final_recommendation.lower():
        final_recommendation = final_recommendation.rstrip(".") + " " + ing_reco

    return {
        # ── Step 1 output ──────────────────────────────────────────────────
        "product_name":       product_name,
        "ingredients":        ingredients,
        "nutrition_facts":    non_null_nutrition,
        "raw_ocr_snippet":    ocr_text[:300],

        # ── Step 2 output ──────────────────────────────────────────────────
        "nutrient_evaluation": nutrient_evaluation,

        # ── Step 3 output ──────────────────────────────────────────────────
        "disease_impact":      disease_impacts,
        "ingredient_analysis": ingredient_risks,   # Part 3 & 8: per-ingredient risk

        # ── Step 4 output ──────────────────────────────────────────────────
        "health_score":        health_score,
        "risk_level":          risk_level_info["level"],
        "risk_color":          risk_level_info["color"],
        "risk_advice":         risk_level_info["advice"],
        "score_explanation":   score_explanation_parts,
        "threshold_summary":   threshold_summary,

        # ── Step 5 output ──────────────────────────────────────────────────
        "reasons":             reasons,
        "affected_conditions": display_conditions,
        "allergy_alerts":      allergy_alerts,
        "has_critical_allergen": any(a.get("severity") == "Severe" for a in allergy_alerts),
        "foods_to_avoid":      recs["foods_to_avoid"],
        "better_alternatives": recs["better_alternatives"],
        "recommended_foods":   recs["recommended_foods"],
        "serving_advice":      recs["serving_advice"],
        "final_recommendation": final_recommendation,

        # User context
        "user_conditions":  display_conditions,
        "personalized_for": current_user.name,
        "user_bp":    f"{health_dict.get('systolic')}/{health_dict.get('diastolic')}" if health_dict.get("systolic") else None,
        "user_sugar": health_dict.get("fasting_sugar"),
        "user_bmi":   health_dict.get("bmi_score"),
    }


@router.post("/extract-ocr")
async def extract_ocr_only(file: UploadFile = File(...),
                            current_user: User = Depends(get_current_user)):
    """OCR only — for testing."""
    image_bytes = await file.read()
    try:
        text   = extract_text_from_image(image_bytes)
        parsed = parse_food_label(text)
        return {"raw_text": text, **parsed}
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/debug-score")
def debug_score(nutrition: dict, db: Session = Depends(get_db)):
    """Debug endpoint — no auth. Pass nutrition JSON, returns full evaluation."""
    from app.models.user import User as UserModel
    user = db.query(UserModel).first()
    if not user:
        return {"error": "No users in database."}
    profile     = db.query(HealthProfile).filter(HealthProfile.user_id == user.id).first()
    health_dict = _build_health_dict(user, profile)
    conditions  = _get_user_conditions(health_dict)
    nutrient_eval   = evaluate_all_nutrients(nutrition)
    disease_impacts = analyze_all_conditions(conditions, nutrition, health_dict)
    violations, _   = analyze_with_health_r(nutrition, health_dict)
    score = calculate_health_score(violations, 0)
    level = get_risk_level(score)
    return {
        "tested_user":      user.name,
        "user_bp":          f"{health_dict.get('systolic')}/{health_dict.get('diastolic')}",
        "conditions":       conditions,
        "health_score":     score,
        "risk_level":       level["level"],
        "nutrient_eval":    [{e["nutrient"]: e["status"]} for e in nutrient_eval],
        "disease_impacts":  [{d["condition"]: d["overall_impact"]} for d in disease_impacts],
        "violations":       [{"n": v["nutrient"], "val": v["user_value"],
                              "limit": v["threshold"], "deduct": v["deduction"]} for v in violations],
    }


@router.get("/recommendations")
def get_user_recommendations(current_user: User = Depends(get_current_user),
                              db: Session = Depends(get_db)):
    profile     = db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()
    health_dict = _build_health_dict(current_user, profile)
    conditions  = _get_user_conditions(health_dict)
    return {"conditions": conditions, "recommendations": get_recommendations(conditions, [], 0)}
