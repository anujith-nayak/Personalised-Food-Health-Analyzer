"""
Pydantic schemas — request validation and response serialization.
"""
from typing import Optional, List
from pydantic import BaseModel, EmailStr, field_validator


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    age: int
    gender: str           # male | female | other
    height: float         # cm
    weight: float         # kg
    food_preference: str  # vegetarian | non_vegetarian | mixed

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v):
        if v.lower() not in ("male", "female", "other"):
            raise ValueError("Gender must be male, female, or other")
        return v.lower()

    @field_validator("food_preference")
    @classmethod
    def validate_food_preference(cls, v):
        allowed = ("vegetarian", "non_vegetarian", "mixed")
        if v.lower() not in allowed:
            raise ValueError(f"food_preference must be one of {allowed}")
        return v.lower()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# ── User / Profile ────────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    age: int
    gender: str
    height: float
    weight: float
    food_preference: str
    bmi_score: Optional[float] = None
    bmi_category: Optional[str] = None

    model_config = {"from_attributes": True}


class UpdateProfileRequest(BaseModel):
    weight: Optional[float] = None
    height: Optional[float] = None
    food_preference: Optional[str] = None
    age: Optional[int] = None


# ── Health Profile ────────────────────────────────────────────────────────────

class HealthProfileRequest(BaseModel):
    # Hypertension
    hypertension: bool = False
    bp_status: Optional[str] = None
    systolic: Optional[int] = None
    diastolic: Optional[int] = None
    # Diabetes
    diabetes: bool = False
    sugar_status: Optional[str] = None
    fasting_sugar: Optional[float] = None
    post_meal_sugar: Optional[float] = None
    # Thyroid
    thyroid: bool = False
    thyroid_type: Optional[str] = None
    # PCOS / PCOD
    pcos: bool = False
    pcos_diagnosed: Optional[bool] = None
    pcod: bool = False
    pcod_diagnosed: Optional[bool] = None
    # Other
    heart_disease: bool = False
    kidney_disease: bool = False
    obesity: bool = False
    none: bool = False
    # Current health statuses submitted together
    current_health_statuses: List[str] = []


class HealthProfileResponse(BaseModel):
    id: int
    user_id: int
    hypertension: bool
    bp_status: Optional[str] = None
    systolic: Optional[int] = None
    diastolic: Optional[int] = None
    diabetes: bool
    sugar_status: Optional[str] = None
    fasting_sugar: Optional[float] = None
    post_meal_sugar: Optional[float] = None
    thyroid: bool
    thyroid_type: Optional[str] = None
    pcos: bool
    pcos_diagnosed: Optional[bool] = None
    pcod: bool
    pcod_diagnosed: Optional[bool] = None
    heart_disease: bool
    kidney_disease: bool
    obesity: bool
    none: bool

    model_config = {"from_attributes": True}


# ── Dashboard ─────────────────────────────────────────────────────────────────

class DashboardResponse(BaseModel):
    user: UserResponse
    health_profile: Optional[HealthProfileResponse] = None
    current_health_statuses: List[str] = []
    food_restrictions: List[str] = []
    profile_completion: int  # 0–100


class FoodRestrictionsResponse(BaseModel):
    restrictions: List[str]
