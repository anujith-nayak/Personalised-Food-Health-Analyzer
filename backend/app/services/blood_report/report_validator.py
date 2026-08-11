"""
Blood Report Validator
======================
Validates extracted medical parameters against plausible range bounds.
Assigns validation status flags ('Valid', 'Needs Review', 'Review') without
automatically overwriting or falsifying medical data.
"""

import logging
from typing import Dict, List, Any
from app.services.blood_report.report_parser import load_blood_report_aliases

logger = logging.getLogger(__name__)


def validate_extracted_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Validates a list of extracted blood report parameters.
    Returns list of dicts with assigned 'status' fields.
    """
    alias_config = load_blood_report_aliases()
    validated: List[Dict[str, Any]] = []

    for item in results:
        param_key = item.get("parameter_key")
        val = item.get("value")
        is_known = item.get("is_known_alias", False) or (param_key in alias_config)

        if val is None:
            status = "Needs Review"
        elif is_known:
            info = alias_config.get(param_key, {})
            min_p = info.get("min_plausible", 0.0)
            max_p = info.get("max_plausible", 99999.0)

            if not (min_p <= val <= max_p):
                logger.warning(
                    f"[BLOOD_VALIDATOR] Parameter '{param_key}' value {val} is outside plausible range "
                    f"[{min_p}, {max_p}]. Flagged for user review."
                )
                status = "Needs Review"
            else:
                status = "Valid"
        else:
            # Unlisted / unknown parameters default to 'Review' so user can inspect during review
            status = "Review"

        validated_item = dict(item)
        validated_item["status"] = status
        validated.append(validated_item)

    return validated
