"""
Blood Report API Endpoints
==========================
Exposes endpoints for optional blood report upload, extraction review,
user confirmation, retrieval, and deletion.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.services.blood_report.report_service import (
    process_report_upload,
    get_user_blood_report,
    confirm_report_results,
    delete_blood_report,
)

router = APIRouter(prefix="/health/blood-report", tags=["Blood Report Module"])


# ── Request / Response Schemas ────────────────────────────────────────────────

class ConfirmedItemSchema(BaseModel):
    parameter_key: str
    display_name: Optional[str] = None
    value: float
    unit: Optional[str] = ""
    reference_range: Optional[str] = ""


class ConfirmReportRequest(BaseModel):
    confirmed_items: List[ConfirmedItemSchema]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_blood_report(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a medical blood report (PDF, JPG, JPEG, PNG).
    Extracts test parameters and returns them unconfirmed for user review.
    Does NOT modify trusted health profile data until explicitly confirmed.
    """
    try:
        file_bytes = await file.read()
        res = process_report_upload(
            db=db,
            user_id=current_user.id,
            file_bytes=file_bytes,
            file_name=file.filename or "blood_report.pdf",
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Couldn't identify any blood-test values from this report: {e}",
        )


@router.get("")
async def get_blood_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves current user's active blood report and lab results."""
    report_data = get_user_blood_report(db, current_user.id)
    if not report_data:
        return {"has_report": False, "report": None}
    return {"has_report": True, "report": report_data}


@router.put("/{report_id}/confirm")
async def confirm_blood_report(
    report_id: int,
    payload: ConfirmReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Saves user-reviewed and confirmed lab values.
    Confirmed values become part of the enhanced health profile.
    """
    try:
        confirmed_dicts = [item.model_dump() for item in payload.confirmed_items]
        res = confirm_report_results(
            db=db,
            user_id=current_user.id,
            report_id=report_id,
            confirmed_items=confirmed_dicts,
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{report_id}")
async def delete_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Deletes blood report, associated results, and private file from disk."""
    success = delete_blood_report(db, current_user.id, report_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blood report not found.")
    return {"message": "Blood report deleted successfully."}
