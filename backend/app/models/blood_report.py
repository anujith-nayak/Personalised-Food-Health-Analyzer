"""
SQLAlchemy ORM models for optional Blood Reports and extracted lab test results.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database.db import Base


class BloodReport(Base):
    __tablename__ = "blood_reports"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    file_name   = Column(String, nullable=False)
    file_path   = Column(String, nullable=True)     # Private server storage path
    file_type   = Column(String, nullable=False)     # pdf | image
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    status      = Column(String, default="pending")  # pending | confirmed | archived

    user    = relationship("User", back_populates="blood_reports")
    results = relationship("BloodReportResult", back_populates="report", cascade="all, delete-orphan")


class BloodReportResult(Base):
    __tablename__ = "blood_report_results"

    id                = Column(Integer, primary_key=True, index=True)
    report_id         = Column(Integer, ForeignKey("blood_reports.id"), nullable=False, index=True)
    user_id           = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    parameter_key     = Column(String, nullable=False, index=True) # e.g. "hba1c", "fasting_glucose", "ldl"
    display_name      = Column(String, nullable=False)             # e.g. "HbA1c", "Fasting Glucose"
    value             = Column(Float,  nullable=True)
    unit              = Column(String, nullable=True)              # e.g. "mg/dL", "%"
    reference_range   = Column(String, nullable=True)              # e.g. "70 - 99"
    status            = Column(String, default="Review")           # Review | Valid | Needs Review
    confirmed_by_user = Column(Boolean, default=False)
    created_at        = Column(DateTime, default=datetime.utcnow)

    report = relationship("BloodReport", back_populates="results")
