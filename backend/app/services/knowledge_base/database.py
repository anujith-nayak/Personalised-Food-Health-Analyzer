"""
Knowledge Base Database Connection and SQLAlchemy ORM Models
============================================================
Manages SQLite connection for knowledge_base.db and defines normalized ORM models for:
- blood_parameters
- blood_parameter_conditions
- nutrition_actions
- food_examples
- references
"""

import os
from sqlalchemy import create_engine, Column, Integer, String, Float, Text
from sqlalchemy.orm import sessionmaker, declarative_base

KB_DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "knowledge_base.db")
)
KB_DATABASE_URL = f"sqlite:///{KB_DB_PATH}"

kb_engine = create_engine(
    KB_DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
)

KBSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=kb_engine)
KBBase = declarative_base()


class BloodParameter(KBBase):
    __tablename__ = "blood_parameters"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    parameter_name = Column(String(100), unique=True, index=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    normal_low = Column(Float, nullable=False)
    normal_high = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)


class BloodParameterCondition(KBBase):
    __tablename__ = "blood_parameter_conditions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    parameter_name = Column(String(100), index=True, nullable=False)
    condition_name = Column(String(50), nullable=False)


class NutritionAction(KBBase):
    __tablename__ = "nutrition_actions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    parameter_name = Column(String(100), index=True, nullable=False)
    condition_name = Column(String(50), nullable=False)
    nutrient = Column(String(100), nullable=False)
    action = Column(String(50), nullable=False)  # 'Limit', 'Avoid', 'Increase'
    severity = Column(String(50), nullable=False)  # 'High', 'Medium', 'Low'
    reason = Column(Text, nullable=False)
    evidence_source = Column(String(50), nullable=False)  # 'NIH', 'WHO', 'ADA', 'AHA', 'NKF'


class FoodExample(KBBase):
    __tablename__ = "food_examples"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nutrient = Column(String(100), index=True, nullable=False)
    action = Column(String(50), nullable=False)  # 'Limit', 'Avoid', 'Increase'
    food_name = Column(String(150), nullable=False)
    category = Column(String(100), nullable=False)


class Reference(KBBase):
    __tablename__ = "references"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    evidence_source = Column(String(50), unique=True, index=True, nullable=False)
    organization = Column(String(200), nullable=False)
    guideline = Column(String(300), nullable=False)
    url = Column(String(500), nullable=False)


def init_kb_db():
    """Create all tables if they do not exist."""
    KBBase.metadata.create_all(bind=kb_engine)


def get_kb_db():
    """FastAPI dependency or direct generator for KB DB session."""
    db = KBSessionLocal()
    try:
        yield db
    finally:
        db.close()
