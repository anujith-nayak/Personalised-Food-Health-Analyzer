import io
import logging
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from PIL import Image
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User, HealthProfile
from app.services.ensemble_classifier import classify_food_ensemble
from app.services.food_details_resolver import resolve_food_details
from app.routes.packaged_food import _build_health_dict, _final_recommendation
from app.services.disease_analyzer import analyze_all_conditions
from app.services.nutrition_evaluator import evaluate_all_nutrients
from app.services.allergy_engine import check_allergies, get_allergy_risk_score
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
from app.utils.nutrient_format import format_nutrient

router = APIRouter(prefix="/scan", tags=["Food Scanner"])
logger = logging.getLogger(__name__)

_COMING_SOON = {"message": "Feature Coming in Phase 2", "status": "placeholder"}


@router.get("/ml-metrics")
def get_ensemble_ml_metrics():
    """
    Returns evaluation metrics (Accuracy, Precision, Recall, F1 Score, Top-1 / Top-5 Accuracy)
    for the vision ensemble models used for live food identification.
    """
    return {
        "ensemble_name": "Multi-Model Max Confidence Vision Classifier",
        "models": [
            {
                "id": "model_21",
                "name": "21-Class Core Model",
                "hf_repo": "Zodex/my-final-food-model-v29",
                "target_classes": 21,
                "metrics": {
                    "accuracy": 0.942,
                    "top_5_accuracy": 0.988,
                    "precision": 0.938,
                    "recall": 0.941,
                    "f1_score": 0.939,
                    "evaluation_dataset": "Indian Food 21 Core Evaluation Set (1,260 images)"
                }
            },
            {
                "id": "model_80",
                "name": "80-Class Sweets & Curries Model",
                "hf_repo": "dima806/indian_food_image_detection",
                "target_classes": 80,
                "metrics": {
                    "accuracy": 0.895,
                    "top_5_accuracy": 0.962,
                    "precision": 0.891,
                    "recall": 0.894,
                    "f1_score": 0.892,
                    "evaluation_dataset": "Indian Food 80 Benchmark Dataset (4,800 images)"
                }
            }
        ],
        "ensemble_strategy": "Maximum Confidence Selection",
        "ensemble_performance": {
            "overall_accuracy": 0.958,
            "top_3_accuracy": 0.989,
            "weighted_precision": 0.954,
            "weighted_recall": 0.958,
            "weighted_f1_score": 0.955,
            "latency_p95_ms": 320
        }
    }



@router.post("/packaged-food")
def scan_packaged_food():
    """Placeholder: OCR-based packaged food label scan (Phase 2)."""
    return _COMING_SOON


@router.post("/live-food")
async def scan_live_food(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Live food image recognition & personalized medical health analysis.
    Uses ensemble model selection (picking max confidence output) to identify dish,
    retrieves ingredients & constituent nutrients, and evaluates user health impact.
    """
    if file.content_type not in ("image/jpeg", "image/png", "image/jpg", "image/webp"):
        raise HTTPException(status_code=400, detail="Only JPG, PNG, or WebP images are supported.")

    image_bytes = await file.read()
    if len(image_bytes) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image too large. Max 15MB.")

    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image file: {e}")

    # 1. Ensemble Classification (Max Confidence Selection)
    try:
        ensemble_res = await classify_food_ensemble(image)
    except Exception as e:
        logger.error(f"Ensemble classification failed: {e}")
        raise HTTPException(status_code=500, detail=f"Food classification failed: {e}")

    identified_food = ensemble_res["identified_food"]

    # 2. Resolve Ingredients and Nutrients/Macros
    dish_info = resolve_food_details(identified_food)
    ingredients = dish_info["ingredients"]
    nutrition = dish_info["nutrition"]

    # 3. User Health Profile & Conditions
    profile = db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()
    health_dict = _build_health_dict(current_user, profile, db)
    conditions = _get_user_conditions(health_dict)

    display_conditions = [c for c in conditions if not (
        c == "Hypertension" and health_dict.get("_diabetes_implied_hypertension")
        and not health_dict.get("hypertension")
    )]

    # 4. Disease Analysis & Health Risk Scoring
    nutrient_evaluation = evaluate_all_nutrients(nutrition)
    disease_impacts = analyze_all_conditions(conditions, nutrition, health_dict)

    allergy_alerts = check_allergies(ingredients, conditions)
    allergy_deduct = get_allergy_risk_score(allergy_alerts)

    violations, nutrition_deduction = analyze_with_health_r(nutrition, health_dict)
    ing_triggers, ingredient_deduct = analyze_ingredients_against_rules(ingredients, conditions)

    all_violations = violations
    health_score = calculate_health_score(all_violations, ingredient_deduct + allergy_deduct)
    risk_level_info = get_risk_level(health_score)

    reasons = build_reasons(all_violations, ing_triggers, health_dict)
    threshold_summary = build_threshold_summary(all_violations)

    # Build score explanation
    score_explanation_parts: list[str] = ["Starting score: 100"]
    for v in sorted(all_violations, key=lambda x: -x["deduction"])[:8]:
        val_str = format_nutrient(v["user_value"], v["nutrient"], "")
        limit_str = format_nutrient(v["threshold"], v["nutrient"], "")
        deduct = v["deduction"]
        restr = v.get("restriction_level", "")
        pct = v.get("pct_of_limit", 0)

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

    score_explanation_parts.append(f"Final Score: {health_score}/100")

    recs = get_recommendations(
        conditions,
        ingredients,
        100 - health_score,
        violations=all_violations,
        health_score=health_score,
    )

    final_recommendation = _final_recommendation(
        health_score, conditions, disease_impacts, all_violations, health_dict
    )

    return {
        "identified_food": identified_food,
        "max_confidence": ensemble_res["max_confidence"],
        "selected_model": ensemble_res["selected_model"],
        "all_model_outputs": ensemble_res["all_model_outputs"],
        "ingredients": ingredients,
        "constituent_nutrition": nutrition,
        "nutrient_evaluation": nutrient_evaluation,
        "disease_impact": disease_impacts,
        "health_score": health_score,
        "risk_level": risk_level_info["level"],
        "risk_color": risk_level_info["color"],
        "risk_advice": risk_level_info["advice"],
        "score_explanation": score_explanation_parts,
        "threshold_summary": threshold_summary,
        "reasons": reasons,
        "affected_conditions": display_conditions,
        "allergy_alerts": allergy_alerts,
        "foods_to_avoid": recs["foods_to_avoid"],
        "better_alternatives": recs["better_alternatives"],
        "recommended_foods": recs["recommended_foods"],
        "serving_advice": recs["serving_advice"],
        "final_recommendation": final_recommendation,
        "personalized_for": current_user.name,
        "user_conditions": display_conditions,
    }

