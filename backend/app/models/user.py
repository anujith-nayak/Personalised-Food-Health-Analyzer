"""SQLAlchemy ORM models for users and health data."""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    DateTime, ForeignKey, Text
)
from sqlalchemy.orm import relationship
from app.database.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String(20), nullable=False)          # male | female | other
    height = Column(Float, nullable=False)               # cm
    weight = Column(Float, nullable=False)               # kg
    food_preference = Column(String(50), nullable=False) # vegetarian | non_vegetarian | mixed
    bmi_score = Column(Float, nullable=True)
    bmi_category = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    health_profile = relationship("HealthProfile", back_populates="user", uselist=False)
    current_health_statuses = relationship("CurrentHealthStatus", back_populates="user")
    food_restrictions = relationship("FoodRestriction", back_populates="user")


class HealthProfile(Base):
    __tablename__ = "health_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # Hypertension
    hypertension = Column(Boolean, default=False)
    bp_status = Column(String(20), nullable=True)   # normal | low | high
    systolic = Column(Integer, nullable=True)
    diastolic = Column(Integer, nullable=True)

    # Diabetes
    diabetes = Column(Boolean, default=False)
    sugar_status = Column(String(20), nullable=True) # normal | low | high
    fasting_sugar = Column(Float, nullable=True)
    post_meal_sugar = Column(Float, nullable=True)

    # Thyroid
    thyroid = Column(Boolean, default=False)
    thyroid_type = Column(String(30), nullable=True) # hypothyroidism | hyperthyroidism

    # PCOS / PCOD
    pcos = Column(Boolean, default=False)
    pcos_diagnosed = Column(Boolean, nullable=True)
    pcod = Column(Boolean, default=False)
    pcod_diagnosed = Column(Boolean, nullable=True)

    # Other conditions
    heart_disease = Column(Boolean, default=False)
    kidney_disease = Column(Boolean, default=False)
    obesity = Column(Boolean, default=False)
    none = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="health_profile")


class CurrentHealthStatus(Base):
    __tablename__ = "current_health_statuses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status_name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="current_health_statuses")


class FoodRestriction(Base):
    __tablename__ = "food_restrictions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    restriction_name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="food_restrictions")
