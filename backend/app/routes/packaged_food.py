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

router = APIRouter(prefix="/food", tags=["Packaged Food Analysis"])
logger = logging.getLogger(__name__)


def _build_health_dict(user: User, profile: HealthProfile | None) -> dict:
    data = {"bmi_score": user.bmi_score, "bmi_category": user.bmi_category}
    if profile:
        data.update({
            "hypertension":    profile.hypertension,
            "bp_status":       profile.bp_status,
            "systolic":        profile.systolic,
            "diastolic":       profile.diastolic,
            "diabetes":        profile.diabetes,
            "sugar_status":    profile.sugar_status,
            "fasting_sugar":   profile.fasting_sugar,
            "post_meal_sugar": profile.post_meal_sugar,
            "thyroid":         profile.thyroid,
            "thyroid_type":    profile.thyroid_type,
            "pcos":            profile.pcos,
            "pcod":            profile.pcod,
            "heart_disease":   profile.heart_disease,
            "kidney_disease":  profile.kidney_disease,
            "obesity":         profile.obesity,
        })
    return data


def _final_recommendation(score: int, conditions: list[str], disease_impacts: list[dict]) -> str:
    """Generate a plain-language final recommendation."""
    if score >= 81:
        verdict = "Generally safe for occasional consumption."
    elif score >= 61:
        verdict = "Consume in small portions occasionally."
    elif score >= 41:
        verdict = "Limit consumption. Healthier alternatives are recommended."
    elif score >= 21:
        verdict = "Not recommended for regular consumption."
    else:
        verdict = "Avoid this product. It is not suitable for your health conditions."

    # Add condition-specific advice
    extras = []
    for d in disease_impacts:
        if d["impact_color"] in ("orange", "red") and d["concerns"]:
            top = d["concerns"][0]["message"]
            extras.append(f"For {d['condition']}: {top}")

    if extras:
        return verdict + " " + " ".join(extras[:3])
    return verdict


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

    disease_impacts = analyze_all_conditions(conditions, non_null_nutrition)
    logger.info(f"STEP 3 DONE — conditions={conditions}")

    # ── STEP 4: Allergy check + personalized score ────────────────────────────
    logger.info("STEP 4: Calculating personalized health score")
    allergy_alerts   = check_allergies(ingredients, conditions)
    allergy_deduct   = get_allergy_risk_score(allergy_alerts)

    violations, nutrition_deduction = analyze_with_health_r(non_null_nutrition, health_dict)
    ing_triggers, ingredient_deduct  = analyze_ingredients_against_rules(ingredients, conditions)

    health_score     = calculate_health_score(violations, ingredient_deduct + allergy_deduct)
    risk_level_info  = get_risk_level(health_score)

    # Bonus points for beneficial nutrients (fiber, protein)
    fiber   = non_null_nutrition.get("fiber", 0) or 0
    protein = non_null_nutrition.get("protein", 0) or 0
    bonus   = min(int(fiber * 2) + min(int(protein), 5), 10)
    health_score = min(health_score + bonus, 100)

    logger.info(f"STEP 4 DONE — score={health_score} level={risk_level_info['level']}")

    # ── STEP 5: Report assembly ───────────────────────────────────────────────
    reasons           = build_reasons(violations, ing_triggers, health_dict)
    threshold_summary = build_threshold_summary(violations)

    # Score explanation
    score_explanation_parts = ["Starting score: 100"]
    for v in sorted(violations, key=lambda x: -x["deduction"])[:6]:
        score_explanation_parts.append(
            f"{v['condition']} — {v['nutrient']} {v['user_value']}{v['unit']} "
            f"(limit {v['threshold']}{v['unit']}): -{v['deduction']} pts"
        )
    if bonus > 0:
        score_explanation_parts.append(f"Fiber/Protein bonus: +{bonus} pts")
    score_explanation_parts.append(f"Final Score: {health_score}/100")

    recs = get_recommendations(conditions, ingredients, 100 - health_score)
    final_recommendation = _final_recommendation(health_score, conditions, disease_impacts)

    # Remove implied conditions from display
    display_conditions = [c for c in conditions if not (
        c == "Hypertension" and health_dict.get("_diabetes_implied_hypertension")
        and not health_dict.get("hypertension")
    )]

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
    disease_impacts = analyze_all_conditions(conditions, nutrition)
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
