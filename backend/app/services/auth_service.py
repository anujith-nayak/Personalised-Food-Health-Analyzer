"""Authentication business logic: register, login, refresh."""
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from passlib.context import CryptContext

from app.models.user import User
from app.schemas.user import RegisterRequest, LoginRequest, TokenResponse
from app.auth.jwt import create_access_token, create_refresh_token, decode_token
from app.utils.bmi import calculate_bmi, get_bmi_category

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def register_user(db: Session, data: RegisterRequest) -> TokenResponse:
    # Check for duplicate email
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    bmi = calculate_bmi(data.weight, data.height)

    user = User(
        name=data.name,
        email=data.email,
        password_hash=pwd_context.hash(data.password),
        age=data.age,
        gender=data.gender,
        height=data.height,
        weight=data.weight,
        food_preference=data.food_preference,
        bmi_score=bmi,
        bmi_category=get_bmi_category(bmi),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _tokens(user.id)


def login_user(db: Session, data: LoginRequest) -> TokenResponse:
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not pwd_context.verify(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return _tokens(user.id)


def refresh_access_token(db: Session, refresh_token: str) -> TokenResponse:
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _tokens(user.id)


def _tokens(user_id: int) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )
