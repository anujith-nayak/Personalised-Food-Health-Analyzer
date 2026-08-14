"""
Blood Parameter Interpreter
===========================
Evaluates numeric lab test results against reference ranges retrieved dynamically
from the SQLite database (`blood_parameters` table). No hardcoded thresholds.
"""

import logging
from typing import Dict, List, Any
from sqlalchemy.orm import Session
from app.services.knowledge_base.database import BloodParameter, KBSessionLocal

logger = logging.getLogger(__name__)

# Normalize parameter alias mappings to canonical database parameter names
ALIAS_MAP: Dict[str, str] = {
    "hemoglobin": "Hemoglobin",
    "hb": "Hemoglobin",
    "hgb": "Hemoglobin",
    "hba1c": "HbA1c",
    "a1c": "HbA1c",
    "glycated_hemoglobin": "HbA1c",
    "fasting_glucose": "Fasting Blood Sugar",
    "fasting_sugar": "Fasting Blood Sugar",
    "fasting_blood_sugar": "Fasting Blood Sugar",
    "fbs": "Fasting Blood Sugar",
    "random_glucose": "Random Blood Sugar",
    "random_sugar": "Random Blood Sugar",
    "random_blood_sugar": "Random Blood Sugar",
    "rbs": "Random Blood Sugar",
    "ldl": "LDL",
    "ldl_cholesterol": "LDL",
    "hdl": "HDL",
    "hdl_cholesterol": "HDL",
    "total_cholesterol": "Total Cholesterol",
    "cholesterol": "Total Cholesterol",
    "triglycerides": "Triglycerides",
    "triglyceride": "Triglycerides",
    "creatinine": "Creatinine",
    "serum_creatinine": "Creatinine",
    "egfr": "eGFR",
    "gfr": "eGFR",
    "potassium": "Potassium",
    "serum_potassium": "Potassium",
    "sodium": "Sodium",
    "serum_sodium": "Sodium",
    "calcium": "Calcium",
    "serum_calcium": "Calcium",
    "iron": "Iron",
    "serum_iron": "Iron",
    "ferritin": "Ferritin",
    "serum_ferritin": "Ferritin",
    "vitamin_d": "Vitamin D",
    "vit_d": "Vitamin D",
    "25_hydroxy_vitamin_d": "Vitamin D",
    "vitamin_b12": "Vitamin B12",
    "vit_b12": "Vitamin B12",
    "b12": "Vitamin B12",
    "alt": "ALT",
    "sgpt": "ALT",
    "ast": "AST",
    "sgot": "AST",
    "uric_acid": "Uric Acid",
    "serum_uric_acid": "Uric Acid",
}


def normalize_parameter_name(name: str) -> str:
    """Normalize input key to canonical DB parameter_name."""
    clean = str(name).strip().lower().replace("-", "_").replace(" ", "_")
    return ALIAS_MAP.get(clean, str(name).strip())


def interpret_blood_parameters(
    report_values: Dict[str, float], db: Session = None
) -> List[Dict[str, Any]]:
    """
    Input:
      {
        "Hemoglobin": 18.1,
        "HbA1c": 7.4,
        "LDL": 180
      }

    Output:
      [
        {
          "parameter": "Hemoglobin",
          "condition": "High",
          "value": 18.1,
          "unit": "g/dL",
          "normal_range": "13.5 - 17.5 g/dL"
        },
        ...
      ]

    Queries SQLite database `blood_parameters` for `normal_low` and `normal_high`.
    Contains NO hardcoded numerical thresholds.
    """
    close_at_end = False
    if db is None:
        db = KBSessionLocal()
        close_at_end = True

    try:
        # Load all parameter reference ranges from database
        all_params = db.query(BloodParameter).all()
        param_map: Dict[str, BloodParameter] = {
            p.parameter_name.lower(): p for p in all_params
        }

        results: List[Dict[str, Any]] = []

        for key, val in report_values.items():
            if val is None:
                continue
            try:
                numeric_val = float(val)
            except (ValueError, TypeError):
                continue

            canonical_name = normalize_parameter_name(key)
            param_obj = param_map.get(canonical_name.lower())

            if not param_obj:
                # Try direct matching
                for p in all_params:
                    if p.parameter_name.lower() == str(key).strip().lower():
                        param_obj = p
                        break

            if not param_obj:
                logger.debug(f"[Interpreter] Parameter '{key}' not found in DB reference table.")
                continue

            condition = "Normal"
            if numeric_val > param_obj.normal_high:
                condition = "High"
            elif numeric_val < param_obj.normal_low:
                condition = "Low"

            if condition != "Normal":
                results.append({
                    "parameter": param_obj.parameter_name,
                    "display_name": param_obj.display_name,
                    "condition": condition,
                    "value": numeric_val,
                    "unit": param_obj.unit,
                    "normal_low": param_obj.normal_low,
                    "normal_high": param_obj.normal_high,
                    "normal_range": f"{param_obj.normal_low} - {param_obj.normal_high} {param_obj.unit}",
                })

        return results

    finally:
        if close_at_end:
            db.close()
