"""
Blood Report Service
====================
Core business logic & DB operations for optional blood report upload, parsing,
user confirmation, deletion, and merging into health-profile food personalization.
"""

import os
import shutil
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session

from app.models.blood_report import BloodReport, BloodReportResult
from app.services.blood_report.report_ocr import extract_structured_blood_report_ocr
from app.services.blood_report.report_parser import BloodReportParser, normalize_parameter_key
from app.services.blood_report.report_validator import validate_extracted_results

logger = logging.getLogger(__name__)

# Private storage directory for sensitive report files
STORAGE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "storage", "blood_reports")
)


def _ensure_storage_dir():
    os.makedirs(STORAGE_DIR, exist_ok=True)


def process_report_upload(
    db: Session, user_id: int, file_bytes: bytes, file_name: str
) -> Dict[str, Any]:
    """
    Validates, saves file privately, runs structured OCR + parser + validator, and stores
    unconfirmed BloodReport and BloodReportResult entries in DB.
    """
    _ensure_storage_dir()
    fn_lower = file_name.lower()
    allowed_exts = (".pdf", ".jpg", ".jpeg", ".png")

    if not fn_lower.endswith(allowed_exts):
        raise ValueError(f"Invalid file type '{file_name}'. Supported formats: PDF, JPG, JPEG, PNG.")

    max_bytes = 10 * 1024 * 1024  # 10MB limit
    if len(file_bytes) > max_bytes:
        raise ValueError("File size exceeds maximum allowed limit of 10MB.")

    if len(file_bytes) == 0:
        raise ValueError("Uploaded file is empty.")

    # Save file privately on disk
    timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_name = f"user_{user_id}_{timestamp_str}_{os.path.basename(file_name)}"
    file_path = os.path.join(STORAGE_DIR, safe_name)

    with open(file_path, "wb") as f:
        f.write(file_bytes)

    # Structured OCR + Parsing
    ocr_result = extract_structured_blood_report_ocr(file_bytes, file_name)
    parser = BloodReportParser()
    raw_extracted = parser.parse_ocr_result(ocr_result)
    validated_results = validate_extracted_results(raw_extracted)

    # Archive previous unconfirmed reports for this user
    db.query(BloodReport).filter(
        BloodReport.user_id == user_id, BloodReport.status == "pending"
    ).delete(synchronize_session=False)

    # Create new BloodReport entry
    report_type = "pdf" if fn_lower.endswith(".pdf") else "image"
    report = BloodReport(
        user_id=user_id,
        file_name=file_name,
        file_path=file_path,
        file_type=report_type,
        status="pending",
    )
    db.add(report)
    db.flush()

    # Create unconfirmed BloodReportResult entries
    db_results = []
    for item in validated_results:
        res = BloodReportResult(
            report_id=report.id,
            user_id=user_id,
            parameter_key=item["parameter_key"],
            display_name=item["display_name"],
            value=item["value"],
            unit=item["unit"],
            reference_range=item["reference_range"],
            status=item["status"],
            confirmed_by_user=False,
        )
        db.add(res)
        db_results.append(res)

    db.commit()
    db.refresh(report)

    return {
        "report_id": report.id,
        "file_name": report.file_name,
        "uploaded_at": report.uploaded_at.isoformat(),
        "status": report.status,
        "results": [
            {
                "id": r.id,
                "parameter_key": r.parameter_key,
                "display_name": r.display_name,
                "value": r.value,
                "unit": r.unit,
                "reference_range": r.reference_range,
                "status": r.status,
                "confirmed_by_user": r.confirmed_by_user,
            }
            for r in db_results
        ],
    }


