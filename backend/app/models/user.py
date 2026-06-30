"""
SQLAlchemy ORM models.
Tables are auto-created on startup via Base.metadata.create_all().
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.types import JSON
from sqlalchemy.orm import relationship
from app.database.db import Base


class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    name            = Column(String, nullable=False)
    email           = Column(String, unique=True, index=True, nullable=False)
    password_hash   = Column(String, nullable=False)
    age             = Column(Integer, nullable=False)
    gender          = Column(String, nullable=False)       # male | female | other
    height          = Column(Float,  nullable=False)
    weight          = Column(Float,  nullable=False)
    food_preference = Column(String, nullable=False)
    bmi_score       = Column(Float,  nullable=True)
    bmi_category    = Column(String, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    health_profile          = relationship("HealthProfile", back_populates="user", uselist=False)
    current_health_statuses = relationship("CurrentHealthStatus", back_populates="user")
    food_restrictions       = relationship("FoodRestriction", back_populates="user")


class HealthProfile(Base):
    __tablename__ = "health_profiles"

    id      = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # Hypertension
    hypertension = Column(Boolean, default=False)
    bp_status    = Column(String, nullable=True)   # normal | low | high
    systolic     = Column(Integer, nullable=True)
    diastolic    = Column(Integer, nullable=True)

    # Diabetes
    diabetes        = Column(Boolean, default=False)
    sugar_status    = Column(String, nullable=True)  # normal | low | high
    fasting_sugar   = Column(Float,  nullable=True)
    post_meal_sugar = Column(Float,  nullable=True)

    # Thyroid
    thyroid      = Column(Boolean, default=False)
    thyroid_type = Column(String, nullable=True)   # hypothyroidism | hyperthyroidism

    # PCOS / PCOD — only applicable to female / other
    pcos           = Column(Boolean, default=False)
    pcos_diagnosed = Column(Boolean, nullable=True)
    pcod           = Column(Boolean, default=False)
    pcod_diagnosed = Column(Boolean, nullable=True)

    # Other
    heart_disease  = Column(Boolean, default=False)
    kidney_disease = Column(Boolean, default=False)
    obesity        = Column(Boolean, default=False)
    none           = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="health_profile")


class CurrentHealthStatus(Base):
    __tablename__ = "current_health_statuses"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    status_name = Column(String, nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="current_health_statuses")


class FoodRestriction(Base):
    """
    Stores categorised food restrictions per user.
    category = display label  e.g. "High BP", "Fever"
    item     = specific food  e.g. "Chips", "Ice Cream"
    """
    __tablename__ = "food_restrictions"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    category   = Column(String, nullable=False)
    item       = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="food_restrictions")


class FoodRestrictionRule(Base):
    """
    DB-driven rule table.
    Adding a new disease = INSERT a row here, zero code changes needed.

    condition_key  — internal key  e.g. "hypertension_high"
    category_label — display name  e.g. "High BP"
    foods_json     — JSON list     e.g. ["Chips", "Pickles"]
    """
    __tablename__ = "food_restriction_rules"

    id             = Column(Integer, primary_key=True, index=True)
    condition_key  = Column(String, unique=True, nullable=False, index=True)
    category_label = Column(String, nullable=False)
    foods_json     = Column(JSON,   nullable=False)
    created_at     = Column(DateTime, default=datetime.utcnow)
