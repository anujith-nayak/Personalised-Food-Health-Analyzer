"""User profile and dashboard business logic."""
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.user import User, HealthProfile, CurrentHealthStatus, FoodRestriction
from app.schemas.user import (
    UserResponse, UpdateProfileRequest,
    DashboardResponse, FoodRestrictionsResponse, HealthProfileResponse,
)
from app.utils.bmi import calculate_bmi, get_bmi_category


def get_profile(db: Session, user_id: int) -> UserResponse:
    return UserResponse.model_validate(_get_user(db, user_id))


def update_profile(db: Session, user_id: int, data: UpdateProfileRequest) -> UserResponse:
    user = _get_user(db, user_id)
    if data.weight is not None:
        user.weight = data.weight
    if data.height is not None:
        user.height = data.height
    if data.food_preference is not None:
        user.food_preference = data.food_preference
    if data.age is not None:
        user.age = data.age
    # Recalculate BMI whenever weight/height changes
    user.bmi_score = calculate_bmi(user.weight, user.height)
    user.bmi_category = get_bmi_category(user.bmi_score)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


def get_dashboard(db: Session, user_id: int) -> DashboardResponse:
    user = _get_user(db, user_id)
    profile = db.query(HealthProfile).filter(HealthProfile.user_id == user_id).first()
    statuses = [
        s.status_name for s in
        db.query(CurrentHealthStatus).filter(CurrentHealthStatus.user_id == user_id).all()
    ]
    restrictions = [
        r.restriction_name for r in
        db.query(FoodRestriction).filter(FoodRestriction.user_id == user_id).all()
    ]
    return DashboardResponse(
        user=UserResponse.model_validate(user),
        health_profile=HealthProfileResponse.model_validate(profile) if profile else None,
        current_health_statuses=statuses,
        food_restrictions=restrictions,
        profile_completion=_completion(user, profile, statuses),
    )


def get_food_restrictions(db: Session, user_id: int) -> FoodRestrictionsResponse:
    restrictions = [
        r.restriction_name for r in
        db.query(FoodRestriction).filter(FoodRestriction.user_id == user_id).all()
    ]
    return FoodRestrictionsResponse(restrictions=restrictions)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_user(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _completion(user: User, profile, statuses: list) -> int:
    score = 0
    if user.name and user.email:   score += 20
    if user.bmi_score:             score += 20
    if profile:                    score += 20
    if statuses:                   score += 20
    if user.food_preference:       score += 20
    return score
