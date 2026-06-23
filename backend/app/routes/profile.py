from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import UserResponse, UpdateProfileRequest
from app.services.profile_service import get_profile, update_profile

router = APIRouter(tags=["Profile"])


@router.get("/profile", response_model=UserResponse)
def read_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_profile(db, current_user.id)


@router.put("/profile", response_model=UserResponse)
def edit_profile(
    data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_profile(db, current_user.id, data)
