"""User profile and dashboard business logic."""
from collections import defaultdict
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.user import User, HealthProfile, CurrentHealthStatus, FoodRestriction
from app.schemas.user import (
    UserResponse, UpdateProfileRequest, DashboardResponse,
    FoodRestrictionsResponse, FoodRestrictionGroup, HealthProfileResponse,
)
from app.utils.bmi import calculate_bmi, get_bmi_category


def get_profile(db: Session, user_id: int) -> UserResponse:
    return UserResponse.model_validate(_get_user(db, user_id))


def update_profile(db: Session, user_id: int, data: UpdateProfileRequest) -> UserResponse:
    user = _get_user(db, user_id)
    if data.weight is not None:        user.weight          = data.weight
    if data.height is not None:        user.height          = data.height
    if data.food_preference is not None: user.food_preference = data.food_preference
    if data.age is not None:           user.age             = data.age
    user.bmi_score    = calculate_bmi(user.weight, user.height)
    user.bmi_category = get_bmi_category(user.bmi_score)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


def get_dashboard(db: Session, user_id: int) -> DashboardResponse:
    user    = _get_user(db, user_id)
    profile = db.query(HealthProfile).filter(HealthProfile.user_id == user_id).first()
    statuses = [
        s.status_name for s in
        db.query(CurrentHealthStatus).filter(CurrentHealthStatus.user_id == user_id).all()
    ]
    groups = _load_restriction_groups(db, user_id)

    return DashboardResponse(
        user=UserResponse.model_validate(user),
        health_profile=HealthProfileResponse.model_validate(profile) if profile else None,
        current_health_statuses=statuses,
        food_restriction_groups=groups,
        profile_completion=_completion(user, profile, statuses),
    )


def get_food_restrictions(db: Session, user_id: int) -> FoodRestrictionsResponse:
    return FoodRestrictionsResponse(groups=_load_restriction_groups(db, user_id))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_user(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _load_restriction_groups(db: Session, user_id: int) -> list[FoodRestrictionGroup]:
    """Rebuild grouped structure from stored FoodRestriction rows."""
    rows = db.query(FoodRestriction).filter(FoodRestriction.user_id == user_id).all()
    bucket: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        bucket[row.category].append(row.item)
    return [FoodRestrictionGroup(category=cat, items=items) for cat, items in bucket.items()]


def _completion(user: User, profile, statuses: list) -> int:
    score = 0
    if user.name and user.email:    score += 20
    if user.bmi_score:              score += 20
    if profile:                     score += 20
    if statuses:                    score += 20
    if user.food_preference:        score += 20
    return score