def get_user_blood_report(db: Session, user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves current user's active blood report and its results."""
    report = (
        db.query(BloodReport)
        .filter(BloodReport.user_id == user_id)
        .order_by(BloodReport.uploaded_at.desc())
        .first()
    )

    if not report:
        return None

    results = (
        db.query(BloodReportResult)
        .filter(BloodReportResult.report_id == report.id)
        .all()
    )

    return {
        "report_id": report.id,
        "file_name": report.file_name,
        "uploaded_at": report.uploaded_at.isoformat(),
        "status": report.status,
        "results": [
            {
                "id": r.id,
                "parameter_key": r.parameter_key,
                "display_name": r.display_name,
                "value": r.value,
                "unit": r.unit,
                "reference_range": r.reference_range,
                "status": r.status,
                "confirmed_by_user": r.confirmed_by_user,
            }
            for r in results
        ],
    }


def confirm_report_results(
    db: Session, user_id: int, report_id: int, confirmed_items: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Saves user-reviewed lab parameters as confirmed data (confirmed_by_user = True).
    Supports both known and unlisted/custom parameter keys without discarding them.
    Marks report status as 'confirmed'.
    """
    report = (
        db.query(BloodReport)
        .filter(BloodReport.id == report_id, BloodReport.user_id == user_id)
        .first()
    )

    if not report:
        raise ValueError(f"Report ID {report_id} not found for this user.")

    # Delete existing results for this report and replace with user-confirmed list
    db.query(BloodReportResult).filter(BloodReportResult.report_id == report.id).delete()

    db_results = []
    for item in confirmed_items:
        display_name = item.get("display_name") or "Custom Parameter"
        param_key = item.get("parameter_key") or normalize_parameter_key(display_name)
        val = item.get("value")

        if val is None:
            continue

        try:
            float_val = float(val)
        except ValueError:
            continue

        res = BloodReportResult(
            report_id=report.id,
            user_id=user_id,
            parameter_key=param_key,
            display_name=display_name,
            value=float_val,
            unit=item.get("unit", ""),
            reference_range=item.get("reference_range", ""),
            status="Valid",
            confirmed_by_user=True,
        )
        db.add(res)
        db_results.append(res)

    report.status = "confirmed"
    db.commit()
    db.refresh(report)

    return {
        "report_id": report.id,
        "status": report.status,
        "message": "Blood report values successfully confirmed and saved to health profile.",
        "confirmed_count": len(db_results),
    }


def delete_blood_report(db: Session, user_id: int, report_id: int) -> bool:
    """Deletes blood report, associated results, and private file from disk."""
    report = (
        db.query(BloodReport)
        .filter(BloodReport.id == report_id, BloodReport.user_id == user_id)
        .first()
    )

    if not report:
        return False

    if report.file_path and os.path.exists(report.file_path):
        try:
            os.remove(report.file_path)
        except Exception as e:
            logger.warning(f"[BLOOD_SERVICE] Failed to delete file {report.file_path}: {e}")

    db.delete(report)
    db.commit()
    return True


def merge_blood_report_data_into_health_dict(
    db: Session, user_id: int, health_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Merges confirmed blood report lab parameters into health_dict for food personalization.
    CONTROLLED PERSONALIZATION: Only supported parameters affect health_dict. Unlisted parameters
    (e.g., MCH, RDW) are preserved in DB history but do NOT affect food scoring.
    """
    report = (
        db.query(BloodReport)
        .filter(BloodReport.user_id == user_id, BloodReport.status == "confirmed")
        .order_by(BloodReport.uploaded_at.desc())
        .first()
    )

    if not report:
        health_dict["blood_report_active"] = False
        return health_dict

    confirmed_results = (
        db.query(BloodReportResult)
        .filter(BloodReportResult.report_id == report.id, BloodReportResult.confirmed_by_user == True)
        .all()
    )

    if not confirmed_results:
        health_dict["blood_report_active"] = False
        return health_dict

    confirmed_map = {r.parameter_key: r.value for r in confirmed_results}
    lab_summary = {}

    # Refine health profile indicators with lab values ONLY for supported health metrics
    if "fasting_glucose" in confirmed_map:
        health_dict["fasting_sugar"] = confirmed_map["fasting_glucose"]
        lab_summary["Fasting Glucose"] = f"{confirmed_map['fasting_glucose']} mg/dL"

    if "hba1c" in confirmed_map:
        health_dict["hba1c"] = confirmed_map["hba1c"]
        lab_summary["HbA1c"] = f"{confirmed_map['hba1c']}%"

    if "ldl" in confirmed_map:
        health_dict["ldl"] = confirmed_map["ldl"]
        lab_summary["LDL"] = f"{confirmed_map['ldl']} mg/dL"

    if "triglycerides" in confirmed_map:
        health_dict["triglycerides"] = confirmed_map["triglycerides"]
        lab_summary["Triglycerides"] = f"{confirmed_map['triglycerides']} mg/dL"

    if "total_cholesterol" in confirmed_map:
        health_dict["total_cholesterol"] = confirmed_map["total_cholesterol"]
        lab_summary["Total Cholesterol"] = f"{confirmed_map['total_cholesterol']} mg/dL"

    if "creatinine" in confirmed_map:
        health_dict["creatinine"] = confirmed_map["creatinine"]
        lab_summary["Creatinine"] = f"{confirmed_map['creatinine']} mg/dL"

    if "alt" in confirmed_map:
        health_dict["alt"] = confirmed_map["alt"]
        lab_summary["ALT"] = f"{confirmed_map['alt']} U/L"

    health_dict["blood_report_active"] = True
    health_dict["confirmed_lab_values"] = lab_summary
    return health_dict
