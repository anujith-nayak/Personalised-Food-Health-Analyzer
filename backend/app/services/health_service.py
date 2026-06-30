"""Health profile business logic."""
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.user import HealthProfile, CurrentHealthStatus, FoodRestriction
from app.schemas.user import HealthProfileRequest, HealthProfileResponse
from app.utils.food_restrictions import generate_grouped_restrictions


def upsert_health_profile(
    db: Session, user_id: int, data: HealthProfileRequest
) -> HealthProfileResponse:
    """Create or update health profile, validate values, regenerate restrictions."""

    # ── Validate BP / Sugar value vs selected severity ────────────────────
    data.validate_values()

    # ── Enforce gender-based restrictions ─────────────────────────────────
    from app.models.user import User as UserModel
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if user and user.gender == "male":
        if data.pcos or data.pcod:
            raise HTTPException(
                status_code=422,
                detail="PCOS and PCOD are not applicable for male users."
            )

    # ── Upsert the profile row ────────────────────────────────────────────
    profile = db.query(HealthProfile).filter(HealthProfile.user_id == user_id).first()
    fields  = data.model_dump(exclude={"current_health_statuses"})

    if profile:
        for key, val in fields.items():
            setattr(profile, key, val)
    else:
        profile = HealthProfile(user_id=user_id, **fields)
        db.add(profile)

    db.flush()

    # ── Replace current health statuses ───────────────────────────────────
    db.query(CurrentHealthStatus).filter(CurrentHealthStatus.user_id == user_id).delete()
    for name in data.current_health_statuses:
        db.add(CurrentHealthStatus(user_id=user_id, status_name=name))

    # ── Regenerate grouped food restrictions ──────────────────────────────
    db.query(FoodRestriction).filter(FoodRestriction.user_id == user_id).delete()

    groups = generate_grouped_restrictions(profile, data.current_health_statuses, db)
    for group in groups:
        for item in group["items"]:
            db.add(FoodRestriction(
                user_id=user_id,
                category=group["category"],
                item=item,
            ))

    db.commit()
    db.refresh(profile)
    return HealthProfileResponse.model_validate(profile)


def get_health_profile(db: Session, user_id: int) -> HealthProfileResponse:
    profile = db.query(HealthProfile).filter(HealthProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Health profile not found")
    return HealthProfileResponse.model_validate(profile)
