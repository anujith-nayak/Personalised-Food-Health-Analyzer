from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import HealthProfileRequest, HealthProfileResponse
from app.services.health_service import upsert_health_profile, get_health_profile

router = APIRouter(prefix="/health-profile", tags=["Health"])


@router.post("", response_model=HealthProfileResponse, status_code=201)
def create_health_profile(
    data: HealthProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return upsert_health_profile(db, current_user.id, data)


@router.get("", response_model=HealthProfileResponse)
def read_health_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_health_profile(db, current_user.id)


@router.put("", response_model=HealthProfileResponse)
def update_health_profile(
    data: HealthProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return upsert_health_profile(db, current_user.id, data)
