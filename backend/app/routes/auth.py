from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.schemas.user import RegisterRequest, LoginRequest, RefreshTokenRequest, TokenResponse
from app.services.auth_service import register_user, login_user, refresh_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user. Returns JWT tokens."""
    return register_user(db, data)


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """Login with email and password. Returns JWT tokens."""
    return login_user(db, data)


@router.post("/refresh-token", response_model=TokenResponse)
def refresh(data: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Get a new access token using a refresh token."""
    return refresh_access_token(db, data.refresh_token)
