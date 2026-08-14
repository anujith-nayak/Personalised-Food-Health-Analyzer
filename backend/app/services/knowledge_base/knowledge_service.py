"""
Knowledge Base Service Layer
============================
Encapsulates database queries for:
- get_conditions_from_report()
- get_nutrition_actions()
- get_food_recommendations()

All queries execute against SQLite via SQLAlchemy ORM.
"""

import logging
from typing import Dict, List, Any
from sqlalchemy.orm import Session
from app.services.knowledge_base.database import (
    KBSessionLocal,
    BloodParameter,
    BloodParameterCondition,
    NutritionAction,
    FoodExample,
    Reference,
)
from app.services.knowledge_base.blood_parameter_interpreter import (
    interpret_blood_parameters,
)

logger = logging.getLogger(__name__)


def get_conditions_from_report(
    report_values: Dict[str, float], db: Session = None
) -> List[Dict[str, Any]]:
    """
    Given a dictionary of lab parameter values, returns interpreted parameter conditions.
    Uses database-backed blood parameter thresholds.
    """
    return interpret_blood_parameters(report_values, db=db)


def get_nutrition_actions(
    conditions: List[Dict[str, Any]], db: Session = None
) -> List[Dict[str, Any]]:
    """
    Input:
      [
        {"parameter": "Hemoglobin", "condition": "High"},
        {"parameter": "HbA1c", "condition": "High"},
        {"parameter": "LDL", "condition": "High"}
      ]

    Output:
      List of dicts containing nutrition action details, severity, reason, and scientific evidence source with citation URL.
    """
    close_at_end = False
    if db is None:
        db = KBSessionLocal()
        close_at_end = True

    try:
        results: List[Dict[str, Any]] = []

        # Load references map
        references = db.query(Reference).all()
        ref_map: Dict[str, Reference] = {r.evidence_source: r for r in references}

        for item in conditions:
            param_name = item.get("parameter")
            cond_name = item.get("condition")
            if not param_name or not cond_name:
                continue

            actions = (
                db.query(NutritionAction)
                .filter(
                    NutritionAction.parameter_name == param_name,
                    NutritionAction.condition_name == cond_name,
                )
                .all()
            )

            for act in actions:
                ref_obj = ref_map.get(act.evidence_source)
                results.append({
                    "parameter": act.parameter_name,
                    "condition": act.condition_name,
                    "nutrient": act.nutrient,
                    "action": act.action,
                    "severity": act.severity,
                    "reason": act.reason,
                    "evidence_source": act.evidence_source,
                    "organization": ref_obj.organization if ref_obj else act.evidence_source,
                    "guideline": ref_obj.guideline if ref_obj else "",
                    "url": ref_obj.url if ref_obj else "",
                    "user_value": item.get("value"),
                    "unit": item.get("unit", ""),
                })

        return results

    finally:
        if close_at_end:
            db.close()


def get_food_recommendations(
    nutrition_actions: List[Dict[str, Any]], db: Session = None
) -> List[Dict[str, Any]]:
    """
    Queries `food_examples` table for matching nutrient and action.
    """
    close_at_end = False
    if db is None:
        db = KBSessionLocal()
        close_at_end = True

    try:
        food_recs: List[Dict[str, Any]] = []
        seen_foods = set()

        for act in nutrition_actions:
            nutrient = act.get("nutrient")
            action = act.get("action")
            if not nutrient or not action:
                continue

            examples = (
                db.query(FoodExample)
                .filter(
                    FoodExample.nutrient == nutrient,
                    FoodExample.action == action,
                )
                .all()
            )

            for ex in examples:
                key = (ex.nutrient, ex.action, ex.food_name)
                if key in seen_foods:
                    continue
                seen_foods.add(key)
                food_recs.append({
                    "nutrient": ex.nutrient,
                    "action": ex.action,
                    "food_name": ex.food_name,
                    "category": ex.category,
                    "reason": act.get("reason", ""),
                    "evidence_source": act.get("evidence_source", ""),
                })

        return food_recs

    finally:
        if close_at_end:
            db.close()
