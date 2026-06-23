from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import DashboardResponse, FoodRestrictionsResponse
from app.services.profile_service import get_dashboard, get_food_restrictions

router = APIRouter(tags=["Dashboard"])


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_dashboard(db, current_user.id)


@router.get("/food-restrictions", response_model=FoodRestrictionsResponse)
def food_restrictions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_food_restrictions(db, current_user.id)
