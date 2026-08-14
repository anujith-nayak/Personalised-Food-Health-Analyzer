"""
Evidence-Based Recommendation Engine
====================================
Combines blood report conditions, scanned food nutrients, and user disease profile.
Produces merged personalized food recommendations using non-diagnostic, evidence-backed language.
"""

import logging
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from app.services.knowledge_base.database import KBSessionLocal
from app.services.knowledge_base.knowledge_service import (
    get_conditions_from_report,
    get_nutrition_actions,
    get_food_recommendations,
)

logger = logging.getLogger(__name__)


def generate_biomarker_reason(parameter: str, condition: str) -> str:
    """
    Generate non-diagnostic, professional reason phrasing for blood report findings.
    """
    if condition == "High":
        if parameter == "HbA1c":
            return "HbA1c is above the reference range."
        elif parameter == "Hemoglobin":
            return "Hemoglobin is above reference range."
        elif parameter == "LDL":
            return "LDL cholesterol is elevated."
        elif parameter == "Fasting Blood Sugar":
            return "Fasting blood sugar level is elevated."
        elif parameter == "Triglycerides":
            return "Triglycerides are above reference range."
        elif parameter == "Creatinine":
            return "Serum creatinine level is elevated."
        elif parameter == "Uric Acid":
            return "Serum uric acid level is elevated."
        else:
            return f"{parameter} is above the reference range."
    elif condition == "Low":
        if parameter == "eGFR":
            return "Estimated glomerular filtration rate (eGFR) is below reference range."
        elif parameter == "HDL":
            return "HDL cholesterol is below target levels."
        else:
            return f"{parameter} level is below the reference range."
    return f"{parameter} level requires monitoring."


def generate_action_summary(action: str, nutrient: str) -> str:
    """Generate concise recommendation headline."""
    if action in ("Limit", "Avoid"):
        if action == "Avoid":
            return f"Avoid foods high in {nutrient}"
        return f"Limit {nutrient}-rich foods"
    elif action == "Increase":
        return f"Increase foods rich in {nutrient}"
    return f"Monitor {nutrient} intake"


class KnowledgeBaseRecommendationEngine:
    """
    Merges blood biomarker findings with scanned food nutrients and user disease profile.
    """

    def __init__(self, db: Optional[Session] = None):
        self.db = db

    def generate_recommendations(
        self,
        blood_report_values: Optional[Dict[str, float]] = None,
        blood_conditions: Optional[List[Dict[str, Any]]] = None,
        food_nutrients: Optional[Dict[str, Any]] = None,
        disease_conditions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Main recommendation generation entrypoint.
        """
        db = self.db or KBSessionLocal()
        close_db = self.db is None

        try:
            # 1. Interpret blood report values if raw dict provided
            interpreted_conditions: List[Dict[str, Any]] = []
            if blood_conditions:
                interpreted_conditions = blood_conditions
            elif blood_report_values:
                interpreted_conditions = get_conditions_from_report(blood_report_values, db=db)

            # 2. Get evidence-based nutrition actions from DB
            nutrition_actions = get_nutrition_actions(interpreted_conditions, db=db)

            # 3. Get food examples from DB
            food_examples = get_food_recommendations(nutrition_actions, db=db)

            # 4. Process Avoid / Limit / Increase lists
            avoid_set = set()
            limit_set = set()
            increase_set = set()
            reasons: List[str] = []
            biomarker_analysis: List[Dict[str, Any]] = []

            for cond_item in interpreted_conditions:
                p_name = cond_item.get("parameter", "")
                c_name = cond_item.get("condition", "")
                reason_phrase = generate_biomarker_reason(p_name, c_name)
                if reason_phrase not in reasons:
                    reasons.append(reason_phrase)

            for act in nutrition_actions:
                action_type = act.get("action", "")
                nutrient = act.get("nutrient", "")
                param = act.get("parameter", "")
                cond = act.get("condition", "")

                if action_type == "Avoid":
                    avoid_set.add(nutrient)
                elif action_type == "Limit":
                    limit_set.add(nutrient)
                elif action_type == "Increase":
                    increase_set.add(nutrient)

                # Format biomarker item for frontend display
                val_str = f"{act['user_value']} {act['unit']}".strip() if act.get("user_value") is not None else ""
                reco_str = generate_action_summary(action_type, nutrient)

                biomarker_analysis.append({
                    "parameter": param,
                    "value": val_str,
                    "condition": cond,
                    "nutrient": nutrient,
                    "action": action_type,
                    "recommendation": reco_str,
                    "severity": act.get("severity", "Medium"),
                    "reason": act.get("reason", ""),
                    "source": act.get("evidence_source", ""),
                    "organization": act.get("organization", ""),
                    "url": act.get("url", ""),
                })

            # Format food examples by action
            foods_to_avoid = [
                f"{fe['food_name']} ({fe['category']})"
                for fe in food_examples if fe["action"] in ("Avoid", "Limit")
            ]
            foods_to_increase = [
                f"{fe['food_name']} ({fe['category']})"
                for fe in food_examples if fe["action"] == "Increase"
            ]

            return {
                "avoid": sorted(list(avoid_set)),
                "limit": sorted(list(limit_set)),
                "increase": sorted(list(increase_set)),
                "reasons": reasons,
                "biomarker_analysis": biomarker_analysis,
                "food_examples": {
                    "avoid_or_limit": foods_to_avoid,
                    "increase": foods_to_increase,
                },
            }

        finally:
            if close_db:
                db.close()
